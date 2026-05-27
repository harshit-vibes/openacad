"""Populate the 3 Phase-2 atom-tier scenarios via extraction with the
right capability mask per scenario.

Run AFTER the SDG PDFs are ingested and after a model swap that gives you
cheap-enough extraction (default: google/gemini-2.5-flash).

  .venv/bin/python scripts/seed_atom_decomposition.py

Each scenario runs the same extractor but the per-scenario flags in
`scenarios/definitions.py` cause `tools/atoms_extract.py` to scrub attributes
and/or relations from the drafted atoms before they're written:

  atoms-only        → no attrs, no rels, no atom embeddings
  atoms-attrs       → attrs yes, no rels, no atom embeddings
  atoms-attrs-rels  → attrs + rels, no atom embeddings

All three auto-accept every valid draft (no HITL).
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
NEW_SCENARIOS = ["atoms-only", "atoms-attrs", "atoms-attrs-rels"]


def _wipe_atoms(scenario_key: str) -> int:
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


def _extract_for(scenario_key: str, source_ids: list[str]) -> int:
    n_total = 0
    with use_scenario(scenario_key):
        for sid in source_ids:
            existing = db.drafts_for_source(sid)
            if existing:
                print(f"    {sid}: {len(existing)} drafts already pending, skipping extraction")
                n_total += len(existing)
                continue
            print(f"    {sid}: extracting…", flush=True)
            ds = extraction_pipeline.draft(sid)
            extraction_pipeline.validate([d.draft_id for d in ds])
            extraction_pipeline.score([d.draft_id for d in ds])
            n_total += len(ds)
            print(f"      → {len(ds)} drafts produced", flush=True)
    return n_total


def _accept_all(scenario_key: str) -> dict:
    n_accepted = n_errored = 0
    with use_scenario(scenario_key):
        for src in db.list_sources():
            for d in db.drafts_for_source(src.id):
                if d.validation_errors:
                    n_errored += 1
                    continue
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
    return {"accepted": n_accepted, "errored": n_errored}


def main() -> None:
    print("== seed atom-decomposition scenarios (P2 ladder) ==")

    # Optional CLI args restrict which scenarios to seed (skip already-done ones).
    keys_to_seed = sys.argv[1:] if len(sys.argv) > 1 else NEW_SCENARIOS
    unknown = [k for k in keys_to_seed if k not in NEW_SCENARIOS]
    if unknown:
        print(f"ERROR: unknown scenario key(s): {unknown}. Valid: {NEW_SCENARIOS}", file=sys.stderr)
        sys.exit(1)
    print(f"  seeding: {keys_to_seed}\n")

    sources = db.list_sources()
    sdg_sources = [s.id for s in sources if "sdg-briefing" in s.id]
    if not sdg_sources:
        print("ERROR: no SDG sources ingested. Run `make seed` first.", file=sys.stderr)
        sys.exit(1)
    print(f"  {len(sdg_sources)} SDG PDFs available\n")

    for key in keys_to_seed:
        print(f"— {key} —")
        wiped = _wipe_atoms(key)
        if wiped:
            print(f"  wiped {wiped} pre-existing atoms")
        n_drafts = _extract_for(key, sdg_sources)
        stats = _accept_all(key)
        with use_scenario(key):
            n_atoms = len(db.list_atom_projections())
        print(f"  result: {n_drafts} drafts → {stats} → {n_atoms} atoms in {key}\n")

    print("done.\n")
    print("Final atom counts across all 3 ladder scenarios:")
    for key in NEW_SCENARIOS:
        with use_scenario(key):
            n = len(db.list_atom_projections())
        marker = " ← just seeded" if key in keys_to_seed else ""
        print(f"  {key:22} {n} atoms{marker}")


if __name__ == "__main__":
    main()
