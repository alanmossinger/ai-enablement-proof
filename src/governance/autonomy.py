"""Autonomy level definitions and enforcement.

The six-level autonomy ladder classifies every agent action.
The governance chassis enforces maximum permitted levels per action class.
L5 (fully autonomous) is **prohibited** — enforced by CI test.
"""

from enum import IntEnum


class AutonomyLevel(IntEnum):
    """Six-level autonomy ladder for agent actions."""

    OBSERVE = 0  # Collects and displays data
    DESCRIBE = 1  # Summarizes state, no judgment
    PREDICT = 2  # Forecasts with uncertainty
    RECOMMEND = 3  # Proposes actions + rationale
    ACT_WITH_VETO = 4  # Executes unless vetoed in window
    AUTONOMOUS = 5  # PROHIBITED — never granted


# Maximum permitted autonomy level per action class.
# L5 is never listed here — it is structurally impossible to permit.
MAX_PERMITTED_LEVEL: dict[str, AutonomyLevel] = {
    "data_ingestion": AutonomyLevel.OBSERVE,
    "grid_digest": AutonomyLevel.DESCRIBE,
    "load_forecast": AutonomyLevel.PREDICT,
    "net_load_forecast": AutonomyLevel.PREDICT,
    "alert_tier_1": AutonomyLevel.RECOMMEND,
    "alert_tier_2": AutonomyLevel.RECOMMEND,
    "alert_tier_3": AutonomyLevel.RECOMMEND,
    "alert_tier_4": AutonomyLevel.ACT_WITH_VETO,
    "alert_tier_5": AutonomyLevel.ACT_WITH_VETO,
}


def check_autonomy(action_class: str, requested_level: AutonomyLevel) -> bool:
    """Return True if the requested autonomy level is permitted for this action class.

    Raises ValueError if L5 is requested (hard prohibition).
    Returns False if the action class is unknown or exceeds its max level.
    """
    if requested_level == AutonomyLevel.AUTONOMOUS:
        raise ValueError(
            f"L5 (AUTONOMOUS) requested for '{action_class}'. "
            "L5 is prohibited. This is a governance violation."
        )

    max_level = MAX_PERMITTED_LEVEL.get(action_class)
    if max_level is None:
        return False  # Unknown action class — deny by default

    return requested_level <= max_level
