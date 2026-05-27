"""AtomicNote browse + filter + detail + edit — Phase 3."""

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from openacad.notes.schema import AtomicNote, AtomKind

from openacad.feedback.schema import EvalEvent
from openacad.notes.persistence import graph_index as graph_service
from openacad.notes.registry import _legacy as registry_service
from openacad.notes.query import hybrid
from openacad.notes.query import semantic as semantic_service
from openacad.notes.persistence import vault as vault_io
from openacad.runtime import db
router = APIRouter()


@router.get("", response_model=list[AtomicNote])
def list_notes(
    type: AtomKind | None = None,
    tag: str | None = None,
    where_key: str | None = Query(None, description="Attribute key for equality filter"),
    where_value: str | None = Query(None, description="Attribute value (string-cast)"),
    keyword: str | None = Query(None, description="Substring match against body"),
    limit: int = 50,
) -> list[AtomicNote]:
    """Filtered atom browse via the same retrieval planner used by the synthesis agent."""
    where = {where_key: where_value} if where_key and where_value else None
    result = retrieval.query(type=type, where=where, keyword=keyword, limit=limit)

    atoms = result.atoms
    if tag:
        atoms = [a for a in atoms if tag in a.metas.tags]
    return atoms


@router.get("/{atom_id}", response_model=AtomicNote)
def get_note(atom_id: str) -> AtomicNote:
    try:
        return vault_io.read_atom(atom_id)
    except FileNotFoundError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, atom_id) from e


class NotePatch(BaseModel):
    content: str | None = None
    tags: list[str] | None = None
    attributes: dict[str, Any] | None = None
    status: str | None = None


@router.put("/{atom_id}", response_model=AtomicNote)
def update_note(atom_id: str, patch: NotePatch) -> AtomicNote:
    """Scholar-edit an existing atom. Bumps updated_at; revalidates; logs eval event."""
    import uuid

    try:
        atom = vault_io.read_atom(atom_id)
    except FileNotFoundError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, atom_id) from e

    if patch.content is not None:
        atom.content = patch.content
    if patch.tags is not None:
        atom.metas.tags = patch.tags
    if patch.attributes is not None:
        atom.attributes = patch.attributes
    if patch.status is not None:
        atom.metas.status = patch.status  # type: ignore[assignment]
    atom.metas.updated_at = datetime.now(timezone.utc)

    errors = registry_service.validate_atom(atom)
    if errors:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "; ".join(errors))

    vault_io.write_atom(atom)
    db.upsert_atom_projection(atom)
    graph_service.get_graph().upsert(atom)
    semantic_service.atoms_store().upsert(atom.metas.id, atom.content)

    db.log_event(
        EvalEvent(
            id=f"ev-{uuid.uuid4().hex[:8]}",
            timestamp=datetime.now(timezone.utc),
            kind="edit",
            payload={"atom_id": atom_id, "actor": "scholar"},
        )
    )
    return atom


@router.post("/{atom_id}/archive")
def archive_note(atom_id: str) -> dict:
    import uuid

    try:
        atom = vault_io.read_atom(atom_id)
    except FileNotFoundError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, atom_id) from e
    atom.metas.status = "archived"
    atom.metas.updated_at = datetime.now(timezone.utc)
    vault_io.write_atom(atom)
    db.upsert_atom_projection(atom)
    db.log_event(
        EvalEvent(
            id=f"ev-{uuid.uuid4().hex[:8]}",
            timestamp=datetime.now(timezone.utc),
            kind="edit",
            payload={"atom_id": atom_id, "action": "archive"},
        )
    )
    return {"ok": True, "atom_id": atom_id}
