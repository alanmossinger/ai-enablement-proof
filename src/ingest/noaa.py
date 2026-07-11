"""NOAA/NWS weather data client — temperature observations and forecasts.

Sources:
  - NWS API (api.weather.gov): current/recent gridpoint forecasts with issue timestamps
  - NOAA ISD via bulk CSV: historical hourly observations for backtesting

BA-to-station mapping connects weather data to grid regions.
"""

from __future__ import annotations

import csv
import logging
from typing import Any

import httpx

from .store import connect, now_utc

logger = logging.getLogger(__name__)

NWS_BASE = "https://api.weather.gov"
NWS_HEADERS = {
    "User-Agent": "(ai-enablement-proof, github.com/alanmossinger/ai-enablement-proof)",
    "Accept": "application/geo+json",
}

# Major load-center weather stations mapped to BAs.
# USAF-WBAN IDs for ISD historical data + NWS grid coordinates.
# Station IDs: USAF-WBAN from ISD history.
# Verify against https://www.ncei.noaa.gov/pub/data/noaa/isd-history.csv
BA_STATIONS: dict[str, list[dict[str, Any]]] = {
    "ERCO": [
        {"station_id": "722590-03927", "name": "Dallas/Fort Worth", "lat": 32.90, "lon": -97.04},
        {"station_id": "722430-12960", "name": "Houston IAH", "lat": 29.76, "lon": -95.37},
        {"station_id": "722530-12921", "name": "San Antonio", "lat": 29.54, "lon": -98.47},
        {"station_id": "722540-13904", "name": "Austin", "lat": 30.27, "lon": -97.74},
    ],
    "PJM": [
        {"station_id": "724080-13739", "name": "Philadelphia", "lat": 39.95, "lon": -75.17},
        {"station_id": "724050-13743", "name": "Washington DC", "lat": 38.85, "lon": -77.03},
        {"station_id": "725300-94846", "name": "Chicago", "lat": 41.88, "lon": -87.63},
    ],
    "MISO": [
        {"station_id": "726580-14922", "name": "Minneapolis", "lat": 44.98, "lon": -93.27},
        {"station_id": "724340-13994", "name": "St. Louis", "lat": 38.75, "lon": -90.37},
        {"station_id": "725370-94847", "name": "Detroit", "lat": 42.33, "lon": -83.05},
    ],
    "CISO": [
        {"station_id": "722950-23174", "name": "Los Angeles", "lat": 33.94, "lon": -118.41},
        {"station_id": "724940-23234", "name": "San Francisco", "lat": 37.62, "lon": -122.37},
        {"station_id": "724839-93225", "name": "Sacramento", "lat": 38.58, "lon": -121.49},
    ],
    "ISNE": [
        {"station_id": "725090-14739", "name": "Boston", "lat": 42.36, "lon": -71.06},
    ],
    "NYIS": [
        {"station_id": "744860-94789", "name": "New York JFK", "lat": 40.64, "lon": -73.76},
    ],
}


def fetch_nws_forecast(lat: float, lon: float) -> list[dict]:
    """Fetch NWS gridpoint hourly forecast for a location.

    Returns list of forecast periods with issue timestamp for point-in-time tracking.
    """
    # Step 1: get the grid coordinates for this lat/lon
    points_url = f"{NWS_BASE}/points/{lat:.4f},{lon:.4f}"
    resp = httpx.get(points_url, headers=NWS_HEADERS, timeout=30)
    resp.raise_for_status()
    props = resp.json()["properties"]
    grid_id = props["gridId"]
    grid_x = props["gridX"]
    grid_y = props["gridY"]

    # Step 2: get hourly forecast
    forecast_url = f"{NWS_BASE}/gridpoints/{grid_id}/{grid_x},{grid_y}/forecast/hourly"
    resp = httpx.get(forecast_url, headers=NWS_HEADERS, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    update_time = data["properties"].get("updateTime", "")
    periods = data["properties"].get("periods", [])

    results = []
    for p in periods:
        temp_f = p.get("temperature")
        temp_c = (temp_f - 32) * 5 / 9 if temp_f is not None else None
        results.append(
            {
                "issued_at": update_time,
                "valid_at": p.get("startTime", ""),
                "temp_c": temp_c,
            }
        )

    return results


def ingest_nws_forecasts(
    ba_codes: list[str] | None = None,
    db_path: str = "data/grid.duckdb",
) -> int:
    """Fetch and store NWS forecasts for all stations in specified BAs."""
    if ba_codes is None:
        ba_codes = list(BA_STATIONS.keys())

    conn = connect(db_path)
    ingested_at = now_utc()
    count = 0

    for ba in ba_codes:
        stations = BA_STATIONS.get(ba, [])
        for station in stations:
            try:
                forecasts = fetch_nws_forecast(station["lat"], station["lon"])
                for fc in forecasts:
                    conn.execute(
                        """
                        INSERT INTO weather_forecast
                            (station_id, ba_code, issued_at, valid_at, temp_c, source, ingested_at)
                        VALUES (?, ?, ?, ?, ?, 'nws', ?)
                        """,
                        [
                            station["station_id"],
                            ba,
                            fc["issued_at"],
                            fc["valid_at"],
                            fc["temp_c"],
                            ingested_at,
                        ],
                    )
                    count += 1
                logger.info(
                    "Ingested %d forecasts for %s (%s)", len(forecasts), station["name"], ba
                )
            except httpx.HTTPError as e:
                logger.warning("Failed to fetch forecast for %s: %s", station["name"], e)

    conn.close()
    return count


def ingest_isd_csv(
    csv_path: str,
    station_id: str,
    ba_code: str,
    db_path: str = "data/grid.duckdb",
) -> int:
    """Ingest historical hourly temperature from an ISD CSV file.

    ISD CSV files can be downloaded from:
    https://www.ncei.noaa.gov/data/global-hourly/access/
    """
    conn = connect(db_path)
    ingested_at = now_utc()
    count = 0

    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            date_str = row.get("DATE", "")
            tmp_raw = row.get("TMP", "")

            if not date_str or not tmp_raw:
                continue

            # ISD TMP format: "temperature,quality" in tenths of degrees C
            parts = tmp_raw.split(",")
            if not parts or parts[0] in ("+9999", ""):
                continue

            try:
                temp_c = int(parts[0]) / 10.0
            except ValueError:
                continue

            conn.execute(
                """
                INSERT INTO weather_obs (station_id, ba_code, period, temp_c, source, ingested_at)
                VALUES (?, ?, ?, ?, 'isd', ?)
                """,
                [station_id, ba_code, date_str, temp_c, ingested_at],
            )
            count += 1

    logger.info("Ingested %d ISD observations for station %s", count, station_id)
    conn.close()
    return count
