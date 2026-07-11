# Autonomy Ladder

Every agent action is classified on a six-level ladder. The governance chassis
enforces the maximum permitted level per action class.

## Levels

| Level | Name | Agent Behavior | Human Role |
|-------|------|----------------|------------|
| L0 | Observe | Collects and displays data | Full control |
| L1 | Describe | Summarizes state, no judgment | Full control |
| L2 | Predict | Forecasts with uncertainty | Reviews |
| L3 | Recommend | Proposes actions + rationale | Approves/rejects |
| L4 | Act-with-veto | Executes unless vetoed in window | Veto power |
| L5 | Autonomous | **PROHIBITED** | N/A |

## Enforcement

- `src/governance/autonomy.py` defines the ladder and per-action-class limits
- `src/governance/test_no_L5.py` is a CI-blocking test that:
  1. Verifies L5 requests raise `ValueError`
  2. Confirms no action class permits L5
  3. Scans source code for L5 grant attempts
- The prohibition is **tested, not asserted**

## Action Class Mapping

| Action Class | Max Level | Rationale |
|-------------|-----------|-----------|
| data_ingestion | L0 (Observe) | Pure data collection |
| grid_digest | L1 (Describe) | Hourly summary |
| load_forecast | L2 (Predict) | Forecast with uncertainty |
| net_load_forecast | L2 (Predict) | Forecast with uncertainty |
| alert_tier_1-3 | L3 (Recommend) | Proposes, human approves |
| alert_tier_4-5 | L4 (Act-with-veto) | Simulation only |
