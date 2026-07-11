"""Backtest engine — replay historical events through the agent with point-in-time data.

Strict point-in-time discipline: backtests use only data available at
the decision moment. Lookahead is a project-invalidating bug.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime

from src.agent.loop import AgentAction, run_cycle
from src.governance.audit import AuditLogger
from src.stress.gsi import AlertTier

logger = logging.getLogger(__name__)


@dataclass
class BacktestEvent:
    """A known grid event used as ground truth."""

    name: str
    ba_code: str
    event_start: str  # ISO datetime
    event_end: str
    official_declarations: list[dict]  # [{time, level, description}]
    description: str


@dataclass
class BacktestResult:
    """Results from replaying the agent against a historical event."""

    event: BacktestEvent
    actions: list[AgentAction] = field(default_factory=list)
    escalation_timeline: list[dict] = field(default_factory=list)

    @property
    def first_watch(self) -> str | None:
        for a in self.actions:
            if a.tier >= AlertTier.WATCH:
                return a.period
        return None

    @property
    def first_advisory(self) -> str | None:
        for a in self.actions:
            if a.tier >= AlertTier.ADVISORY:
                return a.period
        return None

    @property
    def first_alert(self) -> str | None:
        for a in self.actions:
            if a.tier >= AlertTier.ALERT:
                return a.period
        return None

    @property
    def first_emergency(self) -> str | None:
        for a in self.actions:
            if a.tier >= AlertTier.EMERGENCY_WATCH:
                return a.period
        return None

    @property
    def first_critical(self) -> str | None:
        for a in self.actions:
            if a.tier >= AlertTier.CRITICAL:
                return a.period
        return None

    @property
    def max_tier(self) -> AlertTier:
        if not self.actions:
            return AlertTier.WATCH
        return max(a.tier for a in self.actions)

    @property
    def max_gsi(self) -> float:
        if not self.actions:
            return 0.0
        return max(a.gsi for a in self.actions)

    def lead_time_hours(self, official_time: str) -> float | None:
        """Hours between agent's first Alert+ and official declaration."""
        first = self.first_alert
        if first is None:
            return None
        agent_dt = datetime.fromisoformat(first)
        official_dt = datetime.fromisoformat(official_time)
        delta = official_dt - agent_dt
        return delta.total_seconds() / 3600

    def build_escalation_timeline(self) -> list[dict]:
        """Build the dual-swimlane timeline for visualization."""
        timeline = []
        prev_tier = None
        for a in self.actions:
            if a.tier != prev_tier:
                timeline.append(
                    {
                        "time": a.period,
                        "source": "agent",
                        "tier": a.tier.name,
                        "gsi": a.gsi,
                        "passed": a.passed_governance,
                    }
                )
                prev_tier = a.tier

        for decl in self.event.official_declarations:
            timeline.append(
                {
                    "time": decl["time"],
                    "source": "official",
                    "tier": decl["level"],
                    "gsi": None,
                    "passed": None,
                }
            )

        timeline.sort(key=lambda x: x["time"])
        self.escalation_timeline = timeline
        return timeline


# --- Ground truth events ---

URI_EVENT = BacktestEvent(
    name="Winter Storm Uri",
    ba_code="ERCO",
    event_start="2021-02-10T00:00",
    event_end="2021-02-20T00:00",
    official_declarations=[
        {"time": "2021-02-14T18:15", "level": "EEA1", "description": "ERCOT EEA Level 1"},
        {"time": "2021-02-15T01:25", "level": "EEA2", "description": "ERCOT EEA Level 2"},
        {"time": "2021-02-15T01:55", "level": "EEA3", "description": "ERCOT EEA Level 3"},
    ],
    description=(
        "February 2021 winter storm caused catastrophic grid failure in Texas. "
        "~4.5M customers lost power, estimated $130B in damages, 246 deaths. "
        "Source: FERC/NERC/Regional Entity Staff Report, November 2021."
    ),
)

ELLIOTT_EVENT = BacktestEvent(
    name="Winter Storm Elliott",
    ba_code="PJM",
    event_start="2022-12-20T00:00",
    event_end="2023-01-02T00:00",
    official_declarations=[
        {"time": "2022-12-23T18:00", "level": "Cold Weather Alert", "description": "PJM CWA"},
        {"time": "2022-12-24T04:30", "level": "Max Gen Alert", "description": "PJM Max Gen"},
        {"time": "2022-12-24T06:55", "level": "Max Gen Action", "description": "PJM Max Gen"},
    ],
    description=(
        "December 2022 winter storm across Eastern Interconnection. "
        "90 GW of generation outages across multiple BAs. "
        "Source: FERC/NERC/Regional Entity Staff Report, September 2023."
    ),
)


def run_backtest_synthetic(
    event: BacktestEvent,
    hourly_data: list[dict],
    audit: AuditLogger | None = None,
) -> BacktestResult:
    """Run a backtest using pre-prepared hourly data.

    Each entry in hourly_data should have:
    - period, demand_mw, capacity_mw, forecast_mw, demand_prev_mw, temp_c
    """
    if audit is None:
        audit = AuditLogger()

    result = BacktestResult(event=event)

    for row in hourly_data:
        action = run_cycle(
            ba_code=event.ba_code,
            period=row["period"],
            demand_mw=row["demand_mw"],
            capacity_mw=row["capacity_mw"],
            forecast_mw=row["forecast_mw"],
            demand_prev_mw=row["demand_prev_mw"],
            temp_c=row.get("temp_c"),
            audit=audit,
        )
        result.actions.append(action)

    result.build_escalation_timeline()
    return result
