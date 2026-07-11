"""Tests for point-in-time integrity — the zero-lookahead guarantee.

These tests prove that as_of queries never return data ingested after
the as_of timestamp. This is the integrity foundation of every backtest.
"""

from datetime import UTC, datetime, timedelta

import pytest

from src.ingest.store import (
    as_of_demand,
    as_of_fuel,
    as_of_interchange,
    connect,
)


@pytest.fixture()
def db():
    """In-memory DuckDB with test data spanning multiple ingestion times."""
    conn = connect(":memory:")

    t0 = datetime(2021, 2, 14, 12, 0, tzinfo=UTC)  # Period: noon Feb 14
    t1 = datetime(2021, 2, 14, 13, 0, tzinfo=UTC)  # Period: 1pm Feb 14

    # First ingestion at hour 14 — sees demand = 50000
    ingest_1 = datetime(2021, 2, 14, 14, 0, tzinfo=UTC)
    # Revised ingestion at hour 18 — corrected demand = 51000
    ingest_2 = datetime(2021, 2, 14, 18, 0, tzinfo=UTC)
    # Late revision at hour 22 — final demand = 50500
    ingest_3 = datetime(2021, 2, 14, 22, 0, tzinfo=UTC)

    conn.execute(
        """
        INSERT INTO eia930_demand (ba_code, period, demand_mw, forecast_mw, net_gen_mw, ingested_at)
        VALUES
            ('ERCO', ?, 50000, 49000, 48000, ?),
            ('ERCO', ?, 52000, 51000, 50000, ?),
            ('ERCO', ?, 51000, 49500, 48500, ?),
            ('ERCO', ?, 50500, 49800, 48200, ?)
    """,
        [t0, ingest_1, t1, ingest_1, t0, ingest_2, t0, ingest_3],
    )

    # Fuel data with two ingestion times
    conn.execute(
        """
        INSERT INTO eia930_fuel (ba_code, period, fuel_type, gen_mw, ingested_at)
        VALUES
            ('ERCO', ?, 'NG', 30000, ?),
            ('ERCO', ?, 'WND', 15000, ?),
            ('ERCO', ?, 'NG', 28000, ?)
    """,
        [t0, ingest_1, t0, ingest_1, t0, ingest_2],
    )

    # Interchange data
    conn.execute(
        """
        INSERT INTO eia930_interchange (from_ba, to_ba, period, flow_mw, ingested_at)
        VALUES
            ('ERCO', 'SWPP', ?, 500, ?),
            ('ERCO', 'SWPP', ?, 450, ?)
    """,
        [t0, ingest_1, t0, ingest_2],
    )

    return conn, t0, t1, ingest_1, ingest_2, ingest_3


def test_as_of_sees_only_past_ingestions(db):
    """Querying as_of=ingest_1 must NOT see data from ingest_2 or ingest_3."""
    conn, t0, t1, ingest_1, ingest_2, ingest_3 = db

    rows = as_of_demand(
        conn,
        "ERCO",
        period_start=t0,
        period_end=t0 + timedelta(hours=1),
        as_of=ingest_1,
    )
    assert len(rows) == 1
    assert rows[0]["demand_mw"] == 50000  # First ingestion value


def test_as_of_revision_supersedes(db):
    """Querying as_of=ingest_2 should return the revised value, not the original."""
    conn, t0, t1, ingest_1, ingest_2, ingest_3 = db

    rows = as_of_demand(
        conn,
        "ERCO",
        period_start=t0,
        period_end=t0 + timedelta(hours=1),
        as_of=ingest_2,
    )
    assert len(rows) == 1
    assert rows[0]["demand_mw"] == 51000  # Revised value from ingest_2


def test_as_of_latest_revision(db):
    """Querying as_of=ingest_3 should return the final revised value."""
    conn, t0, t1, ingest_1, ingest_2, ingest_3 = db

    rows = as_of_demand(
        conn,
        "ERCO",
        period_start=t0,
        period_end=t0 + timedelta(hours=1),
        as_of=ingest_3,
    )
    assert len(rows) == 1
    assert rows[0]["demand_mw"] == 50500  # Final revision


def test_as_of_before_any_ingestion_returns_empty(db):
    """Querying before any data was ingested must return nothing."""
    conn, t0, t1, ingest_1, ingest_2, ingest_3 = db

    rows = as_of_demand(
        conn,
        "ERCO",
        period_start=t0,
        period_end=t0 + timedelta(hours=1),
        as_of=datetime(2021, 2, 14, 10, 0, tzinfo=UTC),  # Before ingest_1
    )
    assert len(rows) == 0


def test_as_of_multiple_periods(db):
    """Querying a range returns multiple periods, each with correct point-in-time data."""
    conn, t0, t1, ingest_1, ingest_2, ingest_3 = db

    rows = as_of_demand(
        conn,
        "ERCO",
        period_start=t0,
        period_end=t1 + timedelta(hours=1),
        as_of=ingest_1,
    )
    assert len(rows) == 2
    assert rows[0]["demand_mw"] == 50000  # t0
    assert rows[1]["demand_mw"] == 52000  # t1


def test_fuel_as_of_point_in_time(db):
    """Fuel-type query respects point-in-time semantics."""
    conn, t0, t1, ingest_1, ingest_2, ingest_3 = db

    # At ingest_1: NG=30000, WND=15000
    rows = as_of_fuel(
        conn,
        "ERCO",
        period_start=t0,
        period_end=t0 + timedelta(hours=1),
        as_of=ingest_1,
    )
    ng_row = next(r for r in rows if r["fuel_type"] == "NG")
    assert ng_row["gen_mw"] == 30000

    # At ingest_2: NG revised to 28000
    rows = as_of_fuel(
        conn,
        "ERCO",
        period_start=t0,
        period_end=t0 + timedelta(hours=1),
        as_of=ingest_2,
    )
    ng_row = next(r for r in rows if r["fuel_type"] == "NG")
    assert ng_row["gen_mw"] == 28000


def test_interchange_as_of_point_in_time(db):
    """Interchange query respects point-in-time semantics."""
    conn, t0, t1, ingest_1, ingest_2, ingest_3 = db

    rows = as_of_interchange(
        conn,
        "ERCO",
        period_start=t0,
        period_end=t0 + timedelta(hours=1),
        as_of=ingest_1,
    )
    assert len(rows) == 1
    assert rows[0]["flow_mw"] == 500

    rows = as_of_interchange(
        conn,
        "ERCO",
        period_start=t0,
        period_end=t0 + timedelta(hours=1),
        as_of=ingest_2,
    )
    assert len(rows) == 1
    assert rows[0]["flow_mw"] == 450  # Revised


def test_no_lookahead_invariant(db):
    """The core invariant: no row returned has ingested_at > as_of."""
    conn, t0, t1, ingest_1, ingest_2, ingest_3 = db

    for as_of in [ingest_1, ingest_2, ingest_3]:
        rows = as_of_demand(
            conn,
            "ERCO",
            period_start=t0,
            period_end=t1 + timedelta(hours=1),
            as_of=as_of,
        )
        for row in rows:
            # DuckDB returns naive datetimes; compare without tzinfo
            ingested = row["ingested_at"]
            cutoff = as_of.replace(tzinfo=None)
            assert ingested <= cutoff, (
                f"Lookahead violation: ingested_at={ingested} > as_of={cutoff}"
            )
