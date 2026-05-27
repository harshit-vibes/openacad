"""Universal rubric model + write helpers. Logged on every answer / draft review.

The rubric row lives in the per-scenario `state.sqlite::rubrics` table and also
generates an `EvalEvent(kind="rubric")` so downstream loops (Meta-Evaluator) can
read it through the same event-log pipeline as accept/edit/reject signals.
"""

import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, Field

from openacad.feedback.schema import EvalEvent
from openacad.runtime.scenario import AgentRole, active_scenario
from openacad.runtime import db
def _now() -> datetime:
    return datetime.now(timezone.utc)


class Rubric(BaseModel):
    """Universal eval signal: overall 1-5 + per-criterion 1-5 + free-text reason."""

    id: str = Field(default_factory=lambda: f"rb-{uuid.uuid4().hex[:8]}")
    role: AgentRole
    target_id: str                                  # answer id, draft id, or proposal id
    overall: int = Field(ge=1, le=5)
    criteria: dict[str, int] = Field(default_factory=dict)
    free_text: str = ""
    rater: str = "scholar"
    timestamp: datetime = Field(default_factory=_now)


def record(rubric: Rubric) -> Rubric:
    """Persist the rubric to the active scenario's state.sqlite and log an event."""
    db.log_rubric_row(
        {
            "id": rubric.id,
            "role": rubric.role.value,
            "target_id": rubric.target_id,
            "overall": rubric.overall,
            "criteria": rubric.criteria,
            "free_text": rubric.free_text,
            "rater": rubric.rater,
            "timestamp": rubric.timestamp.isoformat(),
        }
    )
    db.log_event(
        EvalEvent(
            id=f"ev-{uuid.uuid4().hex[:8]}",
            timestamp=rubric.timestamp,
            kind="rubric",
            actor=rubric.rater,
            payload={
                "scenario": active_scenario().key,
                "role": rubric.role.value,
                "target_id": rubric.target_id,
                "overall": rubric.overall,
                "criteria": rubric.criteria,
                "free_text": rubric.free_text,
                "rubric_id": rubric.id,
            },
        )
    )
    return rubric


def list_for_role(role: AgentRole, limit: int = 100) -> list[Rubric]:
    rows = db.list_rubric_rows(role=role.value, limit=limit)
    out = []
    for r in rows:
        out.append(
            Rubric(
                id=r["id"],
                role=AgentRole(r["role"]),
                target_id=r["target_id"],
                overall=r["overall"],
                criteria=r["criteria"],
                free_text=r["free_text"],
                rater=r["rater"],
                timestamp=datetime.fromisoformat(r["timestamp"]),
            )
        )
    return out


def role_average(role: AgentRole) -> dict[str, float | int]:
    """Aggregate stats for a role: count, overall avg, per-criterion avgs."""
    rubs = list_for_role(role, limit=10000)
    if not rubs:
        return {"count": 0, "overall_avg": None, "criteria_avg": {}}
    overall = sum(r.overall for r in rubs) / len(rubs)
    crit_sums: dict[str, list[int]] = {}
    for r in rubs:
        for k, v in r.criteria.items():
            crit_sums.setdefault(k, []).append(v)
    crit_avg = {k: round(sum(vs) / len(vs), 2) for k, vs in crit_sums.items()}
    return {
        "count": len(rubs),
        "overall_avg": round(overall, 2),
        "criteria_avg": crit_avg,
    }
