"""Feature engineering for load/net-load forecasting.

Builds feature matrices from the point-in-time store. All features use
only data available at the forecast moment (strict as-of discipline).
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd

from src.ingest.store import as_of_demand, as_of_weather


def build_demand_features(
    conn,
    ba_code: str,
    period_start: datetime,
    period_end: datetime,
    as_of: datetime,
) -> pd.DataFrame:
    """Build feature matrix for demand forecasting from point-in-time data.

    Features:
    - Calendar: hour_of_day, day_of_week, month, is_weekend
    - Lag demand: lag_1h, lag_24h, lag_168h (1 week)
    - Rolling stats: rolling_24h_mean, rolling_24h_std
    - Day-ahead forecast (EIA's own forecast as a feature)
    """
    # Fetch demand with enough history for lag features (8 days back)
    lookback = timedelta(days=8)
    rows = as_of_demand(conn, ba_code, period_start - lookback, period_end, as_of)

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df["period"] = pd.to_datetime(df["period"], utc=True)
    df = df.sort_values("period").set_index("period")

    # Calendar features
    df["hour_of_day"] = df.index.hour
    df["day_of_week"] = df.index.dayofweek
    df["month"] = df.index.month
    df["is_weekend"] = (df.index.dayofweek >= 5).astype(int)

    # Lag features (only use past data — no lookahead)
    df["lag_1h"] = df["demand_mw"].shift(1)
    df["lag_24h"] = df["demand_mw"].shift(24)
    df["lag_168h"] = df["demand_mw"].shift(168)

    # Rolling statistics
    df["rolling_24h_mean"] = df["demand_mw"].shift(1).rolling(24, min_periods=12).mean()
    df["rolling_24h_std"] = df["demand_mw"].shift(1).rolling(24, min_periods=12).std()

    # EIA day-ahead forecast as feature
    df["eia_forecast"] = df["forecast_mw"]

    # Trim to requested period (remove lookback rows)
    period_start_utc = pd.Timestamp(period_start, tz="UTC")
    period_end_utc = pd.Timestamp(period_end, tz="UTC")
    df = df.loc[period_start_utc:period_end_utc]

    return df


def add_weather_features(
    df: pd.DataFrame,
    conn,
    ba_code: str,
    as_of: datetime,
) -> pd.DataFrame:
    """Add temperature features from weather observations."""
    if df.empty:
        return df

    period_start = df.index.min().to_pydatetime()
    period_end = df.index.max().to_pydatetime() + timedelta(hours=1)

    # Fetch weather with lookback for lags
    lookback = timedelta(days=2)
    wx_rows = as_of_weather(conn, ba_code, period_start - lookback, period_end, as_of)

    if not wx_rows:
        df["temp_c"] = None
        df["temp_lag_24h"] = None
        return df

    wx = pd.DataFrame(wx_rows)
    wx["period"] = pd.to_datetime(wx["period"], utc=True)
    # Average across stations for the BA
    wx = wx.groupby("period")["temp_c"].mean().sort_index()

    df["temp_c"] = wx.reindex(df.index)
    df["temp_lag_24h"] = wx.shift(24).reindex(df.index)

    return df


FEATURE_COLS = [
    "hour_of_day",
    "day_of_week",
    "month",
    "is_weekend",
    "lag_1h",
    "lag_24h",
    "lag_168h",
    "rolling_24h_mean",
    "rolling_24h_std",
    "eia_forecast",
    "temp_c",
    "temp_lag_24h",
]

TARGET_COL = "demand_mw"
