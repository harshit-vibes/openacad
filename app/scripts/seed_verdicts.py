"""Seed scholar-verdict EvalEvents for the `evolving-notes` scenario.

Emits ~20 events with `kind` in {accept, edit, reject}, distributed roughly
60/25/15 to mirror a realistic curation queue. Each event's payload carries a
`draft_id` that, where possible, points at a real DraftAtom persisted in the
scenario's `drafts` table (so the Curate / Observability projections can join).
When there are fewer than 20 real drafts, the script falls back to synthetic
draft ids so the demo still has feed material.

Timestamps stagger across the last 14 days so per-day rollups have spread.
"""

from __future__ import annotations

import random
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from openacad.feedback.schema import EvalEvent
from openacad.runtime import db
from openacad.runtime.scenario import use_scenario


SCENARIO_KEY = "evolving-notes"

# Spec: 12 accept, 5 edit, 3 reject = 20 events.
KINDS_DISTRIBUTION: list[str] = (
    ["accept"] * 12 + ["edit"] * 5 + ["reject"] * 3
)


def _collect_real_draft_ids() -> list[str]:
    """Walk every source and gather every DraftAtom id we can find."""
    ids: list[str] = []
    for src in db.list_sources():
        try:
            drafts = db.drafts_for_source(src.id)
        except Exception:
            continue
        for d in drafts:
            ids.append(d.draft_id)
    return ids


def _kind_payload(kind: str, draft_id: str, rng: random.Random) -> dict:
    """Per-kind payload shape — keeps the activity feed informative."""
    base = {"draft_id": draft_id}
    if kind == "accept":
        return {
            **base,
            "promoted_to": draft_id.replace("draft-", "atom-"),
            "reviewer_note": rng.choice([
                "looks good",
                "clean atomicity",
                "registry-aligned",
            ]),
        }
    if kind == "edit":
        return {
            **base,
            "edits": rng.choice([
                ["tighten content"],
                ["fix attribute key"],
                ["split into two atoms"],
            ]),
            "reviewer_note": "minor revisions before promote",
        }
    # reject
    return {
        **base,
        "reason": rng.choice([
            "duplicate of existing atom",
            "off-topic for this paper",
            "claim not grounded in source",
        ]),
    }


def main() -> None:
    rng = random.Random("seed-verdicts")
    now = datetime.now(timezone.utc)

    with use_scenario(SCENARIO_KEY):
        real_ids = _collect_real_draft_ids()

        # Shuffle the kinds so the timeline doesn't render as 12-block-of-accepts.
        kinds = list(KINDS_DISTRIBUTION)
        rng.shuffle(kinds)

        emitted = 0
        for i, kind in enumerate(kinds):
            # Prefer a real draft if we have one for this slot, else fabricate.
            if real_ids:
                draft_id = real_ids[i % len(real_ids)]
            else:
                draft_id = f"draft-synthetic-{i:02d}"

            ts = now - timedelta(
                days=rng.randint(0, 14),
                hours=rng.randint(0, 23),
                minutes=rng.randint(0, 59),
            )

            db.log_event(
                EvalEvent(
                    id=f"verdict-{uuid.uuid4().hex[:8]}",
                    timestamp=ts,
                    kind=kind,
                    actor="scholar",
                    payload=_kind_payload(kind, draft_id, rng),
                )
            )
            emitted += 1

    print(f"emitted {emitted} verdict events for {SCENARIO_KEY}")


if __name__ == "__main__":
    main()
