# AI-Enablement-Proof

## A Governed Autonomous Agent for Grid Reliability Across the U.S. Power System

*Autonomy you can audit. Govern the machine, or the machine governs you.*

---

Most AI agent demos automate paperwork. This one watches the North American power grid,
detects reliability stress hours before operators declare emergencies, drafts
operator-grade advisories -- and every single action passes through a codified governance
gate with a full audit trail.

Replayed against real grid emergencies (Winter Storm Uri, Winter Storm Elliott, Western
heat domes), the agent's detection lead time **and its false-alarm rate** are measured,
published, and reproducible from public federal data.

**This is what "AI agent enablement" means when an operator builds it: autonomy you can audit.**

---

### The Agent Loop

```
        GOVERNANCE CHASSIS
        (every arrow passes through a coded gate)

  OBSERVE --> ORIENT --> DECIDE --> RECOMMEND --> LOG
  EIA-930     Forecasts   Grid       Graduated     Immutable
  NOAA wx     + anomaly   Stress     alerts +      audit
  ERCOT/NERC  detection   Index      playbook      trail
  archives                engine     actions       (JSONL)
```

### The Autonomy Ladder

| Level | Name | Agent Behavior |
|-------|------|----------------|
| L0 | Observe | Collects and displays data |
| L1 | Describe | Summarizes state, no judgment |
| L2 | Predict | Forecasts with uncertainty |
| L3 | Recommend | Proposes actions + rationale |
| L4 | Act-with-veto | Executes unless vetoed (simulation only) |
| L5 | Autonomous | **Prohibited -- enforced by CI test** |

The repo contains `test_no_L5.py`, a required CI check that fails the build if any code
path attempts an L5 action. Governance as a merge blocker, not a slide.

---

### Data Sources

All public. All citable. All reproducible.

- **EIA-930** (API v2) -- hourly demand, generation by fuel, interchange for ~65 U.S. BAs
- **NOAA/NWS** -- temperature forecasts and actuals for BA load centers
- **ERCOT public archives** -- EEA declarations and notices
- **NERC/FERC reports** -- post-event analyses (Uri, Elliott)

---

### Portfolio Context

| Project | Claim |
|---------|-------|
| [Forecast-to-Dispatch](https://github.com/alanmossinger/forecast-to-dispatch) | Governed AI captures audited market value (86.1% revenue capture) |
| **AI-Enablement-Proof** | **A governed autonomous agent on critical infrastructure -- safely** |

---

*Status: Phase 0 -- Foundation. See [PROJECT_PLAN.md](PROJECT_PLAN.md) for the full build plan.*
