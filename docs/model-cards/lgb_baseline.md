# Model Card: LightGBM Baseline Load Forecast

*NIST AI RMF aligned*

## Model Details

- **Name:** lgb_baseline
- **Type:** Gradient boosted trees (LightGBM)
- **Task:** Hourly load demand forecasting per balancing authority
- **Version:** 0.1.0
- **Author:** Alan Mossinger

## Intended Use

Short-horizon (1-48 hour) load demand forecasting for grid stress detection.
Used as the baseline model — must be beaten before adding complexity.

**Not intended for:** Operational grid dispatch, market bidding, or any
decision that affects physical grid state.

## Training Data

- **Source:** EIA-930 API v2 (hourly demand, day-ahead forecast, net generation)
- **Weather:** NOAA ISD hourly temperature observations
- **Point-in-time discipline:** All training data respects as-of semantics;
  no lookahead contamination

## Features

| Feature | Source | Description |
|---------|--------|-------------|
| hour_of_day | Calendar | 0-23 |
| day_of_week | Calendar | 0-6 (Mon-Sun) |
| month | Calendar | 1-12 |
| is_weekend | Calendar | Binary |
| lag_1h | EIA-930 | Demand 1 hour ago |
| lag_24h | EIA-930 | Demand 24 hours ago |
| lag_168h | EIA-930 | Demand 1 week ago |
| rolling_24h_mean | EIA-930 | 24h rolling mean (shifted 1h) |
| rolling_24h_std | EIA-930 | 24h rolling std (shifted 1h) |
| eia_forecast | EIA-930 | EIA's own day-ahead forecast |
| temp_c | NOAA ISD | Temperature in Celsius |
| temp_lag_24h | NOAA ISD | Temperature 24 hours ago |

## Hyperparameters

- num_leaves: 31
- learning_rate: 0.05
- feature_fraction: 0.8
- bagging_fraction: 0.8
- num_boost_round: 200

## Metrics

*To be populated after training on real data.*

| BA | MAE (MW) | RMSE (MW) | MAPE (%) | N samples |
|----|----------|-----------|----------|-----------|
| ERCO | TBD | TBD | TBD | TBD |
| PJM | TBD | TBD | TBD | TBD |

## Limitations

- No weather forecast features yet (uses observations only)
- Simple calendar features; no holiday calendar
- No cross-BA features (each BA modeled independently)
- Not tuned per BA (same hyperparameters everywhere)
- Baseline honesty: regions where this simple model wins over
  more complex models are highlighted, not hidden (F11)

## Ethical Considerations

- This is a demonstration system, not operational
- Predictions are never used for real grid dispatch
- False positive rates are published honestly
