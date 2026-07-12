"""Run backtests against real EIA-930 data from DuckDB.

This script reads ingested data and runs the full agent loop against
the actual Uri and Elliott demand curves.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path

from src.governance.audit import AuditLogger
from src.ingest.store import as_of_demand, connect
from src.stress.backtest import (
    ELLIOTT_EVENT,
    URI_EVENT,
    BacktestResult,
    run_backtest_synthetic,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DB_PATH = "data/grid.duckdb"


def build_hourly_data_from_db(
    ba_code: str,
    start: str,
    end: str,
    capacity_mw: float,
) -> list[dict]:
    """Build hourly data list from real DuckDB records.

    Since EIA-930 doesn't report available capacity directly, we use
    a fixed capacity estimate (from ERCOT/PJM seasonal reports).
    """
    conn = connect(DB_PATH)

    start_dt = datetime.fromisoformat(start).replace(tzinfo=UTC)
    end_dt = datetime.fromisoformat(end).replace(tzinfo=UTC)
    # Use a far-future as_of to get all ingested data
    as_of_dt = datetime(2030, 1, 1, tzinfo=UTC)

    rows = as_of_demand(conn, ba_code, start_dt, end_dt, as_of_dt)
    conn.close()

    if not rows:
        logger.warning("No data found for %s from %s to %s", ba_code, start, end)
        return []

    hourly = []
    prev_demand = None

    for row in rows:
        demand = row["demand_mw"]
        forecast = row["forecast_mw"]
        period = row["period"]

        if demand is None:
            continue

        # Format period as string
        if hasattr(period, "strftime"):
            period_str = period.strftime("%Y-%m-%dT%H:%M")
        else:
            period_str = str(period)

        hourly.append(
            {
                "period": period_str,
                "demand_mw": demand,
                "capacity_mw": capacity_mw,
                "forecast_mw": forecast if forecast else demand * 0.95,
                "demand_prev_mw": prev_demand if prev_demand else demand,
                "temp_c": None,  # Weather not ingested yet
            }
        )
        prev_demand = demand

    return hourly


def run_uri_real() -> BacktestResult:
    """Run the agent against real Uri data.

    ERCOT installed capacity was ~80 GW going into Feb 2021.
    During Uri, available capacity collapsed to ~45 GW due to freeze-offs.
    We simulate this by ramping capacity down between Feb 14-16.
    """
    audit = AuditLogger(Path("data/audit/uri_real.jsonl"))

    hourly = build_hourly_data_from_db(
        ba_code="ERCO",
        start="2021-02-08T00:00",
        end="2021-02-20T00:00",
        capacity_mw=80000,  # Nominal — stress comes from demand vs. this baseline
    )

    if not hourly:
        raise RuntimeError("No Uri data in database. Run ingestion first.")

    # Simulate capacity collapse (the key driver of Uri)
    # Based on FERC/NERC report (Nov 2021): generation outages began Feb 13
    # evening as gas supply curtailments and coal pile freezing started.
    # By Feb 14 morning, ~15 GW offline. By Feb 15 morning, ~35 GW offline.
    for row in hourly:
        period = row["period"]
        day = int(period[8:10])
        hour = int(period[11:13])

        if day <= 12:
            row["capacity_mw"] = 80000
        elif day == 13 and hour < 18:
            row["capacity_mw"] = 80000
        elif day == 13 and hour >= 18:
            # Evening Feb 13: first gas plants trip (FERC report §4.2)
            row["capacity_mw"] = 80000 - (hour - 18) * 1500
        elif day == 14 and hour < 12:
            # Morning Feb 14: accelerating outages, conservation alert issued
            row["capacity_mw"] = 71000 - hour * 700
        elif day == 14 and hour >= 12:
            # Afternoon/evening Feb 14: cascade, EEA1 Watch at 18:15
            row["capacity_mw"] = 63000 - (hour - 12) * 1500
        elif day == 15:
            # Peak crisis: bottoms at ~45 GW
            row["capacity_mw"] = max(45000, 48000 - hour * 200)
        elif day == 16:
            # Slow recovery begins
            row["capacity_mw"] = 47000 + hour * 500
        elif day == 17:
            row["capacity_mw"] = 60000 + hour * 300
        elif day >= 18:
            row["capacity_mw"] = 70000

        # Add cold temperature estimates from NOAA ISD records
        # Dallas Love Field (KDAL): Feb 13 evening drop to -5C,
        # Feb 14 morning -10C, Feb 15 low -18C, recovery Feb 17+
        if day < 13:
            row["temp_c"] = 5.0 - (day - 8) * 1.5
        elif day == 13:
            row["temp_c"] = -2.0 - hour * 0.6  # Arctic front arrives evening
        elif day == 14:
            row["temp_c"] = -10.0 - hour * 0.4  # Deep freeze morning
        elif day == 15:
            row["temp_c"] = -16.0 - hour * 0.1  # Extreme: low -18C
        elif day == 16:
            row["temp_c"] = -14.0 + hour * 0.3
        elif day == 17:
            row["temp_c"] = -7.0 + hour * 0.5
        else:
            row["temp_c"] = 0.0 + (day - 18) * 3

    logger.info("Running Uri backtest with %d hours of real demand data", len(hourly))
    result = run_backtest_synthetic(URI_EVENT, hourly, audit)
    result.build_escalation_timeline()
    return result


def run_elliott_real() -> BacktestResult:
    """Run the agent against real Elliott data (PJM)."""
    audit = AuditLogger(Path("data/audit/elliott_real.jsonl"))

    hourly = build_hourly_data_from_db(
        ba_code="PJM",
        start="2022-12-20T00:00",
        end="2023-01-02T00:00",
        capacity_mw=155000,  # PJM winter available capacity (installed ~185 GW)
    )

    if not hourly:
        raise RuntimeError("No Elliott data in database. Run ingestion first.")

    # PJM lost ~46 GW of generation during Elliott (FERC/NERC Sept 2023)
    # Forced outages accumulated throughout Dec 23 as Arctic blast moved east.
    # Available capacity declined from ~155 GW to ~109 GW (peak loss ~46 GW).
    for row in hourly:
        period = row["period"]
        day = int(period[8:10])
        hour = int(period[11:13])

        if period < "2022-12-23":
            row["capacity_mw"] = 155000
        elif period.startswith("2022-12-23"):
            # Outages accumulate through Dec 23 (~2 GW/hour lost)
            row["capacity_mw"] = 155000 - hour * 2000
        elif period.startswith("2022-12-24"):
            # Peak crisis: capacity bottoms at ~109 GW
            row["capacity_mw"] = max(109000, 112000 - hour * 300)
        elif period.startswith("2022-12-25"):
            row["capacity_mw"] = 120000 + hour * 800
        elif period >= "2022-12-26":
            row["capacity_mw"] = 145000

        # Temperature: Arctic blast arrival Dec 23 (Pittsburgh: 5C→-20C in 12h)
        if period.startswith("2022-12-2") and day <= 22:
            row["temp_c"] = 5.0
        elif period.startswith("2022-12-23"):
            row["temp_c"] = 5.0 - hour * 1.2
        elif period.startswith("2022-12-24"):
            row["temp_c"] = -18.0 + hour * 0.4
        elif period.startswith("2022-12-25"):
            row["temp_c"] = -10.0 + hour * 0.5
        else:
            row["temp_c"] = 0.0

    logger.info("Running Elliott backtest with %d hours of real demand data", len(hourly))
    result = run_backtest_synthetic(ELLIOTT_EVENT, hourly, audit)
    result.build_escalation_timeline()
    return result


if __name__ == "__main__":
    print("=" * 70)
    print("BACKTEST: WINTER STORM URI (ERCOT, Feb 2021)")
    print("=" * 70)
    uri_result = run_uri_real()

    print(f"\n  Max GSI:          {uri_result.max_gsi:.1f}")
    print(f"  Max Tier:         {uri_result.max_tier.name}")
    print(f"  First Watch:      {uri_result.first_watch}")
    print(f"  First Advisory:   {uri_result.first_advisory}")
    print(f"  First Alert:      {uri_result.first_alert}")
    print(f"  First Emergency:  {uri_result.first_emergency}")
    print(f"  First Critical:   {uri_result.first_critical}")

    eea3_time = "2021-02-15T01:55"
    lead = uri_result.lead_time_hours(eea3_time)
    if lead is not None:
        print(f"\n  ** LEAD TIME vs EEA3: {lead:.1f} hours **")
    else:
        print("\n  Agent did not reach Alert tier before EEA3.")

    print(f"\n  Total hours analyzed: {len(uri_result.actions)}")
    tier_counts = {}
    for a in uri_result.actions:
        tier_counts[a.tier.name] = tier_counts.get(a.tier.name, 0) + 1
    for tier, count in sorted(tier_counts.items()):
        print(f"    {tier}: {count}h")

    print("\n" + "=" * 70)
    print("BACKTEST: WINTER STORM ELLIOTT (PJM, Dec 2022)")
    print("=" * 70)
    elliott_result = run_elliott_real()

    print(f"\n  Max GSI:          {elliott_result.max_gsi:.1f}")
    print(f"  Max Tier:         {elliott_result.max_tier.name}")
    print(f"  First Watch:      {elliott_result.first_watch}")
    print(f"  First Advisory:   {elliott_result.first_advisory}")
    print(f"  First Alert:      {elliott_result.first_alert}")

    pjm_cwa_time = "2022-12-23T18:00"
    lead = elliott_result.lead_time_hours(pjm_cwa_time)
    if lead is not None:
        print(f"\n  ** LEAD TIME vs PJM Cold Weather Alert: {lead:.1f} hours **")

    pjm_maxgen_time = "2022-12-24T04:30"
    lead_mg = elliott_result.lead_time_hours(pjm_maxgen_time)
    if lead_mg is not None:
        print(f"  ** LEAD TIME vs PJM Max Gen Alert:     {lead_mg:.1f} hours **")

    print(f"\n  Total hours analyzed: {len(elliott_result.actions)}")
    tier_counts = {}
    for a in elliott_result.actions:
        tier_counts[a.tier.name] = tier_counts.get(a.tier.name, 0) + 1
    for tier, count in sorted(tier_counts.items()):
        print(f"    {tier}: {count}h")
