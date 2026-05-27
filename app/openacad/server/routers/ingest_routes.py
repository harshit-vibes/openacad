"""Ingest / paper-library API routes for the Next.js playground.

Endpoints:

- ``GET /ingest/papers``                list ingested documents
- ``GET /ingest/papers/{doc_id}``       per-doc detail (chunks + atoms-derived)
- ``GET /ingest/chunks/{doc_id}``       all chunks for a doc
- ``GET /ingest/stats``                 ingest-pipeline KPI rollup
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from openacad.server.deps import get_vault
from openacad.vault import Vault, read_chunks

router = APIRouter()


def _papers_summary(vault: Vault) -> list[dict[str, Any]]:
    docs_dir = vault.documents_dir
    chunks_dir = vault.chunks_dir
    out: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    # Source 1: PDF files in documents/
    if docs_dir.exists():
        for pdf in sorted(docs_dir.glob("*.pdf")):
            doc_id = pdf.stem
            seen_ids.add(doc_id)
            chunks_path = chunks_dir / f"{doc_id}.jsonl"
            n_chunks = 0
            if chunks_path.exists():
                try:
                    n_chunks = sum(1 for _ in read_chunks(chunks_path))
                except Exception:  # noqa: BLE001
                    n_chunks = 0
            out.append({
                "doc_id": doc_id,
                "pdf_path": str(pdf),
                "n_chunks": n_chunks,
                "n_atoms": _count_atoms_for_doc(vault, doc_id),
                "has_pdf": True,
            })

    # Source 2: chunk JSONLs without a matching PDF (legacy / migrated data).
    if chunks_dir.exists():
        for jsonl in sorted(chunks_dir.glob("*.jsonl")):
            doc_id = jsonl.stem
            if doc_id in seen_ids:
                continue
            try:
                n_chunks = sum(1 for _ in read_chunks(jsonl))
            except Exception:  # noqa: BLE001
                n_chunks = 0
            out.append({
                "doc_id": doc_id,
                "pdf_path": None,
                "n_chunks": n_chunks,
                "n_atoms": _count_atoms_for_doc(vault, doc_id),
                "has_pdf": False,
            })

    return out


def _count_atoms_for_doc(vault: Vault, doc_id: str) -> int:
    count = 0
    for atom in vault.atoms:
        for src in atom.sources:
            if src.document == doc_id:
                count += 1
                break
    return count


@router.get("/papers")
def list_papers(vault: Vault = Depends(get_vault)) -> dict[str, Any]:
    papers = _papers_summary(vault)
    return {"papers": papers, "count": len(papers)}


@router.get("/papers/{doc_id}")
def get_paper(doc_id: str, vault: Vault = Depends(get_vault)) -> dict[str, Any]:
    chunks_path = vault.chunks_dir / f"{doc_id}.jsonl"
    pdf_path = vault.documents_dir / f"{doc_id}.pdf"
    if not chunks_path.exists() and not pdf_path.exists():
        raise HTTPException(status_code=404, detail=f"doc {doc_id!r} not found")

    chunks: list[dict[str, Any]] = []
    if chunks_path.exists():
        try:
            for chunk in read_chunks(chunks_path):
                chunks.append({
                    "id": chunk.id,
                    "doc_id": chunk.doc_id,
                    "page": chunk.page,
                    "char_start": chunk.char_start,
                    "char_end": chunk.char_end,
                    "n_chars": len(chunk.text),
                    "preview": chunk.text[:200],
                })
        except Exception as e:  # noqa: BLE001
            raise HTTPException(status_code=500, detail=f"failed to read chunks: {e}")

    # Atoms derived from this doc.
    derived: list[dict[str, Any]] = []
    for atom in vault.atoms:
        for src in atom.sources:
            if src.document == doc_id:
                derived.append({
                    "id": atom.id,
                    "type": atom.type,
                    "status": atom.status,
                    "chunk": src.chunk,
                    "page": src.page,
                })
                break

    return {
        "doc_id": doc_id,
        "has_pdf": pdf_path.exists(),
        "pdf_path": str(pdf_path) if pdf_path.exists() else None,
        "n_chunks": len(chunks),
        "chunks": chunks,
        "n_atoms": len(derived),
        "atoms": derived,
    }


@router.get("/chunks/{doc_id}")
def get_chunks(doc_id: str, vault: Vault = Depends(get_vault)) -> list[dict[str, Any]]:
    chunks_path = vault.chunks_dir / f"{doc_id}.jsonl"
    if not chunks_path.exists():
        raise HTTPException(status_code=404, detail=f"no chunks for doc {doc_id!r}")
    out: list[dict[str, Any]] = []
    for chunk in read_chunks(chunks_path):
        out.append({
            "id": chunk.id,
            "doc_id": chunk.doc_id,
            "page": chunk.page,
            "char_start": chunk.char_start,
            "char_end": chunk.char_end,
            "text": chunk.text,
        })
    return out


@router.get("/stats")
def ingest_stats(vault: Vault = Depends(get_vault)) -> dict[str, Any]:
    papers = _papers_summary(vault)
    total_chunks = sum(p["n_chunks"] for p in papers)
    total_atoms = sum(p["n_atoms"] for p in papers)
    return {
        "n_papers": len(papers),
        "n_chunks": total_chunks,
        "n_atoms_derived": total_atoms,
    }
