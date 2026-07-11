"""The agent loop — OODA inside a governance chassis.

OBSERVE -> ORIENT -> DECIDE -> RECOMMEND -> LOG

Every arrow passes through a coded governance gate.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass

from src.governance.audit import AuditLogger
from src.governance.autonomy import AutonomyLevel
from src.governance.gates import run_all_gates
from src.stress.gsi import AlertTier, compute_gsi

logger = logging.getLogger(__name__)


# Alert tier -> autonomy level mapping
TIER_AUTONOMY: dict[AlertTier, AutonomyLevel] = {
    AlertTier.WATCH: AutonomyLevel.DESCRIBE,
    AlertTier.ADVISORY: AutonomyLevel.RECOMMEND,
    AlertTier.ALERT: AutonomyLevel.RECOMMEND,
    AlertTier.EMERGENCY_WATCH: AutonomyLevel.RECOMMEND,
    AlertTier.CRITICAL: AutonomyLevel.ACT_WITH_VETO,
}

# Alert tier -> action class mapping
TIER_ACTION_CLASS: dict[AlertTier, str] = {
    AlertTier.WATCH: "grid_digest",
    AlertTier.ADVISORY: "alert_tier_2",
    AlertTier.ALERT: "alert_tier_3",
    AlertTier.EMERGENCY_WATCH: "alert_tier_4",
    AlertTier.CRITICAL: "alert_tier_5",
}


# Playbook actions per tier (operator language, not data-science language)
PLAYBOOK: dict[AlertTier, list[str]] = {
    AlertTier.WATCH: [
        "Continue normal monitoring cadence",
        "Log current reserve margin and forecast accuracy",
    ],
    AlertTier.ADVISORY: [
        "Increase monitoring frequency to 30-minute intervals",
        "Review next-24h load forecast against capacity projections",
        "Verify demand response program readiness",
    ],
    AlertTier.ALERT: [
        "Activate demand response standby notifications",
        "Verify peaker fuel supply and start-up readiness",
        "Defer any planned maintenance outages in the affected BA",
        "Coordinate with neighboring BAs on interchange capacity",
    ],
    AlertTier.EMERGENCY_WATCH: [
        "Pre-position emergency demand response for activation",
        "Notify executive operations leadership",
        "Verify firm load-shed rotation plans are current",
        "Coordinate with state emergency management if weather-driven",
    ],
    AlertTier.CRITICAL: [
        "Recommend immediate demand response activation",
        "Escalate to chief operations officer",
        "Prepare load-shed implementation if reserves breach minimum",
        "Issue public conservation appeal through established channels",
    ],
}


@dataclass
class AgentAction:
    """A recommended action from the agent loop."""

    action_id: str
    ba_code: str
    period: str
    tier: AlertTier
    gsi: float
    playbook_actions: list[str]
    passed_governance: bool
    blocked_gates: list[str]
    autonomy_level: AutonomyLevel


def run_cycle(
    ba_code: str,
    period: str,
    demand_mw: float,
    capacity_mw: float,
    forecast_mw: float,
    demand_prev_mw: float,
    temp_c: float | None = None,
    confidence: float = 0.8,
    audit: AuditLogger | None = None,
) -> AgentAction:
    """Execute one full agent cycle for a single BA-hour.

    OBSERVE -> ORIENT -> DECIDE -> RECOMMEND -> GATE -> LOG
    """
    if audit is None:
        audit = AuditLogger()

    action_id = str(uuid.uuid4())

    # --- OBSERVE ---
    audit.log_observation(
        source="agent_cycle",
        record_count=1,
        ba_code=ba_code,
        period=period,
    )

    # --- ORIENT + DECIDE: compute Grid Stress Index ---
    gsi_result = compute_gsi(
        ba_code=ba_code,
        period=period,
        demand_mw=demand_mw,
        capacity_mw=capacity_mw,
        forecast_mw=forecast_mw,
        demand_prev_mw=demand_prev_mw,
        temp_c=temp_c,
    )

    audit.log_stress_score(
        ba=ba_code,
        gsi=gsi_result.gsi,
        tier=gsi_result.tier.name,
        components=gsi_result.components,
    )

    # --- RECOMMEND: select playbook actions ---
    tier = gsi_result.tier
    autonomy = TIER_AUTONOMY[tier]
    action_class = TIER_ACTION_CLASS[tier]
    playbook_actions = PLAYBOOK[tier]

    summary = f"GSI={gsi_result.gsi:.1f} ({tier.name}): {len(playbook_actions)} actions"
    audit.log_recommendation(
        action_class=action_class,
        action_id=action_id,
        summary=summary,
    )

    # --- GATE: governance checks ---
    verdict = run_all_gates(
        action_class=action_class,
        action_id=action_id,
        confidence=confidence,
        affected_bas=[ba_code],
        requested_level=autonomy,
    )

    audit.log_gate_verdict(verdict)

    if not verdict.passed:
        blocked_names = [g.gate_name for g in verdict.blocked_gates]
        audit.log_block(action_id=action_id, blocked_gates=blocked_names)
        logger.warning(
            "Action %s BLOCKED by gates: %s",
            action_id,
            blocked_names,
        )
    else:
        logger.info(
            "Action %s APPROVED: %s tier %s",
            action_id,
            ba_code,
            tier.name,
        )

    return AgentAction(
        action_id=action_id,
        ba_code=ba_code,
        period=period,
        tier=tier,
        gsi=gsi_result.gsi,
        playbook_actions=playbook_actions if verdict.passed else [],
        passed_governance=verdict.passed,
        blocked_gates=[g.gate_name for g in verdict.blocked_gates],
        autonomy_level=autonomy,
    )
