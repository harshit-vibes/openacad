"""Lifecycle hook fired after an atom is committed to the vault.

Each side-effect is gated on the active scenario's capability flags so the
progressive ladder of scenarios (atoms-only → atoms-attrs → atoms-attrs-rels →
+ atom embeddings → + HITL → + self-improving) is honored:

  - graph upsert          : `has_relations`           (no graph if no relations)
  - atom-embedding upsert : `has_atom_embeddings`     (no MiniLM if disabled)
  - registry promotion    : `has_attributes` or `has_relations`
                            (nothing to promote if neither)
"""

from __future__ import annotations

from openacad.notes.schema import AtomicNote


def fire(atom: AtomicNote) -> None:
    """Side-effects of an atom being accepted into the vault."""
    from openacad.runtime.scenario import active_scenario
    scn = active_scenario()

    if scn.has_relations:
        from openacad.notes.persistence import graph_index as graph_service
        graph_service.get_graph().upsert(atom)

    if scn.has_atom_embeddings:
        from openacad.notes.query import semantic as semantic_service
        semantic_service.atoms_store().upsert(atom.metas.id, atom.content)

    if scn.has_attributes or scn.has_relations:
        from openacad.notes.registry import _legacy as registry_service
        registry_service.recount_usage_and_promote()
