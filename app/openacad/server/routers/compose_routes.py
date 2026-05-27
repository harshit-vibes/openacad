"""Compose stub route.

The real composer agent ships in a later milestone. This stub returns a
structured plan + atom citations from the vault FTS so the UI can render
a realistic-looking artifact while the agent wiring lands.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from openacad.server.deps import get_vault
from openacad.vault import Vault

router = APIRouter()


class ComposeRequest(BaseModel):
    preset: str = Field(default="brief", description="brief | paper | book")
    title: str = Field(default="Untitled")
    sections: list[str] = Field(default_factory=list)
    brief: str = Field(default="", description="Author's prompt / outline")


@router.post("")
def compose(req: ComposeRequest, vault: Vault = Depends(get_vault)) -> dict[str, Any]:
    """Return a stub artifact stitched from vault FTS hits per section."""
    # For each section, run a tiny FTS lookup so the response feels real.
    sections: list[dict[str, Any]] = []
    for heading in req.sections or [req.title]:
        hits = vault.search(heading, top_k=5)
        sections.append({
            "heading": heading,
            "atoms_cited": [
                {"id": a.id, "type": a.type, "body_preview": a.body[:160]}
                for a in hits
            ],
            "draft": (
                f"## {heading}\n\n"
                + (
                    "\n\n".join(f"- {a.body[:240]}" for a in hits)
                    if hits
                    else "_No vault atoms matched this heading yet._"
                )
            ),
        })
    return {
        "preset": req.preset,
        "title": req.title,
        "brief": req.brief,
        "sections": sections,
        "status": "stub",
        "note": "Composer agent ships in a later milestone; results are stub assembled from FTS.",
    }
