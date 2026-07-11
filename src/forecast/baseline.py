"""LightGBM baseline forecast model for per-BA load prediction.

Simple baselines reported first and honestly (Anti-Fabrication Rule 7).
This is the model that must be beaten before adding complexity.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import lightgbm as lgb
import numpy as np
import pandas as pd

from .features import FEATURE_COLS, TARGET_COL

logger = logging.getLogger(__name__)


@dataclass
class ForecastMetrics:
    """Evaluation metrics for a forecast model."""

    ba_code: str
    model_name: str
    n_samples: int
    mae_mw: float
    rmse_mw: float
    mape_pct: float
    evaluated_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def train_lgb_model(
    train_df: pd.DataFrame,
    feature_cols: list[str] | None = None,
    target_col: str = TARGET_COL,
) -> lgb.Booster:
    """Train a LightGBM model on the feature matrix."""
    if feature_cols is None:
        feature_cols = FEATURE_COLS

    # Drop rows with missing target or all-missing features
    available_cols = [c for c in feature_cols if c in train_df.columns]
    df = train_df[available_cols + [target_col]].dropna(subset=[target_col])

    if len(df) < 48:
        raise ValueError(f"Too few training samples: {len(df)} (need >= 48)")

    X = df[available_cols]
    y = df[target_col]

    train_data = lgb.Dataset(X, label=y, feature_name=available_cols)

    params = {
        "objective": "regression",
        "metric": "mae",
        "num_leaves": 31,
        "learning_rate": 0.05,
        "feature_fraction": 0.8,
        "bagging_fraction": 0.8,
        "bagging_freq": 5,
        "verbose": -1,
    }

    model = lgb.train(
        params,
        train_data,
        num_boost_round=200,
    )

    return model


def predict(
    model: lgb.Booster,
    test_df: pd.DataFrame,
    feature_cols: list[str] | None = None,
) -> pd.Series:
    """Generate predictions from a trained model."""
    if feature_cols is None:
        feature_cols = FEATURE_COLS

    available_cols = [c for c in feature_cols if c in test_df.columns]
    X = test_df[available_cols]
    preds = model.predict(X)
    return pd.Series(preds, index=test_df.index, name="predicted_mw")


def evaluate(
    actual: pd.Series,
    predicted: pd.Series,
    ba_code: str,
    model_name: str = "lgb_baseline",
) -> ForecastMetrics:
    """Compute forecast evaluation metrics."""
    mask = actual.notna() & predicted.notna()
    a = actual[mask].values
    p = predicted[mask].values

    if len(a) == 0:
        raise ValueError("No valid samples for evaluation")

    errors = a - p
    mae = float(np.mean(np.abs(errors)))
    rmse = float(np.sqrt(np.mean(errors**2)))

    # MAPE: avoid division by zero
    nonzero = a != 0
    if nonzero.any():
        mape = float(np.mean(np.abs(errors[nonzero] / a[nonzero])) * 100)
    else:
        mape = float("inf")

    return ForecastMetrics(
        ba_code=ba_code,
        model_name=model_name,
        n_samples=len(a),
        mae_mw=round(mae, 1),
        rmse_mw=round(rmse, 1),
        mape_pct=round(mape, 2),
        evaluated_at=datetime.now(UTC).isoformat(),
    )


def save_metrics(metrics: ForecastMetrics, output_dir: str = "data") -> Path:
    """Save metrics as a JSON artifact."""
    path = Path(output_dir) / f"metrics_{metrics.ba_code}_{metrics.model_name}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(metrics.to_dict(), f, indent=2)
    logger.info("Metrics saved to %s", path)
    return path


def save_model(model: lgb.Booster, ba_code: str, output_dir: str = "models") -> Path:
    """Save trained model."""
    path = Path(output_dir) / f"lgb_{ba_code}.txt"
    path.parent.mkdir(parents=True, exist_ok=True)
    model.save_model(str(path))
    logger.info("Model saved to %s", path)
    return path
