"""Seed rubric ratings for the `evolving-notes` scenario.

Produces 8-12 RubricRow entries spread across three roles (answerer, extractor,
meta_evaluator) so the Evals & Prompt Hardening page has plausible signal to
render. Criterion scores live in the 0.70-0.95 band and vary per row so the
"average by criterion" projection has spread.

The existing `db.log_rubric_row` takes a generic dict whose schema requires
`target_id` (string) and `overall` (1-5 integer). We synthesize a target_id
and derive `overall` from the per-criterion average so the row insert succeeds
without forcing every caller to know about those fields.

Idempotency: each run inserts brand-new rows with fresh UUIDs. The script is
safe to re-run, but doing so accumulates additional rubric history (which is
fine for a demo seed).
"""

from __future__ import annotations

import random
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from openacad.runtime import db
from openacad.runtime.scenario import use_scenario


SCENARIO_KEY = "evolving-notes"


# Per-role criterion sets — matches what the spec calls out so the projection
# layer (rubric_avg_by_criterion) sees consistent keys per role.
CRITERIA_BY_ROLE: dict[str, list[str]] = {
    "answerer": ["accuracy", "citation_quality", "clarity", "registry_alignment"],
    "extractor": ["atomicity", "registry_compliance", "completeness", "attribute_richness"],
    "meta_evaluator": ["proposal_quality", "evidence_grounding", "prompt_specificity"],
}

# Per-role row counts — totals to 11, in the 8-12 window the spec requests.
ROLE_COUNTS: dict[str, int] = {
    "answerer": 6,
    "extractor": 3,
    "meta_evaluator": 2,
}

# Per-role free-text seed notes — picked at random so rows differ.
NOTES_BY_ROLE: dict[str, list[str]] = {
    "answerer": [
        "Citations placed inline after each claim; no orphan citations.",
        "Answer is grounded but glosses one of the cited atoms — minor.",
        "Clear prose; could surface contradicting atom when present.",
        "Registry-aligned terminology throughout.",
        "Good coverage of the question; one claim lacks an atom backing.",
        "Concise and well-structured; cites every claim.",
    ],
    "extractor": [
        "Atoms are single-idea; no compound claims slipped through.",
        "Reuses existing registry attributes; only one new key proposed.",
        "Captures the key claim and supporting evidence as separate atoms.",
    ],
    "meta_evaluator": [
        "Proposal targets the lowest-rated criterion with a concrete example.",
        "Rationale quotes scholar free-text verbatim; easy to review.",
    ],
}


def _criterion_score(role: str, criterion: str, idx: int) -> float:
    """Plausible per-criterion score in the 0.70-0.95 band, varied per row.

    Uses a seeded RNG keyed on (role, criterion, idx) so reruns are stable
    enough to eyeball but still produce a realistic spread.
    """
    rng = random.Random(f"{role}:{criterion}:{idx}")
    return round(0.70 + rng.random() * 0.25, 2)


def _overall_from_criteria(criteria: dict[str, float]) -> int:
    """Map 0.70-0.95 avg → 1-5 integer overall score for legacy schema."""
    if not criteria:
        return 3
    avg = sum(criteria.values()) / len(criteria)
    # 0.70 → ~3.5, 0.95 → ~4.75; round to nearest int, clamp 1..5.
    rounded = round(avg * 5)
    return max(1, min(5, rounded))


def _build_row(role: str, idx: int, now: datetime) -> dict:
    crits = {c: _criterion_score(role, c, idx) for c in CRITERIA_BY_ROLE[role]}
    notes_pool = NOTES_BY_ROLE[role]
    note = notes_pool[idx % len(notes_pool)]
    rng = random.Random(f"{role}:ts:{idx}")
    ts = now - timedelta(days=rng.randint(0, 13), hours=rng.randint(0, 23))
    return {
        "id": f"rubric-{uuid.uuid4().hex[:8]}",
        "role": role,
        # target_id: synthesized — points at the artifact the rubric was about.
        # Answerers rate comparison runs, extractors rate atoms, meta_evaluator
        # rates prompt proposals. We make these plausible-looking placeholders.
        "target_id": {
            "answerer": f"cmp-seeded-{idx:02d}",
            "extractor": f"atom-seeded-{idx:02d}",
            "meta_evaluator": f"propose-seeded-{idx:02d}",
        }[role],
        "overall": _overall_from_criteria(crits),
        "criteria": crits,
        # The new pages use `notes` (per the DTO). The legacy table stores it
        # as `free_text`. We populate both so old + new readers agree.
        "free_text": note,
        "notes": note,
        "rater": "scholar",
        "timestamp": ts.isoformat(),
    }


def main() -> None:
    now = datetime.now(timezone.utc)
    total = 0
    with use_scenario(SCENARIO_KEY):
        for role, count in ROLE_COUNTS.items():
            for i in range(count):
                row = _build_row(role, i, now)
                db.log_rubric_row(row)
                total += 1
    print(f"seeded {total} rubric rows for {SCENARIO_KEY}")


if __name__ == "__main__":
    main()
