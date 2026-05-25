"""Manual note authoring — the scholar writes a note from scratch, no source.

Bypasses the Extractor agent. Directly constructs a DraftAtom with
`origin.source_id=None` and `scholar_action="originated"`, then runs it
through the same `_commit()` funnel as accepted drafts.

This means: same registry validation, same hooks, same timeline event.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from openacad.notes.schema import (
    AtomKind,
    AtomicNote,
    DraftAtom,
    Relation,
)
from openacad.notes.curation._legacy import _commit


def _slug(content: str, max_len: int = 60) -> str:
    """Cheap slug from the first ~60 chars of content."""
    import re
    s = content.strip().lower()[:max_len]
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s or f"note-{uuid.uuid4().hex[:8]}"


def author_note(
    content: str,
    kind: AtomKind,
    tags: list[str] | None = None,
    attributes: dict | None = None,
    relations: list[Relation] | None = None,
    suggested_id: str | None = None,
) -> AtomicNote:
    """Create an atom from scratch, no source provenance.

    The atom enters the vault with `scholar_action="originated"`, distinguishing
    it in the timeline from agent-drafted atoms that were `accepted` or `edited`.
    """
    if not content.strip():
        raise ValueError("authored note content cannot be empty")

    sid = suggested_id or _slug(content)
    d = DraftAtom(
        draft_id=f"dr-{uuid.uuid4().hex[:8]}",
        drafted_at=datetime.now(timezone.utc),
        prompt_version="scholar-originated",  # marker, not a real prompt
        source_id="",                          # no source — scholar-originated
        chunk_ids=[],
        page_range=(0, 0),
        type=kind,
        suggested_id=sid,
        tags=tags or [],
        attributes=attributes or {},
        relations=relations or [],
        content=content,
        confidence_score=1.0,                  # scholar-authored = trusted
    )
    return _commit(d, scholar_action="originated")


__all__ = ["author_note"]
