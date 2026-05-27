"""Vault-backed API routes for the Next.js playground.

Endpoints:

- ``GET /vault/atoms``                          paginated list (filter by type, domain)
- ``GET /vault/atoms/{atom_id}``                full AtomicNote dump
- ``GET /vault/atoms/{atom_id}/incoming``       atoms wiki-linking to atom_id
- ``GET /vault/atoms/{atom_id}/outgoing``       outgoing edges
- ``GET /vault/atoms/{atom_id}/source``         exact source-quote substring
- ``GET /vault/search?q=...``                   FTS over atom bodies
- ``GET /vault/semantic?q=...``                 MiniLM cosine semantic search
- ``GET /vault/registry``                       attribute + relation schema view
- ``GET /vault/stats``                          totals (atoms, chunks, papers, attrs, rels)
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from openacad.server.deps import get_vault
from openacad.vault import AtomicNote, Vault

router = APIRouter()


# ---------------------------------------------------------------------------
# Serialisation helpers — pydantic .model_dump() is fine, but we want
# stable, JSON-safe shapes (sets → sorted lists, etc).
# ---------------------------------------------------------------------------


def _atom_summary(atom: AtomicNote) -> dict[str, Any]:
    """Cheap row for the atom table."""
    return {
        "id": atom.id,
        "type": atom.type,
        "status": atom.status,
        "domain": atom.attributes.get("domain"),
        "evidence": atom.attributes.get("evidence"),
        "tags": list(atom.tags),
        "n_relations": len(atom.relations),
        "n_sources": len(atom.sources),
        "updated_at": atom.updated_at,
        "body_preview": (atom.body[:240] + "…") if len(atom.body) > 240 else atom.body,
    }


def _atom_full(atom: AtomicNote) -> dict[str, Any]:
    """Full DTO including relations + sources."""
    return {
        **_atom_summary(atom),
        "aliases": list(atom.aliases),
        "created_at": atom.created_at,
        "body": atom.body,
        "attributes": dict(atom.attributes),
        "sources": [
            {
                "document": s.document,
                "chunk": s.chunk,
                "span": {"start": s.span.start, "end": s.span.end},
                "page": s.page,
            }
            for s in atom.sources
        ],
        "relations": [{"type": r.type, "target": r.target} for r in atom.relations],
    }


# ---------------------------------------------------------------------------
# routes
# ---------------------------------------------------------------------------


@router.get("/atoms")
def list_atoms(
    type: str | None = Query(default=None, description="Filter by atom type"),
    domain: str | None = Query(default=None, description="Filter by domain attribute"),
    status: str | None = Query(default=None, description="Filter by status"),
    q: str | None = Query(default=None, description="Substring match on id / body"),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    vault: Vault = Depends(get_vault),
) -> dict[str, Any]:
    """Paginated list of atoms with simple filters."""
    atoms = vault.atoms
    if type:
        atoms = [a for a in atoms if a.type == type]
    if domain:
        atoms = [a for a in atoms if a.attributes.get("domain") == domain]
    if status:
        atoms = [a for a in atoms if a.status == status]
    if q:
        ql = q.lower()
        atoms = [a for a in atoms if ql in a.id.lower() or ql in a.body.lower()]
    total = len(atoms)
    page = atoms[offset : offset + limit]
    return {
        "atoms": [_atom_summary(a) for a in page],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/atoms/{atom_id}")
def get_atom(atom_id: str, vault: Vault = Depends(get_vault)) -> dict[str, Any]:
    atom = vault.atom(atom_id)
    if atom is None:
        raise HTTPException(status_code=404, detail=f"atom {atom_id!r} not found")
    return _atom_full(atom)


@router.get("/atoms/{atom_id}/incoming")
def atom_incoming(atom_id: str, vault: Vault = Depends(get_vault)) -> list[dict[str, Any]]:
    if vault.atom(atom_id) is None:
        raise HTTPException(status_code=404, detail=f"atom {atom_id!r} not found")
    return [_atom_summary(a) for a in vault.incoming(atom_id)]


@router.get("/atoms/{atom_id}/outgoing")
def atom_outgoing(
    atom_id: str,
    type: str | None = Query(default=None, description="Filter by relation type"),
    vault: Vault = Depends(get_vault),
) -> list[dict[str, Any]]:
    if vault.atom(atom_id) is None:
        raise HTTPException(status_code=404, detail=f"atom {atom_id!r} not found")
    out: list[dict[str, Any]] = []
    atom = vault.atom(atom_id)
    assert atom is not None
    targets = vault.outgoing(atom_id, type=type)
    # Pair each neighbour with the relation type from the source atom.
    targets_by_id = {t.id: t for t in targets}
    for rel in atom.relations:
        if type is not None and rel.type != type:
            continue
        neighbour = targets_by_id.get(rel.target)
        if neighbour is None:
            out.append({"relation": rel.type, "target_id": rel.target, "atom": None})
        else:
            out.append({"relation": rel.type, "target_id": rel.target, "atom": _atom_summary(neighbour)})
    return out


@router.get("/atoms/{atom_id}/source")
def atom_source(atom_id: str, vault: Vault = Depends(get_vault)) -> dict[str, Any]:
    """Return the exact chunk substring referenced by the atom's source(s)."""
    atom = vault.atom(atom_id)
    if atom is None:
        raise HTTPException(status_code=404, detail=f"atom {atom_id!r} not found")
    try:
        text = vault.source_text(atom)
    except LookupError as e:
        return {
            "atom_id": atom_id,
            "text": None,
            "error": str(e),
            "sources": [
                {
                    "document": s.document,
                    "chunk": s.chunk,
                    "span": {"start": s.span.start, "end": s.span.end},
                    "page": s.page,
                }
                for s in atom.sources
            ],
        }
    return {
        "atom_id": atom_id,
        "text": text,
        "sources": [
            {
                "document": s.document,
                "chunk": s.chunk,
                "span": {"start": s.span.start, "end": s.span.end},
                "page": s.page,
            }
            for s in atom.sources
        ],
    }


@router.get("/search")
def search(
    q: str = Query(min_length=1),
    top_k: int = Query(default=10, ge=1, le=100),
    vault: Vault = Depends(get_vault),
) -> dict[str, Any]:
    hits = vault.search(q, top_k=top_k)
    return {
        "query": q,
        "results": [_atom_summary(a) for a in hits],
        "count": len(hits),
    }


@router.get("/semantic")
def semantic(
    q: str = Query(min_length=1),
    top_k: int = Query(default=10, ge=1, le=100),
    vault: Vault = Depends(get_vault),
) -> dict[str, Any]:
    try:
        hits = vault.semantic(q, top_k=top_k)
    except Exception as e:  # noqa: BLE001 — embedding model may not be loaded
        raise HTTPException(
            status_code=503,
            detail=f"semantic search unavailable: {e}",
        )
    return {
        "query": q,
        "results": [_atom_summary(a) for a in hits],
        "count": len(hits),
    }


@router.get("/registry")
def registry(vault: Vault = Depends(get_vault)) -> dict[str, Any]:
    reg = vault.registry
    return {
        "attributes": [
            {
                "name": name,
                "uses": defn.uses,
                "n_atoms": len(defn.atoms),
                "types": list(defn.types),
                "first_seen": defn.first_seen,
                "is_promoted": defn.is_promoted,
            }
            for name, defn in sorted(reg.attributes.items())
        ],
        "relations": [
            {
                "name": name,
                "uses": defn.uses,
                "n_atoms": len(defn.atoms),
                "inverse": defn.inverse,
                "first_seen": defn.first_seen,
                "is_promoted": defn.is_promoted,
            }
            for name, defn in sorted(reg.relations.items())
        ],
        "promoted_attributes": reg.promoted_attributes(),
        "promoted_relations": reg.promoted_relations(),
    }


@router.get("/stats")
def stats(vault: Vault = Depends(get_vault)) -> dict[str, Any]:
    """Top-level counts for KPI cards."""
    atoms = vault.atoms
    types: dict[str, int] = {}
    domains: dict[str, int] = {}
    statuses: dict[str, int] = {}
    total_relations = 0
    total_sources = 0
    for a in atoms:
        types[a.type] = types.get(a.type, 0) + 1
        statuses[a.status] = statuses.get(a.status, 0) + 1
        if a.attributes.get("domain"):
            d = str(a.attributes["domain"])
            domains[d] = domains.get(d, 0) + 1
        total_relations += len(a.relations)
        total_sources += len(a.sources)

    # Count docs + chunk files via vault sidecar.
    docs_dir = vault.documents_dir
    chunks_dir = vault.chunks_dir
    n_docs = len(list(docs_dir.glob("*.pdf"))) if docs_dir.exists() else 0
    n_chunk_files = len(list(chunks_dir.glob("*.jsonl"))) if chunks_dir.exists() else 0

    return {
        "n_atoms": len(atoms),
        "n_documents": n_docs,
        "n_chunk_files": n_chunk_files,
        "n_relations": total_relations,
        "n_sources": total_sources,
        "n_attributes": len(vault.registry.attributes),
        "n_relation_types": len(vault.registry.relations),
        "by_type": types,
        "by_status": statuses,
        "by_domain": domains,
    }
