"""Unified activity timeline — every agent action + scholar verdict + score
lands here. The substrate for HITL + evals as one loop.

V1 reads from the existing per-scenario `eval_events` table that
`runtime.db.log_event()` already populates. Future: cross-scenario rollup,
filtered views, replay-and-rebuild.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Iterator

from openacad.feedback.schema import EvalEvent
from openacad.runtime import db
from openacad.runtime.scenario import SCENARIOS, use_scenario


def list_events(
    scenario_key: str | None = None,
    kind: str | None = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    """Return recent events, optionally filtered. If no scenario_key, scan all.

    Each dict carries the original EvalEvent fields plus `scenario` for
    cross-scenario context.
    """
    out: list[dict[str, Any]] = []
    scenario_keys = [scenario_key] if scenario_key else [s.key for s in SCENARIOS]
    for k in scenario_keys:
        with use_scenario(k):
            try:
                events = db.list_events(kind=kind, limit=limit)
            except Exception:
                continue
            for ev in events:
                out.append({
                    "scenario": k,
                    "id": ev.id,
                    "timestamp": ev.timestamp,
                    "kind": ev.kind,
                    "payload": ev.payload,
                })
    out.sort(key=lambda r: r["timestamp"], reverse=True)
    return out[:limit]


def log_event(kind: str, payload: dict[str, Any]) -> str:
    """Append an event to the active scenario's timeline. Returns event id."""
    import uuid
    from datetime import timezone
    eid = f"ev-{uuid.uuid4().hex[:8]}"
    ev = EvalEvent(
        id=eid,
        timestamp=datetime.now(timezone.utc),
        kind=kind,
        payload=payload,
    )
    db.log_event(ev)
    return eid


def event_counts_by_kind(scenario_key: str | None = None) -> dict[str, int]:
    """Quick aggregate for the timeline page summary tiles."""
    counts: dict[str, int] = {}
    for ev in list_events(scenario_key=scenario_key, limit=10_000):
        counts[ev["kind"]] = counts.get(ev["kind"], 0) + 1
    return counts


__all__ = ["list_events", "log_event", "event_counts_by_kind"]
