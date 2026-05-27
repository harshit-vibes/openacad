"""Paper library projection — what the Ingest page renders."""

from __future__ import annotations

from openacad.runtime import db
from openacad.runtime.scenario import use_scenario

from openacad.projections._models import PaperLibraryView, PaperRow


def paper_library(scenario_key: str = "evolving-notes") -> PaperLibraryView:
    """Read-only roll-up of every paper ingested for the given scenario.

    Counts of chunks (shared corpus) and atoms (per-scenario) are computed
    on the fly so the view is always fresh.
    """
    with use_scenario(scenario_key):
        sources = db.list_sources()

        # Build atom-count index keyed by source_id once.
        atoms = db.list_atom_projections()
        atoms_by_source: dict[str, int] = {}
        for a in atoms:
            sid = a.get("source_id")
            if sid:
                atoms_by_source[sid] = atoms_by_source.get(sid, 0) + 1

        rows: list[PaperRow] = []
        total_chunks = 0
        total_atoms = 0
        last_ingested_at = None
        for s in sources:
            chunks = db.chunks_for_source(s.id)
            n_atoms = atoms_by_source.get(s.id, 0)
            rows.append(
                PaperRow(
                    source_id=s.id,
                    title=s.title or s.filename,
                    authors=[],  # not modeled in PaperSource — left blank
                    year=None,
                    pages=s.n_pages,
                    chunks=len(chunks),
                    atoms=n_atoms,
                    ingested_at=s.uploaded_at,
                )
            )
            total_chunks += len(chunks)
            total_atoms += n_atoms
            if last_ingested_at is None or s.uploaded_at > last_ingested_at:
                last_ingested_at = s.uploaded_at

        return PaperLibraryView(
            papers=rows,
            total_papers=len(rows),
            total_chunks=total_chunks,
            total_atoms=total_atoms,
            last_ingested_at=last_ingested_at,
        )
