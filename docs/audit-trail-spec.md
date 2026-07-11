# Audit Trail Specification

The audit trail is an append-only JSONL event stream. Entries are never modified
or deleted. This is the "flight recorder" of the agent.

## Storage

- **Format:** JSONL (one JSON object per line)
- **Path:** `data/audit/audit.jsonl`
- **Mutability:** Append-only. No updates, no deletes.

## Event Schema

Every event contains:

```json
{
  "event_id": "uuid4",
  "parent_id": "uuid4 | null",
  "timestamp": "ISO-8601 UTC",
  "event_type": "string",
  "payload": {}
}
```

## Event Types

| Type | Payload Fields | When |
|------|---------------|------|
| `observation` | source, record_count | Data ingested |
| `forecast` | ba, horizon_hours | Forecast generated |
| `stress_score` | ba, gsi, tier | GSI computed |
| `recommendation` | action_class, action_id, summary | Action proposed |
| `gate_verdict` | action_class, action_id, passed, gates[] | All gates checked |
| `action_blocked` | action_id, blocked_by[] | Action denied |

## Traceability

Every recommendation can be traced backward through its audit chain:
observation -> forecast -> stress_score -> recommendation -> gate_verdict

The `parent_id` field links events in the causal chain.
