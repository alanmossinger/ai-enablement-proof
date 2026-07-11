"""Tests for the Grid Stress Index engine.

Validates GSI formula, tier classification, and component scoring.
"""

from src.stress.gsi import (
    AlertTier,
    classify_tier,
    compute_forecast_error_stress,
    compute_gsi,
    compute_ramp_stress,
    compute_reserve_margin_stress,
    compute_weather_stress,
)

# --- Reserve margin stress ---


def test_reserve_margin_healthy():
    """15%+ reserve margin = zero stress."""
    assert compute_reserve_margin_stress(85000, 100000) == 0.0


def test_reserve_margin_zero():
    """Zero reserve margin = max stress."""
    assert compute_reserve_margin_stress(100000, 100000) == 100.0


def test_reserve_margin_negative():
    """Demand exceeding capacity = max stress."""
    assert compute_reserve_margin_stress(110000, 100000) == 100.0


def test_reserve_margin_tight():
    """5% margin should produce ~67% stress (linear scale)."""
    stress = compute_reserve_margin_stress(95000, 100000)
    assert 60 < stress < 75


# --- Forecast error stress ---


def test_forecast_error_perfect():
    """Perfect forecast = zero stress."""
    assert compute_forecast_error_stress(50000, 50000) == 0.0


def test_forecast_error_underforecast():
    """Under-forecast (actual > forecast) is dangerous."""
    stress = compute_forecast_error_stress(50000, 55000)
    assert stress > 30


def test_forecast_error_overforecast():
    """Over-forecast (actual < forecast) is less dangerous."""
    stress = compute_forecast_error_stress(50000, 45000)
    assert stress < 30


# --- Ramp stress ---


def test_ramp_normal():
    """Normal ramp (within typical) = zero stress."""
    assert compute_ramp_stress(50000, 49000, typical_ramp=2000) == 0.0


def test_ramp_extreme():
    """3x typical ramp = max stress."""
    assert compute_ramp_stress(56000, 50000, typical_ramp=2000) == 100.0


# --- Weather stress ---


def test_weather_moderate():
    """Moderate temperature = zero stress."""
    assert compute_weather_stress(20.0) == 0.0


def test_weather_extreme_cold():
    """Extreme cold drives stress."""
    stress = compute_weather_stress(-15.0)
    assert stress == 100.0


def test_weather_extreme_heat():
    """Extreme heat drives stress."""
    stress = compute_weather_stress(40.0)
    assert stress == 50.0


def test_weather_none():
    """Missing temperature = no weather stress contribution."""
    assert compute_weather_stress(None) == 0.0


# --- GSI composite ---


def test_gsi_normal_conditions():
    """Normal grid conditions produce low GSI (Watch tier)."""
    result = compute_gsi(
        ba_code="ERCO",
        period="2021-02-10T12:00",
        demand_mw=50000,
        capacity_mw=80000,
        forecast_mw=50000,
        demand_prev_mw=49000,
        temp_c=20.0,
    )
    assert result.gsi < 30
    assert result.tier == AlertTier.WATCH


def test_gsi_uri_like_stress():
    """Uri-like conditions: tight margin, extreme cold, high demand."""
    result = compute_gsi(
        ba_code="ERCO",
        period="2021-02-15T06:00",
        demand_mw=72000,
        capacity_mw=75000,
        forecast_mw=60000,
        demand_prev_mw=65000,
        temp_c=-15.0,
    )
    assert result.gsi > 65
    assert result.tier >= AlertTier.ALERT


def test_gsi_returns_all_components():
    """GSI result includes all four component scores."""
    result = compute_gsi(
        ba_code="TEST",
        period="2021-01-01T00:00",
        demand_mw=50000,
        capacity_mw=80000,
        forecast_mw=50000,
        demand_prev_mw=49000,
    )
    assert "reserve_margin" in result.components
    assert "forecast_error" in result.components
    assert "ramp" in result.components
    assert "weather" in result.components


def test_gsi_capped_at_100():
    """GSI never exceeds 100."""
    result = compute_gsi(
        ba_code="TEST",
        period="2021-01-01T00:00",
        demand_mw=100000,
        capacity_mw=80000,
        forecast_mw=50000,
        demand_prev_mw=80000,
        temp_c=-20.0,
    )
    assert result.gsi <= 100


# --- Tier classification ---


def test_tier_watch():
    assert classify_tier(10) == AlertTier.WATCH


def test_tier_advisory():
    assert classify_tier(55) == AlertTier.ADVISORY


def test_tier_alert():
    assert classify_tier(70) == AlertTier.ALERT


def test_tier_emergency_watch():
    assert classify_tier(85) == AlertTier.EMERGENCY_WATCH


def test_tier_critical():
    assert classify_tier(95) == AlertTier.CRITICAL
