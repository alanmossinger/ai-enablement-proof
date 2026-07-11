"""Governance gates -- coded constraints that every agent action must pass.

Gates are code, not prose. A recommendation that fails a gate is visibly blocked,
and the block is logged.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from .autonomy import AutonomyLevel, check_autonomy


@dataclass(frozen=True)
class GateResult:
    """Outcome of a single governance gate check."""

    gate_name: str
    passed: bool
    reason: str
    checked_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class GateVerdict:
    """Aggregate verdict from all governance gates for a single action."""

    action_class: str
    action_id: str
    results: list[GateResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(r.passed for r in self.results)

    @property
    def blocked_gates(self) -> list[GateResult]:
        return [r for r in self.results if not r.passed]


def confidence_gate(confidence: float, threshold: float = 0.6) -> GateResult:
    """Block recommendations below the confidence threshold."""
    passed = confidence >= threshold
    op = ">=" if passed else "<"
    return GateResult(
        gate_name="confidence",
        passed=passed,
        reason=f"Confidence {confidence:.3f} {op} threshold {threshold:.3f}",
        metadata={"confidence": confidence, "threshold": threshold},
    )


def blast_radius_gate(
    affected_bas: list[str],
    max_bas: int = 10,
) -> GateResult:
    """Block actions that affect too many balancing authorities at once."""
    count = len(affected_bas)
    passed = count <= max_bas
    op = "<=" if passed else ">"
    return GateResult(
        gate_name="blast_radius",
        passed=passed,
        reason=f"Affects {count} BAs ({op} limit {max_bas})",
        metadata={"affected_bas": affected_bas, "count": count, "max": max_bas},
    )


def autonomy_gate(action_class: str, requested_level: AutonomyLevel) -> GateResult:
    """Enforce the autonomy ladder -- L5 raises, others check max permitted."""
    try:
        passed = check_autonomy(action_class, requested_level)
        status = "permitted" if passed else "exceeds max"
        return GateResult(
            gate_name="autonomy",
            passed=passed,
            reason=f"Level {requested_level.name} for '{action_class}': {status}",
            metadata={"action_class": action_class, "level": requested_level.value},
        )
    except ValueError as e:
        return GateResult(
            gate_name="autonomy",
            passed=False,
            reason=str(e),
            metadata={"action_class": action_class, "level": requested_level.value},
        )


def hitl_routing_gate(
    autonomy_level: AutonomyLevel,
    requires_human: bool | None = None,
) -> GateResult:
    """Determine human-in-the-loop routing.

    L3+ actions require human approval by default.
    """
    if requires_human is None:
        requires_human = autonomy_level >= AutonomyLevel.RECOMMEND

    hitl_status = "required" if requires_human else "not required"
    return GateResult(
        gate_name="hitl_routing",
        passed=True,
        reason=f"HITL {hitl_status} at level {autonomy_level.name}",
        metadata={"requires_human": requires_human, "level": autonomy_level.value},
    )


def run_all_gates(
    action_class: str,
    action_id: str,
    confidence: float,
    affected_bas: list[str],
    requested_level: AutonomyLevel,
) -> GateVerdict:
    """Run the full governance gate sequence for an agent action."""
    verdict = GateVerdict(action_class=action_class, action_id=action_id)
    verdict.results.append(confidence_gate(confidence))
    verdict.results.append(blast_radius_gate(affected_bas))
    verdict.results.append(autonomy_gate(action_class, requested_level))
    verdict.results.append(hitl_routing_gate(requested_level))
    return verdict
