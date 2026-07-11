# Gate Specifications

Each governance gate has a defined trigger, logic, failure mode, and log schema.
Gates are code (`src/governance/gates.py`), not prose.

## Gate: Confidence

- **Trigger:** Every recommendation
- **Logic:** `confidence >= threshold` (default 0.6)
- **Failure mode:** Action blocked; logged with confidence value
- **Log schema:** `{gate: "confidence", passed: bool, confidence: float, threshold: float}`

## Gate: Blast Radius

- **Trigger:** Every action affecting balancing authorities
- **Logic:** `len(affected_bas) <= max_bas` (default 10)
- **Failure mode:** Action blocked; logged with BA list
- **Log schema:** `{gate: "blast_radius", passed: bool, count: int, max: int, affected_bas: [str]}`

## Gate: Autonomy

- **Trigger:** Every agent action
- **Logic:** `requested_level <= MAX_PERMITTED_LEVEL[action_class]`; L5 always raises
- **Failure mode:** Action blocked (L5: hard error); logged with level and action class
- **Log schema:** `{gate: "autonomy", passed: bool, action_class: str, level: int}`

## Gate: HITL Routing

- **Trigger:** Every action at L3+
- **Logic:** Classifies whether human approval is required (L3+ by default)
- **Failure mode:** Routing gate -- classifies, does not block
- **Log schema:** `{gate: "hitl_routing", passed: true, requires_human: bool, level: int}`

## Aggregate Verdict

All gates run sequentially via `run_all_gates()`. The action proceeds only if
**all gates pass**. Blocked gates are logged with full metadata.
