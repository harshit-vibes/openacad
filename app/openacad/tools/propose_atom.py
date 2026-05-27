"""Emit a draft atom proposal.

Drafts are NOT written to the vault root — they land in
`<vault.path>/.openacad/drafts/<doc-id-or-misc>/draft-NNN.md` for the curation
loop to review. This tool returns the draft file path it wrote.
"""

from __future__ import annotations

import datetime as dt
import json
import re
import secrets
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any

from openacad.runtime.tool_registry import tool

if TYPE_CHECKING:
    from openacad.vault import Vault


_SLUG_RE = re.compile(r"[^a-z0-9-]+")


def _slug(text: str, n: int = 32) -> str:
    s = text.lower().strip()
    s = _SLUG_RE.sub("-", s).strip("-")
    return (s[:n] or "draft") if s else "draft"


def _drafts_dir(vault: "Any", doc_id: str | None) -> Path:
    """Resolve the drafts directory: <vault.path>/.openacad/drafts/<doc-id>/."""
    base = getattr(vault, "path", None) or getattr(vault, "root", None)
    if base is None:
        raise AttributeError("vault has neither .path nor .root attribute")
    drafts = Path(base) / ".openacad" / "drafts" / (doc_id or "misc")
    drafts.mkdir(parents=True, exist_ok=True)
    return drafts


def _next_draft_number(drafts_dir: Path) -> int:
    nums = []
    for p in drafts_dir.glob("draft-*.md"):
        m = re.match(r"draft-(\d+)\.md", p.name)
        if m:
            nums.append(int(m.group(1)))
    return (max(nums) + 1) if nums else 1


@tool
def propose_atom(
    body: Annotated[str, "Body markdown for the proposed atom (one self-contained claim)"],
    type: Annotated[
        str,
        "Atom kind: claim | concept | definition | finding | indicator | target | method | activity",
    ] = "claim",
    tags: Annotated[list[str] | None, "Optional tag list"] = None,
    doc_id: Annotated[
        str | None,
        "Source document id; the draft lands under .openacad/drafts/<doc_id>/",
    ] = None,
    chunk_id: Annotated[str | None, "Source chunk id, if known"] = None,
    span_start: Annotated[int | None, "Char offset start within the chunk text"] = None,
    span_end: Annotated[int | None, "Char offset end within the chunk text"] = None,
    page: Annotated[int | None, "Source page number"] = None,
    relations: Annotated[
        list[dict] | None,
        "Optional list of {type, target} dicts; targets reference existing atom ids",
    ] = None,
    *,
    vault: "Vault",
) -> dict[str, Any]:
    """Write a draft atom under .openacad/drafts/<doc_id>/draft-NNN.md and return its metadata.

    Returns: {"path": <str>, "draft_id": <str>, "type": <str>, "body_preview": <str>}.
    """
    drafts_dir = _drafts_dir(vault, doc_id)
    n = _next_draft_number(drafts_dir)
    now = dt.datetime.now(dt.UTC).isoformat()
    draft_id = f"draft-{n:03d}-{_slug(body[:48])}-{secrets.token_hex(2)}"

    fm: dict[str, Any] = {
        "type": type,
        "status": "pending",
        "tags": tags or [],
        "created_at": now,
    }
    src: dict[str, Any] = {}
    if doc_id:
        src["document"] = doc_id
    if chunk_id:
        src["chunk"] = chunk_id
    if span_start is not None and span_end is not None:
        src["span"] = {"start": span_start, "end": span_end}
    if page is not None:
        src["page"] = page
    if src:
        fm["source"] = src
    if relations:
        fm["relations"] = relations

    front = json.dumps(fm, indent=2, sort_keys=True)
    md = f"---\n{front}\n---\n\n{body.strip()}\n"

    path = drafts_dir / f"draft-{n:03d}.md"
    path.write_text(md, encoding="utf-8")

    return {
        "path": str(path),
        "draft_id": draft_id,
        "type": type,
        "body_preview": body.strip()[:120],
    }
