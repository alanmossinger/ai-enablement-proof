"""Append-only audit logger — the flight recorder.

Every agent action, gate check, and governance decision is logged to an immutable
JSONL stream. Entries are never modified or deleted.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .gates import GateVerdict

DEFAULT_AUDIT_PATH = Path("data/audit/audit.jsonl")


def _make_entry(
    event_type: str,
    payload: dict[str, Any],
    *,
    event_id: str | None = None,
    parent_id: str | None = None,
) -> dict[str, Any]:
    return {
        "event_id": event_id or str(uuid.uuid4()),
        "parent_id": parent_id,
        "timestamp": datetime.now(UTC).isoformat(),
        "event_type": event_type,
        "payload": payload,
    }


class AuditLogger:
    """Append-only JSONL audit logger."""

    def __init__(self, path: Path | str = DEFAULT_AUDIT_PATH):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _append(self, entry: dict[str, Any]) -> str:
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, default=str) + "\n")
        return entry["event_id"]

    def log_observation(self, source: str, record_count: int, **extra: Any) -> str:
        return self._append(
            _make_entry(
                "observation",
                {"source": source, "record_count": record_count, **extra},
            )
        )

    def log_forecast(self, ba: str, horizon_hours: int, **extra: Any) -> str:
        return self._append(
            _make_entry(
                "forecast",
                {"ba": ba, "horizon_hours": horizon_hours, **extra},
            )
        )

    def log_stress_score(self, ba: str, gsi: float, tier: str, **extra: Any) -> str:
        return self._append(
            _make_entry(
                "stress_score",
                {"ba": ba, "gsi": gsi, "tier": tier, **extra},
            )
        )

    def log_recommendation(
        self, action_class: str, action_id: str, summary: str, **extra: Any
    ) -> str:
        return self._append(
            _make_entry(
                "recommendation",
                {"action_class": action_class, "action_id": action_id, "summary": summary, **extra},
            )
        )

    def log_gate_verdict(self, verdict: GateVerdict) -> str:
        return self._append(
            _make_entry(
                "gate_verdict",
                {
                    "action_class": verdict.action_class,
                    "action_id": verdict.action_id,
                    "passed": verdict.passed,
                    "gates": [
                        {
                            "gate": r.gate_name,
                            "passed": r.passed,
                            "reason": r.reason,
                            "metadata": r.metadata,
                        }
                        for r in verdict.results
                    ],
                },
            )
        )

    def log_block(self, action_id: str, blocked_gates: list[str], **extra: Any) -> str:
        return self._append(
            _make_entry(
                "action_blocked",
                {"action_id": action_id, "blocked_by": blocked_gates, **extra},
            )
        )

    def read_all(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        entries = []
        with self.path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))
        return entries
