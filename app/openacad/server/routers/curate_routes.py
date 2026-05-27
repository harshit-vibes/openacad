"""Curation (drafts) read-only API routes for the Next.js playground.

The Next.js playground is intentionally read-only for curation — the
accept / edit / reject verdicts live in the CLI (`openacad curate`). The
UI only mirrors the pending draft queue so scholars can see what's
waiting.

Endpoints:

- ``GET /curate/drafts``                list pending drafts (across all docs)
- ``GET /curate/drafts/{doc_id}``       drafts pending for one document
- ``GET /curate/drafts/{doc_id}/{draft_name}`` full draft body + source quote
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from openacad.server.deps import get_vault
from openacad.vault import AtomicNote, Vault

router = APIRouter()


def _list_doc_drafts(vault: Vault, doc_dir: Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for md in sorted(doc_dir.glob("draft-*.md")):
        text = md.read_text("utf-8")
        try:
            atom = AtomicNote.from_markdown(text, id=md.stem)
            out.append({
                "doc_id": doc_dir.name,
                "draft_name": md.name,
                "draft_id": md.stem,
                "type": atom.type,
                "domain": atom.attributes.get("domain"),
                "body_preview": (
                    atom.body[:240] + "…" if len(atom.body) > 240 else atom.body
                ),
                "n_sources": len(atom.sources),
            })
        except Exception as e:  # noqa: BLE001 — surface parse problems
            out.append({
                "doc_id": doc_dir.name,
                "draft_name": md.name,
                "draft_id": md.stem,
                "parse_error": str(e),
                "body_preview": text[:240],
            })
    return out


@router.get("/drafts")
def list_drafts(vault: Vault = Depends(get_vault)) -> dict[str, Any]:
    drafts_dir = vault.drafts_dir
    out: list[dict[str, Any]] = []
    if drafts_dir.exists():
        for doc_dir in sorted(drafts_dir.iterdir()):
            if not doc_dir.is_dir():
                continue
            if doc_dir.name.startswith("."):
                continue
            out.extend(_list_doc_drafts(vault, doc_dir))
    return {"drafts": out, "count": len(out)}


@router.get("/drafts/{doc_id}")
def list_doc_drafts(doc_id: str, vault: Vault = Depends(get_vault)) -> dict[str, Any]:
    doc_dir = vault.drafts_dir / doc_id
    if not doc_dir.exists():
        raise HTTPException(status_code=404, detail=f"no drafts dir for doc {doc_id!r}")
    drafts = _list_doc_drafts(vault, doc_dir)
    return {"doc_id": doc_id, "drafts": drafts, "count": len(drafts)}


@router.get("/drafts/{doc_id}/{draft_name}")
def get_draft(
    doc_id: str,
    draft_name: str,
    vault: Vault = Depends(get_vault),
) -> dict[str, Any]:
    md = vault.drafts_dir / doc_id / draft_name
    # Permit either "draft-001" or "draft-001.md".
    if not md.exists() and not md.name.endswith(".md"):
        md = md.with_suffix(".md")
    if not md.exists():
        raise HTTPException(status_code=404, detail=f"draft {draft_name!r} not found")

    text = md.read_text("utf-8")
    try:
        atom = AtomicNote.from_markdown(text, id=md.stem)
    except Exception as e:  # noqa: BLE001
        return {
            "doc_id": doc_id,
            "draft_name": md.name,
            "raw": text,
            "parse_error": str(e),
        }

    source_text: str | None = None
    try:
        source_text = vault.source_text(atom) or None
    except LookupError:
        source_text = None

    return {
        "doc_id": doc_id,
        "draft_name": md.name,
        "draft_id": md.stem,
        "type": atom.type,
        "status": atom.status,
        "tags": list(atom.tags),
        "attributes": dict(atom.attributes),
        "body": atom.body,
        "sources": [
            {
                "document": s.document,
                "chunk": s.chunk,
                "span": {"start": s.span.start, "end": s.span.end},
                "page": s.page,
            }
            for s in atom.sources
        ],
        "source_text": source_text,
        "raw": text,
    }
