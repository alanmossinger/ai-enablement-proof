# Deployment Gate Checklist

Generic, reusable checklist for deploying any AI agent in any organization.
Derived from `src/governance/` but abstracted for cross-project use.

## Pre-Deployment Gates

- [ ] **Autonomy level defined** -- action classes mapped to permitted levels
- [ ] **Confidence threshold set** -- minimum confidence for recommendations
- [ ] **Blast radius bounded** -- maximum scope of any single action
- [ ] **HITL routing configured** -- which actions require human approval
- [ ] **Audit trail active** -- append-only logging of all decisions
- [ ] **L5 prohibition tested** -- CI test confirms autonomous actions are blocked
- [ ] **Model card complete** -- NIST AI RMF aligned documentation
- [ ] **Data lineage documented** -- every input traceable to source
- [ ] **Point-in-time integrity verified** -- no lookahead in training or evaluation
- [ ] **False-positive rate published** -- honest error analysis, not hidden

## Operational Gates

- [ ] **Unattended run validated** -- agent runs N days with complete audit chains
- [ ] **Escalation path defined** -- who gets paged when the agent flags high severity
- [ ] **Degradation mode defined** -- agent behavior when data sources fail
- [ ] **Override mechanism tested** -- humans can override or stop the agent immediately
- [ ] **Monitoring dashboard live** -- real-time view of agent actions and gate verdicts

## Post-Deployment Gates

- [ ] **Value measurement active** -- business metrics tied to agent outputs
- [ ] **Counterfactual documented** -- what would have happened without the agent
- [ ] **Drift detection active** -- model performance monitored over time
- [ ] **Governance review scheduled** -- periodic review of autonomy levels and thresholds
