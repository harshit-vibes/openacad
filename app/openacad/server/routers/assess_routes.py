"""Coverage-assessment stub route.

Real coverage analysis ships in a later milestone. This stub does a cheap
heuristic: tokenise the input, run a few FTS searches, report which atom
ids would be cited and which "topics" appear under-represented.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from openacad.server.deps import get_vault
from openacad.vault import Vault

router = APIRouter()


_STOPWORDS = {
    "the", "a", "an", "of", "to", "in", "and", "or", "is", "are", "was",
    "were", "be", "been", "for", "on", "at", "by", "with", "as", "that",
    "this", "it", "its", "from", "we", "our", "their", "they", "but",
}


class AssessRequest(BaseModel):
    text: str = Field(..., description="Draft / artifact to assess")
    top_terms: int = Field(default=10, ge=3, le=30)


@router.post("")
def assess(req: AssessRequest, vault: Vault = Depends(get_vault)) -> dict[str, Any]:
    # Extract candidate terms (word tokens >= 4 chars, lowercased, deduped).
    tokens = re.findall(r"[A-Za-z][A-Za-z\-]{3,}", req.text.lower())
    tokens = [t for t in tokens if t not in _STOPWORDS]
    most_common = [t for t, _c in Counter(tokens).most_common(req.top_terms)]

    findings: list[dict[str, Any]] = []
    matched_atoms: set[str] = set()
    for term in most_common:
        hits = vault.search(term, top_k=3)
        findings.append({
            "term": term,
            "n_hits": len(hits),
            "atoms": [{"id": a.id, "type": a.type} for a in hits],
            "coverage": "covered" if hits else "gap",
        })
        for a in hits:
            matched_atoms.add(a.id)

    gaps = [f for f in findings if f["coverage"] == "gap"]
    covered = [f for f in findings if f["coverage"] == "covered"]

    return {
        "n_chars": len(req.text),
        "top_terms": most_common,
        "findings": findings,
        "gaps": gaps,
        "n_atoms_matched": len(matched_atoms),
        "matched_atoms": sorted(matched_atoms),
        "summary": {
            "covered_terms": len(covered),
            "gap_terms": len(gaps),
            "coverage_ratio": (
                round(len(covered) / max(1, len(findings)), 3) if findings else 0
            ),
        },
        "status": "stub",
        "note": "Heuristic coverage scan; full assessor agent ships in a later milestone.",
    }
