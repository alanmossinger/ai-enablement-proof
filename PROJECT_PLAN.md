# PROJECT_PLAN.md — AI-Enablement-Proof
## A Governed Autonomous Agent for Grid Reliability Across the U.S. Power System

**Repository:** `github.com/alanmossinger/ai-enablement-proof`
**Author:** Alan Mössinger
**Status:** Phase 0 — Foundation
**Series:** Forecast-to-Dispatch → Capital-to-Production → **AI-Enablement-Proof**
**Tagline:** *"Autonomy you can audit. Govern the machine, or the machine governs you."*

---

## 0. One-Paragraph Thesis

> Most AI agent demos automate paperwork. This one watches the North American power grid, detects reliability stress hours before operators declare emergencies, drafts operator-grade advisories — and every single action passes through a codified governance gate with a full audit trail. Replayed against the last five years of real grid emergencies (Winter Storm Uri, Winter Storm Elliott, the recent heat domes), the agent's detection lead time **and its false-alarm rate** are measured, published, and reproducible from public federal data. **This is what "AI agent enablement" means when an operator builds it: autonomy you can audit.**

**The headline engineered to survive a CEO's attention span:** *Winter Storm Uri caused ~$130B in damages and 246 deaths. AI-Enablement-Proof, backtested against only the public data available at the time, escalated to its highest alert tier [X] hours before ERCOT declared EEA3 — and the repo shows every governance gate each of those decisions passed through.* Everything in this project exists to make that sentence true, provable, and reproducible. [X] is whatever the honest number turns out to be.

---

## 1. Why This Agent Moves the Energy Industry

1. **Grid reliability is the #1 story in energy.** NERC reliability assessments flag elevated risk across most of North America — data-center load growth, electrification, thermal retirements, weather volatility. Control rooms are understaffed relative to the complexity they manage. An agent that extends operator situational awareness is the most-requested capability in grid operations, not a toy.
2. **Agentic AI is the 2026 enterprise conversation — and energy is where "move fast and break things" is not an option.** A 24/7 autonomous agent wrapped in hard, code-enforced governance is precisely the tension every energy CIO/CEO is trying to resolve. This repo resolves it in public.
3. **The audience is the whole sector.** Utilities, IPPs, storage operators, traders, grid operators, and energy-intensive manufacturers (battery plants included) all carry reliability exposure. An agent demonstrated on the *national* grid speaks to all of them at once — including a battery manufacturer whose customers buy precisely because of grid stress.

---

## 2. Strategic Positioning

### 2.1 Portfolio logic

| Project | Claim it proves |
|---|---|
| Forecast-to-Dispatch | Governed AI captures audited market value (86.1% revenue capture, $3.31M settled, ERCOT) |
| C-MAPSS RUL Governance | Governance as enforceable CI gates (NIST AI RMF, EU AI Act) |
| Capital-to-Production | Prescriptive AI for capital allocation under uncertainty |
| **AI-Enablement-Proof (this project)** | **A governed autonomous agent on critical infrastructure — safely** |

### 2.2 Audience hierarchy (in order)

1. **CEOs / P&L executives** — README top fold: dollars, hours of warning, zero technical vocabulary.
2. **CIOs / CDOs** — architecture, autonomy ladder, audit-trail spec, the seam between infrastructure and enablement.
3. **Practitioners** — runnable code, evaluation harness, backtest notebooks. The 13-figure catalog as a scannable visual narrative.

### 2.3 Naming rules

- **No implied operational deployment.** Always "demonstration system," "backtested," "running on live public data." Never imply a grid operator uses this.

---

## 3. What the Agent Actually Does

### 3.1 The agent loop (OODA structure inside a governance chassis)

```
        ┌──────────────────────────────────────────────────────────┐
        │                   GOVERNANCE CHASSIS                      │
        │      (every arrow below passes through a coded gate)      │
        │                                                           │
        │  OBSERVE ──► ORIENT ──► DECIDE ──► RECOMMEND ──► LOG      │
        │  EIA-930     Forecasts   Grid       Graduated     Immutable│
        │  NOAA wx     + anomaly   Stress     alerts +      audit    │
        │  ERCOT/NERC  detection   Index      playbook      trail    │
        │  archives                engine     actions       (JSONL)  │
        └──────────────────────────────────────────────────────────┘
```

1. **OBSERVE** — Poll EIA-930 hourly demand / generation-by-fuel / interchange for all ~65 U.S. balancing authorities; join NOAA/NWS temperature forecasts (weather extremes are the dominant stress driver).
2. **ORIENT** — Short-horizon load and net-load forecasts per BA (LightGBM baseline → temporal model), plus anomaly detection on forecast residuals, interchange patterns, and generation-mix shifts.
3. **DECIDE** — A transparent stress-scoring engine converts forecasts + anomalies into a **Grid Stress Index (GSI)** per BA per hour, mapped to five alert tiers (Watch → Advisory → Alert → Emergency Watch → Critical). The GSI formula is published, not a black box.
4. **RECOMMEND** — For each tier, the agent drafts an action package from a playbook library ("pre-position demand response," "verify peaker fuel supply," "defer planned maintenance outage") written in control-room language, not data-science language.
5. **GATE + LOG** — Before anything is surfaced: confidence threshold gate, blast-radius classification, autonomy-level check, human-in-the-loop routing, immutable audit logging. Gates are **code, not prose** — a recommendation that fails a gate is visibly blocked, and the block is logged too.

### 3.2 The Autonomy Ladder (core intellectual contribution)

Every agent action is classified on a six-level ladder; the chassis enforces the maximum permitted level per action class:

| Level | Name | Agent behavior | Human role | AI-Enablement-Proof usage |
|---|---|---|---|---|
| L0 | Observe | Collects and displays data | Full control | Data ingestion |
| L1 | Describe | Summarizes state, no judgment | Full control | Hourly grid digest |
| L2 | Predict | Forecasts with uncertainty | Reviews | Load/net-load forecasts |
| L3 | Recommend | Proposes actions + rationale | Approves/rejects | Alert tiers 1–3 |
| L4 | Act-with-veto | Executes unless vetoed in window | Veto power | **Demonstrated, simulation only** |
| L5 | Autonomous | Executes and reports | Audits | **Prohibited — and the prohibition is a coded, CI-blocking test** |

The interview punchline: *the repo contains `test_no_L5.py`, a required CI check that fails the build if any code path attempts an L5 action.* Governance as a merge blocker, not a slide.

### 3.3 Backtest anchor events (strict point-in-time discipline)

- **Winter Storm Uri** — ERCOT, Feb 2021. Headline: alert-tier escalation lead time vs. official EEA declarations.
- **Winter Storm Elliott** — Eastern Interconnection, Dec 2022. Showcases multi-BA stress propagation — the national view.
- **A Western heat dome** — CAISO/WECC summer event: heat-driven evening-ramp stress.
- **A quiet control month** — to measure the false-alarm rate honestly. An agent that cries wolf is a governance failure; the false-positive analysis is a *feature* of this project, not a weakness to hide.

---

## 4. Data Sources (All Public, All Citable)

| Source | Content | Access | Role |
|---|---|---|---|
| EIA-930 via EIA API v2 | Hourly demand, day-ahead demand forecast, net generation by fuel, interchange — every U.S. BA since 2015 | Free API key | Primary observation stream |
| NOAA/NWS API + ISD historical | Temperature forecasts and actuals for BA load centers | Free | Stress-driver features |
| ERCOT public archives | EEA declarations and notices | Free | Uri ground-truth labels |
| NERC/FERC public event reports | Uri & Elliott post-event analyses | Free | Ground truth + primary-source citations |
| LBNL / EIA STEO (optional) | Context layers | Free | Enrichment only |

**Rule:** every number in the README traces to a public source or to a committed notebook. No exceptions.

---

## 5. Architecture

```
ai-enablement-proof/
├── README.md                      ← executive narrative + figure gallery
├── PROJECT_PLAN.md                ← this file
├── CLAUDE.md                      ← build governance for AI-assisted development
├── docs/
│   ├── autonomy-ladder.md
│   ├── gate-specifications.md     ← per gate: trigger, logic, failure mode, log schema
│   ├── audit-trail-spec.md        ← immutable JSONL event schema
│   ├── alert-playbooks/           ← per-tier action packages, operator language
│   └── model-cards/               ← one per model, NIST AI RMF aligned
├── src/
│   ├── ingest/                    ← EIA-930 + NOAA pollers, point-in-time store (DuckDB)
│   ├── forecast/                  ← per-BA load & net-load models
│   ├── stress/                    ← Grid Stress Index engine (published formula)
│   ├── agent/                     ← the loop: orient → decide → recommend
│   ├── governance/                ← gates as code (the crown jewels)
│   │   ├── gates.py               ← confidence, blast-radius, autonomy, HITL routing
│   │   ├── audit.py               ← append-only logger
│   │   └── test_no_L5.py          ← CI-blocking autonomy test
│   └── api/                       ← FastAPI: current GSI, alerts, audit queries
├── notebooks/
│   ├── 01_uri_backtest.ipynb
│   ├── 02_elliott_backtest.ipynb
│   ├── 03_heatdome_backtest.ipynb
│   └── 04_false_alarm_analysis.ipynb
├── enablement/                    ← the operating-system layer (Section 6)
└── figures/                       ← 13-figure catalog, generated by code only
```

**Stack:** Python 3.11+, pandas/polars, LightGBM baseline + PyTorch temporal model, FastAPI, DuckDB point-in-time store, Plotly + matplotlib, GitHub Actions CI with governance tests as required merge checks.

---

## 6. The Enablement Layer (`/enablement`)

The public codification of the federated hub-and-spoke operating model — with AI-Enablement-Proof as its worked example:

1. **`operating-model.md`** — hub-and-spoke blueprint; explicit RACI drawing the seam between infrastructure ownership (CIO territory) and the enablement/value layer (governance, adoption, value realization). Written to be lifted directly into an interview or client conversation.
2. **`maturity-rubric.md`** — 5 levels × 6 dimensions (governance, data ownership, workforce literacy, use-case portfolio discipline, value measurement, operating cadence). AI-Enablement-Proof is scored against the rubric honestly, including where it falls short.
3. **`deployment-gate-checklist.md`** — the generic, reusable version of `src/governance/` for any agent in any company.
4. **`value-scorecard.md`** — tying an agent to P&L: avoided-cost framing (load-shed avoided, imbalance cost avoided, maintenance deferral), with an honest counterfactual-caveat structure.
5. **`executive-onepager.md`** — one page, zero technical vocabulary, capital-allocation and workforce-capacity framing. **Deliberately written to be handed to a non-technical CEO unmodified.**

---

## 7. Phase Plan

| Phase | Deliverable | Exit criterion |
|---|---|---|
| **0 — Foundation** | This plan, CLAUDE.md, anti-fabrication rules, figure catalog, repo scaffold, EIA API key | Documents committed |
| **1 — Point-in-time data layer** | EIA-930 + NOAA ingestion into DuckDB with strict as-of semantics | Reproduce any historical hour's information state with **zero lookahead** — the integrity foundation of every claim |
| **2 — Forecast engine** | Per-BA load & net-load forecasts, LightGBM first, temporal model second | MAPE / pinball-loss tables per BA committed as CSV artifacts; baseline numbers published honestly |
| **3 — Grid Stress Index** | Transparent GSI formula + five calibrated tiers | GSI time series 2019–2025, all BAs; historical EEA events land in top tiers |
| **4 — Governance chassis** | Gates as code, audit logger, autonomy enforcement, `test_no_L5.py` as required CI check | A deliberately over-confident recommendation is **blocked**, and the block is auditable |
| **5 — Agent loop** | Scheduled hourly loop on live public data | Agent runs **unattended for 7 days**; every output has a complete audit chain |
| **6 — Backtests (headline phase)** | Uri, Elliott, heat dome, quiet control month | Lead-time table (agent escalation vs. official declarations), false-alarm rate, one-command reproduction per notebook |
| **7 — Figures** | The 13-figure catalog | Every figure generated by committed code from committed data; no hand-edited images, ever |
| **8 — Enablement layer** | Section 6 documents | AI-Enablement-Proof self-scored against its own rubric |
| **9 — Publication** | README, LinkedIn sequence, live-dashboard demo GIF | Post sequence per Section 13 |

---

## 8. Figure Catalog (13 Figures — the Visual Narrative)

Design language: dark background, one accent color per figure family, every figure standalone-legible — a recruiter scrolling the README should get the complete story from images alone. Innovation bar: each figure shows something the reader has **not seen before** in a portfolio project.

| # | Figure | Type | The story it tells |
|---|---|---|---|
| F1 | **The National Pulse** | Animated choropleth (GIF): all ~65 BAs colored by Grid Stress Index, hour by hour through Winter Storm Elliott | The agent sees the whole country at once; stress propagates east like weather. Instantly shareable. |
| F2 | **[X] Hours Before** | Uri dual-swimlane timeline: agent tier escalations (bottom) vs. official ERCOT actions (top), the gap shaded | **The money figure.** The shaded gap IS the value of the agent. One glance, no caption needed. |
| F3 | **Anatomy of a Decision** | Vertical decision-flow of one real recommendation traversing every gate, with actual logged values at each gate | Governance made visible. This figure IS the "governed agent" claim. |
| F4 | **The Autonomy Ladder** | Six rungs, action classes plotted at their permitted level; the L5 rung drawn physically severed, `test_no_L5.py` printed on the cut | The most screenshot-able governance visual in the repo. |
| F5 | **Forecast Fan vs. Reality** | Net-load fan chart (P10–P90) entering Uri, actual trace overlaid, stress-tier thresholds as horizontal bands | Honest uncertainty communication — the fan widens exactly when it should. |
| F6 | **The Gate Funnel** | Sankey: recommendations generated → gates passed → HITL routing tiers → simulated approve/veto; blocked flows in red | The chassis working at volume: N proposed, M blocked, and why. |
| F7 | **Crying Wolf, Measured** | Full-year calendar heatmap: every alert, colored true/false positive; the false-alarm rate printed large | Radical honesty as differentiation. Nobody publishes their false positives. |
| F8 | **Stress Propagation Network** | Force-directed graph: BAs as nodes, interchange as edges (thickness = flow, color = GSI), Elliott snapshot sequence | The grid as a network organism — visually novel, technically substantive. |
| F9 | **What the Agent Read** | SHAP waterfall for the single decision in F3, chained to its audit-log ID | Explainability at decision granularity, linked to the flight recorder. |
| F10 | **The Flight Recorder** | Stylized rendering of the immutable JSONL audit stream as a ribbon, gate events flagged | Makes the most boring artifact in AI — the audit log — visually compelling. |
| F11 | **Baseline Humility** | Small multiples: LightGBM vs. temporal model per region; regions where the simple model wins are highlighted, not hidden | Anti-hype credibility. The F2D discipline, continued. |
| F12 | **Avoided-Cost Waterfall** | Modeled avoided costs per backtest event; each bar annotated with its counterfactual assumption on the figure itself | The CEO figure: dollars with visible epistemic humility. |
| F13 | **The Operating System** | One-poster composition: hub-and-spoke, maturity radar (self-scored), gate checklist | The "this scales beyond one project" figure; doubles as VEX collateral and a book graphic. |

---

## 9. Anti-Fabrication Rules (Non-Negotiable)

1. **Every quantitative claim traces to committed code + public data.** If a number appears in the README, a notebook reproduces it.
2. **Strict point-in-time discipline.** Backtests use only data timestamped before the decision moment. Lookahead is a project-invalidating bug.
3. **No implied operational deployment.** "Demonstration system," "backtested," "live public data" — never imply a grid operator runs this.
4. **False positives are published, not buried.** F7 gets its own figure and its own LinkedIn post.
5. **Counterfactual value claims carry visible assumptions**, printed on the figure (F12).
6. **No employer names.** Anonymized vignettes only.
7. **Simple baselines reported first and honestly**, including where they win (F11).
8. **AI-assisted development is itself governed** via CLAUDE.md — the build process demonstrates the methodology (meta-proof: the agent was built under the same discipline it enforces).
9. **The autonomy prohibition is tested, not asserted.** `test_no_L5.py` exists, runs in CI, and is a required merge check from Phase 4 onward.
10. **Official event timelines cite primary sources** (NERC/FERC reports, ERCOT notices) — never news summaries.
11. **The lead-time headline uses the honest number, whatever it is.** A governed agent with a modest, true lead time beats an inflated one; the governance story stands regardless.

---

## 10. Market Vocabulary

Balancing authority (BA) · Energy Emergency Alert (EEA 1/2/3) · net load · reserve margin · operating reserves · firm load shed · interchange · ramping · duck curve · demand response (DR) · capacity adequacy · N-1 contingency · point-in-time / as-of data · human-in-the-loop (HITL) · blast radius · autonomy level · audit trail · model card · NIST AI RMF · EU AI Act risk tiering.

**Rule:** alert playbooks read the way a control-room operator would write them, not the way a data scientist would.

---

## 11. Success Metrics

| Metric | Target | Why it matters |
|---|---|---|
| Uri escalation lead time vs. EEA3 | The honest number, published | The headline |
| False-alarm rate (Advisory+) | Published, with cost framing | Credibility |
| Unattended live run | ≥ 7 consecutive days, complete audit chains | The "agent" claim is real |
| CI governance checks | 100% required, incl. no-L5 test | The "governed" claim is real |
| Reproduction | Any figure regenerable with one command | Anti-fabrication proof |
| Executive one-pager | Readable by a non-technical CEO unmodified | The P&L-executive test |

---

## 12. Risk Register

| Risk | Mitigation |
|---|---|
| EIA-930 data quality (known BA reporting errors) | Use EIA's cleaned/imputed series where available; document known issues per BA; exclude irreparable BAs transparently |
| Backtest lead time disappoints | Publish the honest number (Rule 11); the governance story stands regardless |
| Scope creep into Capital-to-Production territory | Hard boundary: AI-Enablement-Proof = operations/reliability; C2P = capital allocation. They cross-reference, never merge |
| "Toy project" perception | 7-day unattended live run + complete audit chains + required CI gates = production posture, stated explicitly |
| Time competition with active interview processes | The Phase 6 + F2/F3/F4 milestone is a shippable interview artifact before full completion |

---

*Build discipline: this plan is executed under the same governance it preaches. Every phase has an exit criterion; no phase is declared complete without its artifact committed.*
