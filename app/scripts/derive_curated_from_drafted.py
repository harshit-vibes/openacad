"""Fallback population path — derive Curated Notes from Drafted Notes without
additional LLM calls.

Used when prepare_atom_scenarios.py hits LLM rate/credit limits mid-flight.

Policy:
- Drafted Notes is the source of truth (assumed already populated via LLM extraction).
- Curated Notes = subset of Drafted atoms that have at least one relation
  AND at least two attributes — a heuristic proxy for "well-formed enough to keep."
- Evolving Notes = mirror of Curated Notes.

After running, all three atom-tier scenarios have atoms and the 6-way head-to-head
will produce meaningful results.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from openacad.runtime.scenario import use_scenario
from openacad.runtime import db
from openacad.notes.query import semantic as semantic_service
from openacad.notes.persistence import vault as vault_io
MIN_ATTRS = 2
MIN_RELS = 0     # was 1 (too strict — dropped 188/200 atoms); now relation-optional


def _wipe(scenario_key: str) -> int:
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


def _copy_atoms(src_key: str, dst_key: str, *, filter_fn=None) -> int:
    """Copy atoms from src scenario to dst (optionally filtered). Returns count."""
    with use_scenario(src_key):
        src_atoms = vault_io.list_atoms()
    if filter_fn:
        src_atoms = [a for a in src_atoms if filter_fn(a)]
    n = 0
    for a in src_atoms:
        with use_scenario(dst_key):
            vault_io.write_atom(a)
            db.upsert_atom_projection(a)
            semantic_service.atoms_store().upsert(a.metas.id, a.content)
            n += 1
    return n


def well_formed(atom) -> bool:
    return len(atom.attributes) >= MIN_ATTRS and len(atom.relations) >= MIN_RELS


def main() -> None:
    print("== derive Curated + Evolving from Drafted (no LLM) ==")

    # Check Drafted is populated
    with use_scenario("drafted-notes"):
        drafted_atoms = vault_io.list_atoms()
    if not drafted_atoms:
        print("ERROR: Drafted Notes is empty. Run prepare_atom_scenarios.py first.",
              file=sys.stderr)
        sys.exit(1)
    print(f"  Drafted Notes has {len(drafted_atoms)} atoms")

    n_well_formed = sum(1 for a in drafted_atoms if well_formed(a))
    print(f"  {n_well_formed} atoms are well-formed (≥{MIN_ATTRS} attrs, ≥{MIN_RELS} rels)")

    print("\n— Curated Notes: copy well-formed subset of Drafted —")
    n_wiped = _wipe("curated-notes")
    print(f"  wiped {n_wiped} pre-existing atoms")
    n_copied = _copy_atoms("drafted-notes", "curated-notes", filter_fn=well_formed)
    print(f"  copied {n_copied} well-formed atoms → Curated Notes")

    print("\n— Evolving Notes: mirror of Curated —")
    n_wiped = _wipe("evolving-notes")
    print(f"  wiped {n_wiped} pre-existing atoms")
    n_copied = _copy_atoms("curated-notes", "evolving-notes")
    print(f"  mirrored {n_copied} atoms → Evolving Notes")

    print("\ndone.")
    for k in ("drafted-notes", "curated-notes", "evolving-notes"):
        with use_scenario(k):
            print(f"  {k}: {len(vault_io.list_atoms())} atoms")


if __name__ == "__main__":
    main()
