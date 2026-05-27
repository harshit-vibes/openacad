"""Populate the three atom-tier scenarios from the same extraction pool with
different acceptance policies. Makes the 6-way comparison meaningful.

Policy:
- Drafted Notes: accept ALL valid drafts (noisy, dense)
- Curated Notes: accept only drafts with confidence_score >= MIN_CURATED (cleaner)
- Evolving Notes: same atoms as Curated Notes (the differentiation is prompt
  evolution at runtime via the Meta-Evaluator, not extraction policy)

Run AFTER the SDG PDFs are ingested:

    .venv/bin/python scripts/prepare_atom_scenarios.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from openacad.runtime.scenario import use_scenario
from openacad.notes.curation import _legacy as curate_service
from openacad.runtime import db
from openacad.notes.intake import from_chunks as extraction_pipeline
from openacad.notes.persistence import vault as vault_io
MIN_CURATED_CONFIDENCE = 0.8


def _extract_and_score_all(scenario_key: str, source_ids: list[str]) -> dict:
    """Run extraction over every source for the scenario; return drafts produced.
    Idempotent: skips sources that already have drafts pending."""
    out: dict[str, int] = {}
    with use_scenario(scenario_key):
        for sid in source_ids:
            existing = db.drafts_for_source(sid)
            if existing:
                print(f"    {sid}: {len(existing)} drafts already pending, skipping extraction")
                out[sid] = len(existing)
                continue
            print(f"    {sid}: extracting…", flush=True)
            ds = extraction_pipeline.draft(sid)
            extraction_pipeline.validate([d.draft_id for d in ds])
            extraction_pipeline.score([d.draft_id for d in ds])
            out[sid] = len(ds)
            print(f"      → {len(ds)} drafts produced", flush=True)
    return out


def _accept_with_policy(scenario_key: str, min_confidence: float | None) -> dict:
    """Walk pending drafts; accept those that pass validation AND clear the
    confidence threshold. Returns {accepted, errored, filtered_below_threshold}."""
    n_accepted = n_errored = n_below = 0
    with use_scenario(scenario_key):
        for src in db.list_sources():
            drafts = db.drafts_for_source(src.id)
            for d in drafts:
                if d.validation_errors:
                    n_errored += 1
                    continue
                if min_confidence is not None and (d.confidence_score or 0) < min_confidence:
                    n_below += 1
                    continue
                # Auto-suffix id collisions
                base = d.suggested_id
                suffix = 1
                while vault_io.atom_exists(d.suggested_id):
                    d.suggested_id = f"{base}-{suffix}"
                    suffix += 1
                if suffix > 1:
                    db.upsert_draft(d)
                try:
                    curate_service.accept(d.draft_id)
                    n_accepted += 1
                except ValueError:
                    n_errored += 1
    return {"accepted": n_accepted, "errored": n_errored, "below_threshold": n_below}


def _copy_atoms_from(src_scenario: str, dst_scenario: str) -> int:
    """Materialize the same set of atoms in dst as in src (clean copy of notes
    + projections + embeddings). Used to mirror Curated Notes into Evolving Notes."""
    from openacad.notes.query import semantic as semantic_service
    import shutil

    with use_scenario(src_scenario):
        src_atoms = vault_io.list_atoms()
    with use_scenario(dst_scenario):
        # wipe dst first
        for a in vault_io.list_atoms():
            try:
                vault_io.atom_path(a.metas.id).unlink()
                db.remove_atom_projection(a.metas.id)
                semantic_service.atoms_store().remove(a.metas.id)
            except Exception:
                pass
    # copy
    n = 0
    for a in src_atoms:
        with use_scenario(dst_scenario):
            vault_io.write_atom(a)
            db.upsert_atom_projection(a)
            semantic_service.atoms_store().upsert(a.metas.id, a.content)
            n += 1
    return n


def _wipe_atoms(scenario_key: str) -> int:
    """Remove all atoms (notes + projections + embeddings) from the scenario.
    Used to start each scenario from a clean slate before the differentiated
    population pass."""
    from openacad.notes.query import semantic as semantic_service
    n = 0
    with use_scenario(scenario_key):
        for a in vault_io.list_atoms():
            try:
                vault_io.atom_path(a.metas.id).unlink()
                db.remove_atom_projection(a.metas.id)
                semantic_service.atoms_store().remove(a.metas.id)
                n += 1
            except Exception:
                pass
    return n


def main() -> None:
    print("== prepare atom-tier scenarios with differentiated policies ==")

    sources = db.list_sources()
    sdg_sources = [s.id for s in sources if "sdg-briefing" in s.id]
    if not sdg_sources:
        print("ERROR: no SDG sources ingested. Run `make seed` first.", file=sys.stderr)
        sys.exit(1)
    print(f"  {len(sdg_sources)} SDG PDFs available")

    # Wipe existing atoms so each scenario starts clean
    for key in ("drafted-notes", "curated-notes", "evolving-notes"):
        n = _wipe_atoms(key)
        print(f"  wiped {n} pre-existing atoms from {key}")

    # ── Drafted Notes: extract + accept ALL ─────────────────────────────
    print("\n— Drafted Notes (auto-accept all valid drafts) —")
    _extract_and_score_all("drafted-notes", sdg_sources)
    drafted_stats = _accept_with_policy("drafted-notes", min_confidence=None)
    with use_scenario("drafted-notes"):
        drafted_n = len(db.list_atom_projections())
    print(f"  result: {drafted_stats}  →  {drafted_n} atoms in Drafted Notes")

    # ── Curated Notes: extract + accept only high-confidence ────────────
    print(f"\n— Curated Notes (accept only confidence >= {MIN_CURATED_CONFIDENCE}) —")
    _extract_and_score_all("curated-notes", sdg_sources)
    curated_stats = _accept_with_policy("curated-notes", min_confidence=MIN_CURATED_CONFIDENCE)
    with use_scenario("curated-notes"):
        curated_n = len(db.list_atom_projections())
    print(f"  result: {curated_stats}  →  {curated_n} atoms in Curated Notes")

    # ── Evolving Notes: mirror Curated Notes ────────────────────────────
    print("\n— Evolving Notes (mirror of Curated Notes; prompts evolve at runtime) —")
    n_copied = _copy_atoms_from("curated-notes", "evolving-notes")
    with use_scenario("evolving-notes"):
        evolving_n = len(db.list_atom_projections())
    print(f"  mirrored {n_copied} atoms  →  {evolving_n} atoms in Evolving Notes")

    print("\ndone.")
    print(f"\nFinal atom counts:")
    print(f"  Drafted Notes:  {drafted_n}")
    print(f"  Curated Notes:  {curated_n}")
    print(f"  Evolving Notes: {evolving_n}")


if __name__ == "__main__":
    main()
