"""FastAPI app — current GSI, alerts, and audit queries.

Provides REST endpoints for:
- GET /gsi/{ba_code} — current Grid Stress Index
- GET /alerts — active alerts across all BAs
- GET /audit — query the audit trail
- GET /health — health check
"""

from __future__ import annotations

from fastapi import FastAPI, Query

from src.agent.loop import run_cycle
from src.governance.audit import AuditLogger

app = FastAPI(
    title="AI-Enablement-Proof",
    description="Governed autonomous agent for U.S. grid reliability",
    version="0.1.0",
)

audit = AuditLogger()


@app.get("/health")
def health():
    return {"status": "ok", "version": "0.1.0"}


@app.get("/gsi/{ba_code}")
def get_gsi(
    ba_code: str,
    demand_mw: float = Query(..., description="Current demand in MW"),
    capacity_mw: float = Query(..., description="Available capacity in MW"),
    forecast_mw: float = Query(..., description="Forecasted demand in MW"),
    demand_prev_mw: float = Query(..., description="Previous hour demand in MW"),
    temp_c: float | None = Query(None, description="Current temperature in Celsius"),
    confidence: float = Query(0.8, description="Model confidence score"),
):
    """Compute GSI and run the full agent cycle for a BA."""
    from datetime import UTC, datetime

    period = datetime.now(UTC).strftime("%Y-%m-%dT%H:00")

    action = run_cycle(
        ba_code=ba_code,
        period=period,
        demand_mw=demand_mw,
        capacity_mw=capacity_mw,
        forecast_mw=forecast_mw,
        demand_prev_mw=demand_prev_mw,
        temp_c=temp_c,
        confidence=confidence,
        audit=audit,
    )

    return {
        "ba_code": action.ba_code,
        "period": action.period,
        "gsi": action.gsi,
        "tier": action.tier.name,
        "passed_governance": action.passed_governance,
        "blocked_gates": action.blocked_gates,
        "playbook_actions": action.playbook_actions,
        "autonomy_level": action.autonomy_level.name,
        "action_id": action.action_id,
    }


@app.get("/audit")
def get_audit(
    limit: int = Query(100, description="Max entries to return"),
    event_type: str | None = Query(None, description="Filter by event type"),
):
    """Query the immutable audit trail."""
    entries = audit.read_all()

    if event_type:
        entries = [e for e in entries if e.get("event_type") == event_type]

    return {"total": len(entries), "entries": entries[-limit:]}
