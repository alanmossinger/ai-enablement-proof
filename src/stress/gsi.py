"""Grid Stress Index (GSI) engine — transparent, published formula.

The GSI converts forecasts + anomalies into a stress score per BA per hour,
mapped to five calibrated alert tiers. The formula is published, not a black box.

GSI Components:
1. Reserve margin stress: how close demand is to capacity
2. Forecast error stress: divergence between forecast and actual
3. Ramp rate stress: rapid demand changes
4. Weather stress: extreme temperatures driving load
5. Interchange stress: unusual cross-BA flow patterns
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum


class AlertTier(IntEnum):
    """Five graduated alert tiers."""

    WATCH = 1  # Elevated awareness
    ADVISORY = 2  # Prepare contingency plans
    ALERT = 3  # Activate demand response, verify reserves
    EMERGENCY_WATCH = 4  # Pre-position emergency resources
    CRITICAL = 5  # Imminent grid stress; all hands


# Tier thresholds on the 0-100 GSI scale
TIER_THRESHOLDS: dict[AlertTier, float] = {
    AlertTier.WATCH: 30.0,
    AlertTier.ADVISORY: 50.0,
    AlertTier.ALERT: 65.0,
    AlertTier.EMERGENCY_WATCH: 80.0,
    AlertTier.CRITICAL: 90.0,
}


@dataclass
class GSIResult:
    """Grid Stress Index computation result for one BA-hour."""

    ba_code: str
    period: str
    gsi: float
    tier: AlertTier
    components: dict[str, float]


def classify_tier(gsi: float) -> AlertTier:
    """Map a GSI score to an alert tier."""
    for tier in reversed(AlertTier):
        if gsi >= TIER_THRESHOLDS[tier]:
            return tier
    return AlertTier.WATCH  # Below all thresholds = still Watch baseline


def compute_reserve_margin_stress(
    demand_mw: float,
    capacity_mw: float,
) -> float:
    """Score 0-100 based on how tight the reserve margin is.

    Reserve margin = (capacity - demand) / capacity.
    Stress rises as margin shrinks below 15%.
    """
    if capacity_mw <= 0:
        return 100.0

    margin = (capacity_mw - demand_mw) / capacity_mw

    if margin >= 0.15:
        return 0.0
    if margin <= 0.0:
        return 100.0

    # Linear scale: 15% margin = 0 stress, 0% margin = 100 stress
    return (1 - margin / 0.15) * 100


def compute_forecast_error_stress(
    forecast_mw: float,
    actual_mw: float,
) -> float:
    """Score 0-100 based on forecast miss magnitude.

    Large under-forecasts (actual >> forecast) are more dangerous.
    """
    if forecast_mw <= 0:
        return 50.0

    error_pct = (actual_mw - forecast_mw) / forecast_mw * 100

    if error_pct <= 0:
        # Over-forecast (actual < forecast) — less dangerous
        return min(abs(error_pct) * 2, 30)

    # Under-forecast — more dangerous
    return min(error_pct * 5, 100)


def compute_ramp_stress(
    demand_current: float,
    demand_prev: float,
    typical_ramp: float = 2000.0,
) -> float:
    """Score 0-100 based on demand ramp rate vs. typical.

    Rapid ramps stress generation dispatch.
    """
    if typical_ramp <= 0:
        return 50.0

    ramp = abs(demand_current - demand_prev)
    ratio = ramp / typical_ramp

    if ratio <= 1.0:
        return 0.0
    if ratio >= 3.0:
        return 100.0

    return (ratio - 1) / 2 * 100


def compute_weather_stress(
    temp_c: float | None,
    cold_threshold: float = -5.0,
    hot_threshold: float = 35.0,
) -> float:
    """Score 0-100 based on temperature extremes.

    Extreme cold (heating) and extreme heat (cooling) drive load spikes.
    """
    if temp_c is None:
        return 0.0

    if temp_c <= cold_threshold:
        # Extreme cold — stress increases as temp drops
        excess = cold_threshold - temp_c
        return min(excess * 10, 100)

    if temp_c >= hot_threshold:
        # Extreme heat — stress increases as temp rises
        excess = temp_c - hot_threshold
        return min(excess * 10, 100)

    return 0.0


def compute_gsi(
    ba_code: str,
    period: str,
    demand_mw: float,
    capacity_mw: float,
    forecast_mw: float,
    demand_prev_mw: float,
    temp_c: float | None = None,
    typical_ramp: float = 2000.0,
    weights: dict[str, float] | None = None,
) -> GSIResult:
    """Compute the Grid Stress Index for one BA-hour.

    The formula is a weighted sum of component scores, each 0-100.
    Default weights emphasize reserve margin (the most direct stress signal).
    """
    if weights is None:
        weights = {
            "reserve_margin": 0.40,
            "forecast_error": 0.25,
            "ramp": 0.15,
            "weather": 0.20,
        }

    components = {
        "reserve_margin": compute_reserve_margin_stress(demand_mw, capacity_mw),
        "forecast_error": compute_forecast_error_stress(forecast_mw, demand_mw),
        "ramp": compute_ramp_stress(demand_mw, demand_prev_mw, typical_ramp),
        "weather": compute_weather_stress(temp_c),
    }

    gsi = sum(weights[k] * components[k] for k in weights)
    gsi = round(min(gsi, 100.0), 2)
    tier = classify_tier(gsi)

    return GSIResult(
        ba_code=ba_code,
        period=period,
        gsi=gsi,
        tier=tier,
        components=components,
    )
