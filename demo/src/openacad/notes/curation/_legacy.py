"""Curate commit logic. Single funnel for every vault mutation:

  draft → accept/edit/reject → commit (write file + project to SQLite + update graph
                                       + update embeddings + run registry promotion
                                       + log eval event)

Reject does not write a file but logs the rejection reason for the prompt
regeneration loop.
"""

import uuid
from datetime import datetime, timezone

from openacad.notes.schema import AtomicNote, DraftAtom, Metas, Origin, ScholarAct

from openacad.feedback.schema import EvalEvent
from openacad.notes.registry import _legacy as registry_service
from openacad.notes.persistence import vault as vault_io
from openacad.runtime import db
def now() -> datetime:
    return datetime.now(timezone.utc)


def _commit(d: DraftAtom, scholar_action: ScholarAct) -> AtomicNote:
    """Promote a draft to an active AtomicNote. Runs validation; raises on errors."""
    ts = now()
    atom = AtomicNote(
        metas=Metas(
            id=d.suggested_id,
            type=d.type,
            status="active",
            created_at=ts,
            updated_at=ts,
            tags=d.tags,
        ),
        origin=Origin(
            source_id=d.source_id,
            chunk_ids=d.chunk_ids,
            page_range=d.page_range,
            prompt_version=d.prompt_version,
            scholar_action=scholar_action,
        ),
        attributes=d.attributes,
        relations=d.relations,
        content=d.content,
    )

    errors = registry_service.validate_atom(atom)
    if errors:
        raise ValueError("registry validation failed: " + "; ".join(errors))

    # Idempotency: if id already exists, the suggested_id collided. Caller must edit first.
    if vault_io.atom_exists(atom.metas.id):
        raise ValueError(f"atom id {atom.metas.id} already exists; edit the draft to give it a unique id")

    vault_io.write_atom(atom)
    db.upsert_atom_projection(atom)
    db.delete_draft(d.draft_id)

    db.log_event(
        EvalEvent(
            id=f"ev-{uuid.uuid4().hex[:8]}",
            timestamp=ts,
            kind="accept" if scholar_action == "accepted" else "edit",
            payload={
                "atom_id": atom.metas.id,
                "draft_id": d.draft_id,
                "prompt_version": d.prompt_version,
                "scholar_action": scholar_action,
            },
        )
    )

    # Lifecycle side-effects (graph, embedding, registry sweep) live in the hook.
    from openacad.hooks.on_atom_accepted import fire as fire_on_atom_accepted
    fire_on_atom_accepted(atom)

    return atom


def accept(draft_id: str) -> AtomicNote:
    d = db.get_draft(draft_id)
    if not d:
        raise ValueError(f"draft {draft_id} not found")
    return _commit(d, "accepted")


def edit_and_accept(edited: DraftAtom) -> AtomicNote:
    # Persist the edited draft, then commit it as "edited"
    db.upsert_draft(edited)
    return _commit(edited, "edited")


def reject(draft_id: str, reason: str) -> dict:
    d = db.get_draft(draft_id)
    if not d:
        raise ValueError(f"draft {draft_id} not found")

    db.log_event(
        EvalEvent(
            id=f"ev-{uuid.uuid4().hex[:8]}",
            timestamp=now(),
            kind="reject",
            payload={
                "draft_id": draft_id,
                "suggested_id": d.suggested_id,
                "prompt_version": d.prompt_version,
                "reason": reason,
            },
        )
    )
    db.delete_draft(draft_id)
    return {"ok": True, "draft_id": draft_id}
