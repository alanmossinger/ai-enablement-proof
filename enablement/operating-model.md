# AI Enablement Operating Model

## Hub-and-Spoke Blueprint

The federated operating model separates infrastructure ownership (CIO territory)
from the enablement/value layer (governance, adoption, value realization).

### The Hub (AI Enablement Office)

- **Governance frameworks** — autonomy ladders, gate specifications, audit standards
- **Use-case portfolio discipline** — intake, prioritization, value measurement
- **Workforce AI literacy** — training, adoption tracking, capability building
- **Operating cadence** — weekly reviews, monthly scorecards, quarterly maturity assessments

### The Spokes (Business Units / Functions)

- **Domain expertise** — the subject matter that makes AI actions meaningful
- **Use-case identification** — closest to the problem, first to see opportunity
- **Adoption ownership** — the spoke owns workflow integration and change management
- **Value realization** — the spoke measures and reports business impact

### The Seam (Infrastructure vs. Enablement)

| Responsibility | Owner |
|---------------|-------|
| Cloud infrastructure, MLOps, model serving | CIO / Platform Engineering |
| Data pipelines, data quality, access controls | CIO / Data Engineering |
| Governance frameworks, autonomy policy | AI Enablement Hub |
| Use-case prioritization, value tracking | AI Enablement Hub |
| Model development, evaluation, monitoring | Shared (Hub + Spoke) |
| Workflow integration, adoption | Spoke (Business Unit) |

### AI-Enablement-Proof as Worked Example

This project demonstrates the hub-and-spoke model in practice:
- The governance chassis (`src/governance/`) is the hub artifact
- The grid reliability domain is the spoke
- The autonomy ladder, gate specs, and audit trail are reusable across any agent
