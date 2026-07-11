"""Tests for the agent loop — governance integration.

Verifies the full OODA cycle: observe -> orient -> decide -> recommend -> gate -> log.
"""

import tempfile
from pathlib import Path

from src.agent.loop import run_cycle
from src.governance.audit import AuditLogger
from src.stress.gsi import AlertTier


def _make_audit() -> AuditLogger:
    """Create an audit logger in a temp directory."""
    tmp = tempfile.mkdtemp()
    return AuditLogger(Path(tmp) / "test_audit.jsonl")


def test_normal_conditions_produce_watch():
    """Normal grid conditions => Watch tier, action approved."""
    audit = _make_audit()
    action = run_cycle(
        ba_code="ERCO",
        period="2021-02-10T12:00",
        demand_mw=50000,
        capacity_mw=80000,
        forecast_mw=50000,
        demand_prev_mw=49000,
        temp_c=20.0,
        audit=audit,
    )
    assert action.tier == AlertTier.WATCH
    assert action.passed_governance
    assert len(action.blocked_gates) == 0


def test_uri_like_conditions_produce_high_tier():
    """Uri-like stress => Alert or higher, with governance approval."""
    audit = _make_audit()
    action = run_cycle(
        ba_code="ERCO",
        period="2021-02-15T06:00",
        demand_mw=72000,
        capacity_mw=75000,
        forecast_mw=60000,
        demand_prev_mw=65000,
        temp_c=-15.0,
        audit=audit,
    )
    assert action.tier >= AlertTier.ALERT
    assert action.gsi > 65
    assert action.passed_governance


def test_low_confidence_blocks_action():
    """Action with low confidence is blocked by the confidence gate."""
    audit = _make_audit()
    action = run_cycle(
        ba_code="ERCO",
        period="2021-02-15T06:00",
        demand_mw=72000,
        capacity_mw=75000,
        forecast_mw=60000,
        demand_prev_mw=65000,
        temp_c=-15.0,
        confidence=0.3,  # Below 0.6 threshold
        audit=audit,
    )
    assert not action.passed_governance
    assert "confidence" in action.blocked_gates


def test_audit_trail_complete():
    """Every agent cycle produces a complete audit chain."""
    audit = _make_audit()
    run_cycle(
        ba_code="ERCO",
        period="2021-02-10T12:00",
        demand_mw=50000,
        capacity_mw=80000,
        forecast_mw=50000,
        demand_prev_mw=49000,
        audit=audit,
    )

    entries = audit.read_all()
    event_types = [e["event_type"] for e in entries]

    # Full audit chain: observe -> stress -> recommend -> gate
    assert "observation" in event_types
    assert "stress_score" in event_types
    assert "recommendation" in event_types
    assert "gate_verdict" in event_types


def test_blocked_action_has_empty_playbook():
    """Blocked actions should not expose playbook actions."""
    audit = _make_audit()
    action = run_cycle(
        ba_code="ERCO",
        period="2021-02-15T06:00",
        demand_mw=72000,
        capacity_mw=75000,
        forecast_mw=60000,
        demand_prev_mw=65000,
        confidence=0.1,
        audit=audit,
    )
    assert not action.passed_governance
    assert action.playbook_actions == []


def test_blocked_action_logged():
    """Blocked actions produce an action_blocked audit event."""
    audit = _make_audit()
    run_cycle(
        ba_code="ERCO",
        period="2021-02-15T06:00",
        demand_mw=72000,
        capacity_mw=75000,
        forecast_mw=60000,
        demand_prev_mw=65000,
        confidence=0.1,
        audit=audit,
    )
    entries = audit.read_all()
    event_types = [e["event_type"] for e in entries]
    assert "action_blocked" in event_types
