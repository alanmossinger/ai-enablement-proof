"""Tests for the backtest engine — Uri simulation with synthetic data.

Uses a synthetic demand curve that mimics Uri's signature:
rising demand, collapsing capacity, extreme cold.
"""

import tempfile
from pathlib import Path

from src.governance.audit import AuditLogger
from src.stress.backtest import URI_EVENT, run_backtest_synthetic
from src.stress.gsi import AlertTier


def _make_audit() -> AuditLogger:
    tmp = tempfile.mkdtemp()
    return AuditLogger(Path(tmp) / "backtest_audit.jsonl")


def _generate_uri_synthetic() -> list[dict]:
    """Generate synthetic hourly data mimicking Uri's progression.

    Feb 10-19: demand rises, capacity drops, temperature plunges.
    """
    hours = []
    for day in range(10, 20):
        for hour in range(24):
            idx = (day - 10) * 24 + hour
            period = f"2021-02-{day:02d}T{hour:02d}:00"

            # Demand rises as heating load increases (Uri peaked ~69 GW)
            base_demand = 50000 + idx * 100
            # Capacity collapses after day 14 (generators freezing)
            # Uri reality: ~80GW -> ~45GW available in ~12 hours
            if day < 14:
                capacity = 80000
            elif day == 14:
                capacity = 80000 - hour * 1500  # Rapid collapse
            elif day == 15:
                capacity = 56000 - hour * 300
            else:
                capacity = max(55000, 70000 - (day - 14) * 3000)
            capacity = max(capacity, 45000)

            # Temperature plunges (Uri: Dallas hit -18C)
            if day < 13:
                temp = 5.0 - day * 0.5
            elif day < 16:
                temp = -5.0 - (day - 13) * 6
            else:
                temp = -17.0 + (day - 16) * 5

            # Forecast lags reality (under-forecasts the surge)
            forecast = base_demand * 0.88

            demand = min(base_demand, capacity + 2000)
            prev_demand = demand - 100 if idx > 0 else demand

            hours.append(
                {
                    "period": period,
                    "demand_mw": demand,
                    "capacity_mw": capacity,
                    "forecast_mw": forecast,
                    "demand_prev_mw": prev_demand,
                    "temp_c": temp,
                }
            )

    return hours


def test_uri_backtest_detects_stress():
    """Agent should escalate to Alert+ during Uri simulation."""
    audit = _make_audit()
    data = _generate_uri_synthetic()
    result = run_backtest_synthetic(URI_EVENT, data, audit)

    assert result.max_tier >= AlertTier.ALERT
    assert result.max_gsi > 50


def test_uri_backtest_escalates_before_eea3():
    """Agent should reach Alert tier before the official EEA3 declaration."""
    audit = _make_audit()
    data = _generate_uri_synthetic()
    result = run_backtest_synthetic(URI_EVENT, data, audit)

    eea3_time = "2021-02-15T01:55"
    lead = result.lead_time_hours(eea3_time)

    assert lead is not None, "Agent never reached Alert tier"
    assert lead > 0, f"Agent escalated AFTER EEA3 (lead={lead}h)"


def test_uri_backtest_has_complete_audit():
    """Every backtest hour should produce audit entries."""
    audit = _make_audit()
    data = _generate_uri_synthetic()
    run_backtest_synthetic(URI_EVENT, data, audit)

    entries = audit.read_all()
    assert len(entries) > 0

    event_types = {e["event_type"] for e in entries}
    assert "observation" in event_types
    assert "stress_score" in event_types
    assert "gate_verdict" in event_types


def test_uri_escalation_timeline():
    """Escalation timeline should include both agent and official events."""
    audit = _make_audit()
    data = _generate_uri_synthetic()
    result = run_backtest_synthetic(URI_EVENT, data, audit)

    timeline = result.escalation_timeline
    sources = {e["source"] for e in timeline}
    assert "agent" in sources
    assert "official" in sources


def test_backtest_result_properties():
    """BacktestResult exposes first-escalation times per tier."""
    audit = _make_audit()
    data = _generate_uri_synthetic()
    result = run_backtest_synthetic(URI_EVENT, data, audit)

    assert result.first_watch is not None
    assert len(result.actions) == len(data)


def test_false_alarm_quiet_period():
    """Quiet conditions should produce mostly Watch tier (low false alarm rate)."""
    audit = _make_audit()

    quiet_data = []
    for hour in range(168):  # 1 week
        day = 1 + hour // 24
        h = hour % 24
        quiet_data.append(
            {
                "period": f"2021-06-{day:02d}T{h:02d}:00",
                "demand_mw": 45000 + 5000 * (0.5 if 8 <= h <= 20 else 0),
                "capacity_mw": 80000,
                "forecast_mw": 45000 + 5000 * (0.5 if 8 <= h <= 20 else 0),
                "demand_prev_mw": 44900 + 5000 * (0.5 if 7 <= h <= 19 else 0),
                "temp_c": 25.0,
            }
        )

    result = run_backtest_synthetic(URI_EVENT, quiet_data, audit)

    alert_count = sum(1 for a in result.actions if a.tier >= AlertTier.ALERT)
    false_alarm_rate = alert_count / len(result.actions)
    assert false_alarm_rate < 0.05, f"False alarm rate too high: {false_alarm_rate:.1%}"
