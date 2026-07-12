"""EIA-930 API v2 client — hourly grid data for all U.S. balancing authorities.

Endpoints:
  - region-data: hourly demand, day-ahead forecast, net generation per BA
  - fuel-type-data: generation by fuel type per BA
  - interchange-data: interchange flows between BAs

All data is stamped with `ingested_at` for point-in-time integrity.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

from .store import connect, now_utc

logger = logging.getLogger(__name__)

BASE_URL = "https://api.eia.gov/v2/electricity/rto"

# Page size limit for EIA API v2
PAGE_SIZE = 5000


def _get_api_key() -> str:
    key = os.environ.get("EIA_API_KEY", "")
    if not key:
        raise OSError(
            "EIA_API_KEY not set. Register free at https://www.eia.gov/opendata/register.php"
        )
    return key


def _fetch_paginated(
    endpoint: str,
    params: dict[str, Any],
    *,
    max_pages: int = 20,
) -> list[dict]:
    """Fetch all pages from an EIA API v2 endpoint."""
    api_key = _get_api_key()
    params = {**params, "api_key": api_key, "length": PAGE_SIZE}
    all_records: list[dict] = []

    for page in range(max_pages):
        params["offset"] = page * PAGE_SIZE
        resp = httpx.get(f"{BASE_URL}/{endpoint}", params=params, timeout=60)
        resp.raise_for_status()
        body = resp.json()

        data = body.get("response", {}).get("data", [])
        if not data:
            break
        all_records.extend(data)

        total = int(body.get("response", {}).get("total", 0))
        if len(all_records) >= total:
            break

    logger.info("Fetched %d records from %s", len(all_records), endpoint)
    return all_records


def fetch_demand(
    start: str,
    end: str,
    ba_codes: list[str] | None = None,
) -> list[dict]:
    """Fetch hourly demand, forecast, and net generation per BA.

    Args:
        start: ISO date string (e.g. "2021-02-01")
        end: ISO date string (e.g. "2021-02-28")
        ba_codes: Optional list of BA codes to filter (e.g. ["ERCO", "PJM"])
    """
    params: dict[str, Any] = {
        "frequency": "hourly",
        "data[0]": "value",
        "facets[type][]": ["D", "DF", "NG"],  # Demand, Demand Forecast, Net Generation
        "start": start,
        "end": end,
        "sort[0][column]": "period",
        "sort[0][direction]": "asc",
    }
    if ba_codes:
        for i, ba in enumerate(ba_codes):
            params[f"facets[respondent][{i}]"] = ba

    return _fetch_paginated("region-data/data/", params)


def fetch_fuel_type(
    start: str,
    end: str,
    ba_codes: list[str] | None = None,
) -> list[dict]:
    """Fetch generation by fuel type per BA."""
    params: dict[str, Any] = {
        "frequency": "hourly",
        "data[0]": "value",
        "start": start,
        "end": end,
        "sort[0][column]": "period",
        "sort[0][direction]": "asc",
    }
    if ba_codes:
        for i, ba in enumerate(ba_codes):
            params[f"facets[respondent][{i}]"] = ba

    return _fetch_paginated("fuel-type-data/data/", params)


def fetch_interchange(
    start: str,
    end: str,
    ba_codes: list[str] | None = None,
) -> list[dict]:
    """Fetch interchange flows between BAs."""
    params: dict[str, Any] = {
        "frequency": "hourly",
        "data[0]": "value",
        "start": start,
        "end": end,
        "sort[0][column]": "period",
        "sort[0][direction]": "asc",
    }
    if ba_codes:
        for i, ba in enumerate(ba_codes):
            params[f"facets[fromba][{i}]"] = ba

    return _fetch_paginated("interchange-data/data/", params)


def ingest_demand(
    start: str,
    end: str,
    ba_codes: list[str] | None = None,
    db_path: str = "data/grid.duckdb",
) -> int:
    """Fetch and store demand data with point-in-time ingestion timestamp."""
    records = fetch_demand(start, end, ba_codes)
    if not records:
        return 0

    conn = connect(db_path)
    ingested_at = now_utc()
    count = 0

    # EIA returns records with type facet — pivot D/DF/NG into columns per (ba, period)
    by_key: dict[tuple[str, str], dict[str, float | None]] = {}
    for rec in records:
        ba = rec.get("respondent", "")
        period = _normalize_period(rec.get("period", ""))
        rtype = rec.get("type", "")
        value = rec.get("value")

        key = (ba, period)
        if key not in by_key:
            by_key[key] = {"demand_mw": None, "forecast_mw": None, "net_gen_mw": None}

        if rtype == "D":
            by_key[key]["demand_mw"] = _safe_float(value)
        elif rtype == "DF":
            by_key[key]["forecast_mw"] = _safe_float(value)
        elif rtype == "NG":
            by_key[key]["net_gen_mw"] = _safe_float(value)

    for (ba, period), vals in by_key.items():
        conn.execute(
            """
            INSERT INTO eia930_demand
                (ba_code, period, demand_mw, forecast_mw, net_gen_mw, ingested_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [ba, period, vals["demand_mw"], vals["forecast_mw"], vals["net_gen_mw"], ingested_at],
        )
        count += 1

    logger.info("Ingested %d demand records for %s to %s", count, start, end)
    conn.close()
    return count


def ingest_fuel_type(
    start: str,
    end: str,
    ba_codes: list[str] | None = None,
    db_path: str = "data/grid.duckdb",
) -> int:
    """Fetch and store fuel-type generation data."""
    records = fetch_fuel_type(start, end, ba_codes)
    if not records:
        return 0

    conn = connect(db_path)
    ingested_at = now_utc()
    count = 0

    for rec in records:
        ba = rec.get("respondent", "")
        period = _normalize_period(rec.get("period", ""))
        fuel = rec.get("fueltype", "")
        value = _safe_float(rec.get("value"))

        conn.execute(
            """
            INSERT INTO eia930_fuel (ba_code, period, fuel_type, gen_mw, ingested_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            [ba, period, fuel, value, ingested_at],
        )
        count += 1

    logger.info("Ingested %d fuel records for %s to %s", count, start, end)
    conn.close()
    return count


def ingest_interchange(
    start: str,
    end: str,
    ba_codes: list[str] | None = None,
    db_path: str = "data/grid.duckdb",
) -> int:
    """Fetch and store interchange data."""
    records = fetch_interchange(start, end, ba_codes)
    if not records:
        return 0

    conn = connect(db_path)
    ingested_at = now_utc()
    count = 0

    for rec in records:
        from_ba = rec.get("fromba", "")
        to_ba = rec.get("toba", "")
        period = _normalize_period(rec.get("period", ""))
        value = _safe_float(rec.get("value"))

        conn.execute(
            """
            INSERT INTO eia930_interchange (from_ba, to_ba, period, flow_mw, ingested_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            [from_ba, to_ba, period, value, ingested_at],
        )
        count += 1

    logger.info("Ingested %d interchange records for %s to %s", count, start, end)
    conn.close()
    return count


def _normalize_period(period: str) -> str:
    """Convert EIA period format '2021-02-08T00' to DuckDB-compatible timestamp."""
    # EIA returns 'YYYY-MM-DDTHH' — need 'YYYY-MM-DD HH:00:00'
    if "T" in period and len(period) <= 13:
        date_part, hour_part = period.split("T", 1)
        return f"{date_part} {hour_part}:00:00"
    return period


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None
