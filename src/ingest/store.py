"""DuckDB point-in-time data store.

Every record carries an `ingested_at` timestamp — the moment this system first
saw the data. Queries accept an `as_of` parameter to reconstruct the information
state at any historical moment with zero lookahead.

This is the integrity foundation of every backtest claim.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import duckdb

DEFAULT_DB_PATH = Path("data/grid.duckdb")


def connect(db_path: Path | str = DEFAULT_DB_PATH) -> duckdb.DuckDBPyConnection:
    """Open (or create) the point-in-time DuckDB store."""
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = duckdb.connect(str(db_path))
    _init_schema(conn)
    return conn


def _init_schema(conn: duckdb.DuckDBPyConnection) -> None:
    """Create tables if they don't exist."""

    # EIA-930 hourly demand by balancing authority
    conn.execute("""
        CREATE TABLE IF NOT EXISTS eia930_demand (
            ba_code       VARCHAR NOT NULL,
            period        TIMESTAMP NOT NULL,
            demand_mw     DOUBLE,
            forecast_mw   DOUBLE,
            net_gen_mw    DOUBLE,
            source        VARCHAR DEFAULT 'eia930',
            published_at  TIMESTAMP,
            ingested_at   TIMESTAMP NOT NULL,
            PRIMARY KEY (ba_code, period, ingested_at)
        )
    """)

    # EIA-930 generation by fuel type
    conn.execute("""
        CREATE TABLE IF NOT EXISTS eia930_fuel (
            ba_code       VARCHAR NOT NULL,
            period        TIMESTAMP NOT NULL,
            fuel_type     VARCHAR NOT NULL,
            gen_mw        DOUBLE,
            source        VARCHAR DEFAULT 'eia930',
            published_at  TIMESTAMP,
            ingested_at   TIMESTAMP NOT NULL,
            PRIMARY KEY (ba_code, period, fuel_type, ingested_at)
        )
    """)

    # EIA-930 interchange between BAs
    conn.execute("""
        CREATE TABLE IF NOT EXISTS eia930_interchange (
            from_ba       VARCHAR NOT NULL,
            to_ba         VARCHAR NOT NULL,
            period        TIMESTAMP NOT NULL,
            flow_mw       DOUBLE,
            source        VARCHAR DEFAULT 'eia930',
            published_at  TIMESTAMP,
            ingested_at   TIMESTAMP NOT NULL,
            PRIMARY KEY (from_ba, to_ba, period, ingested_at)
        )
    """)

    # Weather observations (historical + recent)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS weather_obs (
            station_id    VARCHAR NOT NULL,
            ba_code       VARCHAR,
            period        TIMESTAMP NOT NULL,
            temp_c        DOUBLE,
            source        VARCHAR DEFAULT 'noaa',
            ingested_at   TIMESTAMP NOT NULL,
            PRIMARY KEY (station_id, period, ingested_at)
        )
    """)

    # Weather forecasts (point-in-time: issued_at is when the forecast was made)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS weather_forecast (
            station_id    VARCHAR NOT NULL,
            ba_code       VARCHAR,
            issued_at     TIMESTAMP NOT NULL,
            valid_at      TIMESTAMP NOT NULL,
            temp_c        DOUBLE,
            source        VARCHAR DEFAULT 'nws',
            ingested_at   TIMESTAMP NOT NULL,
            PRIMARY KEY (station_id, issued_at, valid_at, ingested_at)
        )
    """)


def as_of_demand(
    conn: duckdb.DuckDBPyConnection,
    ba_code: str,
    period_start: datetime,
    period_end: datetime,
    as_of: datetime,
) -> list[dict]:
    """Query demand data using only records ingested before `as_of`.

    Returns the latest-ingested version of each (ba_code, period) row
    that was available at `as_of`. This is the core point-in-time primitive.
    """
    result = conn.execute(
        """
        WITH ranked AS (
            SELECT *,
                ROW_NUMBER() OVER (
                    PARTITION BY ba_code, period
                    ORDER BY ingested_at DESC
                ) AS rn
            FROM eia930_demand
            WHERE ba_code = ?
              AND period >= ?
              AND period < ?
              AND ingested_at <= ?
        )
        SELECT ba_code, period, demand_mw, forecast_mw, net_gen_mw,
               published_at, ingested_at
        FROM ranked
        WHERE rn = 1
        ORDER BY period
    """,
        [ba_code, period_start, period_end, as_of],
    ).fetchall()

    columns = [
        "ba_code",
        "period",
        "demand_mw",
        "forecast_mw",
        "net_gen_mw",
        "published_at",
        "ingested_at",
    ]
    return [dict(zip(columns, row)) for row in result]


def as_of_fuel(
    conn: duckdb.DuckDBPyConnection,
    ba_code: str,
    period_start: datetime,
    period_end: datetime,
    as_of: datetime,
) -> list[dict]:
    """Query fuel-type generation with point-in-time semantics."""
    result = conn.execute(
        """
        WITH ranked AS (
            SELECT *,
                ROW_NUMBER() OVER (
                    PARTITION BY ba_code, period, fuel_type
                    ORDER BY ingested_at DESC
                ) AS rn
            FROM eia930_fuel
            WHERE ba_code = ?
              AND period >= ?
              AND period < ?
              AND ingested_at <= ?
        )
        SELECT ba_code, period, fuel_type, gen_mw, published_at, ingested_at
        FROM ranked
        WHERE rn = 1
        ORDER BY period, fuel_type
    """,
        [ba_code, period_start, period_end, as_of],
    ).fetchall()

    columns = ["ba_code", "period", "fuel_type", "gen_mw", "published_at", "ingested_at"]
    return [dict(zip(columns, row)) for row in result]


def as_of_interchange(
    conn: duckdb.DuckDBPyConnection,
    ba_code: str,
    period_start: datetime,
    period_end: datetime,
    as_of: datetime,
) -> list[dict]:
    """Query interchange with point-in-time semantics. Returns flows where ba_code is sender."""
    result = conn.execute(
        """
        WITH ranked AS (
            SELECT *,
                ROW_NUMBER() OVER (
                    PARTITION BY from_ba, to_ba, period
                    ORDER BY ingested_at DESC
                ) AS rn
            FROM eia930_interchange
            WHERE from_ba = ?
              AND period >= ?
              AND period < ?
              AND ingested_at <= ?
        )
        SELECT from_ba, to_ba, period, flow_mw, published_at, ingested_at
        FROM ranked
        WHERE rn = 1
        ORDER BY period, to_ba
    """,
        [ba_code, period_start, period_end, as_of],
    ).fetchall()

    columns = ["from_ba", "to_ba", "period", "flow_mw", "published_at", "ingested_at"]
    return [dict(zip(columns, row)) for row in result]


def as_of_weather(
    conn: duckdb.DuckDBPyConnection,
    ba_code: str,
    period_start: datetime,
    period_end: datetime,
    as_of: datetime,
) -> list[dict]:
    """Query weather observations with point-in-time semantics."""
    result = conn.execute(
        """
        WITH ranked AS (
            SELECT *,
                ROW_NUMBER() OVER (
                    PARTITION BY station_id, period
                    ORDER BY ingested_at DESC
                ) AS rn
            FROM weather_obs
            WHERE ba_code = ?
              AND period >= ?
              AND period < ?
              AND ingested_at <= ?
        )
        SELECT station_id, ba_code, period, temp_c, ingested_at
        FROM ranked
        WHERE rn = 1
        ORDER BY period
    """,
        [ba_code, period_start, period_end, as_of],
    ).fetchall()

    columns = ["station_id", "ba_code", "period", "temp_c", "ingested_at"]
    return [dict(zip(columns, row)) for row in result]


def now_utc() -> datetime:
    return datetime.now(UTC)
