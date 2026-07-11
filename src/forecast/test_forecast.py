"""Tests for the forecast engine — LightGBM baseline.

Tests use synthetic data to verify the pipeline works end-to-end
without requiring real EIA data or API keys.
"""

from datetime import UTC, datetime

import numpy as np
import pandas as pd
import pytest

from src.forecast.baseline import ForecastMetrics, evaluate, predict, train_lgb_model
from src.forecast.features import TARGET_COL


def _make_synthetic_df(n_hours: int = 336) -> pd.DataFrame:
    """Create synthetic demand data with realistic patterns.

    Generates 14 days of hourly data with:
    - Diurnal cycle (higher during day)
    - Weekly pattern (lower on weekends)
    - Noise
    """
    rng = np.random.default_rng(42)
    start = datetime(2021, 1, 1, tzinfo=UTC)
    index = pd.date_range(start, periods=n_hours, freq="h", tz="UTC")

    hours = np.arange(n_hours)
    hour_of_day = hours % 24
    day_of_week = (hours // 24) % 7

    # Base load + diurnal cycle + weekly pattern
    base = 40000
    diurnal = 10000 * np.sin(np.pi * (hour_of_day - 6) / 12)
    diurnal = np.clip(diurnal, 0, 10000)
    weekend_effect = -3000 * (day_of_week >= 5).astype(float)
    noise = rng.normal(0, 500, n_hours)
    demand = base + diurnal + weekend_effect + noise

    df = pd.DataFrame(
        {
            TARGET_COL: demand,
            "forecast_mw": demand + rng.normal(0, 300, n_hours),
            "net_gen_mw": demand * 0.95 + rng.normal(0, 200, n_hours),
            "hour_of_day": hour_of_day,
            "day_of_week": day_of_week,
            "month": 1,
            "is_weekend": (day_of_week >= 5).astype(int),
            "lag_1h": np.roll(demand, 1),
            "lag_24h": np.roll(demand, 24),
            "lag_168h": np.roll(demand, 168),
            "eia_forecast": demand + rng.normal(0, 300, n_hours),
            "temp_c": 5.0 + 10 * np.sin(np.pi * (hour_of_day - 6) / 12) + rng.normal(0, 1, n_hours),
            "temp_lag_24h": None,
        },
        index=index,
    )

    # Fill rolling stats
    df["rolling_24h_mean"] = df[TARGET_COL].shift(1).rolling(24, min_periods=12).mean()
    df["rolling_24h_std"] = df[TARGET_COL].shift(1).rolling(24, min_periods=12).std()
    df["temp_lag_24h"] = df["temp_c"].shift(24)

    return df.iloc[168:]  # Drop first week (lag warmup)


def test_train_and_predict():
    """LightGBM trains and produces predictions with correct shape."""
    df = _make_synthetic_df()
    train_df = df.iloc[:-48]
    test_df = df.iloc[-48:]

    model = train_lgb_model(train_df)
    preds = predict(model, test_df)

    assert len(preds) == len(test_df)
    assert preds.notna().all()


def test_predictions_are_reasonable():
    """Predictions should be in the plausible demand range."""
    df = _make_synthetic_df()
    train_df = df.iloc[:-48]
    test_df = df.iloc[-48:]

    model = train_lgb_model(train_df)
    preds = predict(model, test_df)

    assert preds.min() > 20000, "Predictions unreasonably low"
    assert preds.max() < 80000, "Predictions unreasonably high"


def test_evaluate_metrics():
    """Evaluation produces valid metrics."""
    df = _make_synthetic_df()
    train_df = df.iloc[:-48]
    test_df = df.iloc[-48:]

    model = train_lgb_model(train_df)
    preds = predict(model, test_df)
    metrics = evaluate(test_df[TARGET_COL], preds, ba_code="SYNTH")

    assert metrics.mae_mw > 0
    assert metrics.rmse_mw >= metrics.mae_mw
    assert metrics.mape_pct > 0
    assert metrics.n_samples == 48
    assert metrics.ba_code == "SYNTH"


def test_mape_below_threshold():
    """Baseline MAPE on synthetic data should be reasonable (< 10%)."""
    df = _make_synthetic_df(n_hours=504)  # 3 weeks
    train_df = df.iloc[:-48]
    test_df = df.iloc[-48:]

    model = train_lgb_model(train_df)
    preds = predict(model, test_df)
    metrics = evaluate(test_df[TARGET_COL], preds, ba_code="SYNTH")

    assert metrics.mape_pct < 10, f"MAPE too high: {metrics.mape_pct}%"


def test_too_few_samples_raises():
    """Training with fewer than 48 samples should raise ValueError."""
    df = _make_synthetic_df()
    with pytest.raises(ValueError, match="Too few training samples"):
        train_lgb_model(df.iloc[:10])


def test_metrics_serialization():
    """ForecastMetrics round-trips to dict."""
    m = ForecastMetrics(
        ba_code="ERCO",
        model_name="lgb_baseline",
        n_samples=100,
        mae_mw=500.0,
        rmse_mw=700.0,
        mape_pct=3.5,
        evaluated_at="2021-02-14T00:00:00+00:00",
    )
    d = m.to_dict()
    assert d["ba_code"] == "ERCO"
    assert d["mape_pct"] == 3.5
