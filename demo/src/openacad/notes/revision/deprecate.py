"""Post-active note revision: mark a curated note as deprecated.

Doesn't delete — keeps the file with `metas.status="deprecated"` so
historical citations still resolve. Logs an EvalEvent so the timeline
shows the deprecation reason.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from openacad.feedback.schema import EvalEvent
from openacad.notes.persistence import vault as vault_io
from openacad.runtime import db


def deprecate(atom_id: str, reason: str) -> dict:
    """Mark an active atom as deprecated with a scholar-provided reason."""
    atom = vault_io.read_atom(atom_id)
    if atom is None:
        raise ValueError(f"no atom with id={atom_id!r}")
    if atom.metas.status == "deprecated":
        return {"atom_id": atom_id, "status": "already-deprecated"}

    atom.metas.status = "deprecated"
    atom.metas.updated_at = datetime.now(timezone.utc)
    atom.origin.scholar_action = "deprecated"

    vault_io.write_atom(atom)
    db.upsert_atom_projection(atom)

    db.log_event(
        EvalEvent(
            id=f"ev-{uuid.uuid4().hex[:8]}",
            timestamp=datetime.now(timezone.utc),
            kind="deprecate",
            payload={"atom_id": atom_id, "reason": reason},
        )
    )
    return {"atom_id": atom_id, "status": "deprecated", "reason": reason}


__all__ = ["deprecate"]
