"""Notes-and-registry projection — atoms list + attribute/relation schema with
orphan detection.

We read the registry definitions directly off disk (via vault_io) instead of
the global `get_schema()` singleton, which caches against the first scenario
it sees and would otherwise lock the projection to a single vault.
"""

from __future__ import annotations

from openacad.notes.persistence import vault as vault_io
from openacad.notes.registry.schema import AttributeDef as RegistryAttributeDef
from openacad.notes.registry.schema import RelationDef as RegistryRelationDef
from openacad.runtime import db
from openacad.runtime.scenario import use_scenario

from openacad.projections._models import (
    AtomRow,
    AttributeDef,
    RegistryView,
    RelationDef,
)


_PREVIEW_CHARS = 200


def _allowed_values_as_strings(av) -> list[str] | None:
    if av is None:
        return None
    return [str(x) for x in av]


def registry_view(scenario_key: str = "evolving-notes") -> RegistryView:
    """Project atoms + registry schema for the Notes & Registry page."""
    with use_scenario(scenario_key):
        atom_projections = db.list_atom_projections()
        attrs_raw: list[RegistryAttributeDef] = vault_io.list_attribute_defs()
        rels_raw: list[RegistryRelationDef] = vault_io.list_relation_defs()

        # Build atom rows. We need the full atom content for the preview,
        # plus counts of attributes/relations from the index projection.
        atom_rows: list[AtomRow] = []
        # Tally which attribute keys / relation types are actually referenced
        # by any atom — used for orphan detection below.
        used_attr_keys: set[str] = set()
        used_rel_keys: set[str] = set()

        for proj in atom_projections:
            # Attribute counts come from any "attr.*" flat key.
            attr_keys = [
                k[len("attr."):] for k in proj.keys() if k.startswith("attr.")
            ]
            n_attrs = len(attr_keys)
            for k in attr_keys:
                used_attr_keys.add(k)

            rel_types = proj.get("relation_types", []) or []
            n_rels = len(rel_types)
            for t in rel_types:
                used_rel_keys.add(t)

            # Content preview — read the full atom (cheap; ~150 atoms typical).
            atom_id = proj["id"]
            try:
                full = vault_io.read_atom(atom_id)
                preview = (full.content or "")[:_PREVIEW_CHARS]
            except Exception:
                preview = ""

            atom_rows.append(
                AtomRow(
                    atom_id=atom_id,
                    kind=proj.get("type", ""),
                    content_preview=preview,
                    n_attrs=n_attrs,
                    n_rels=n_rels,
                    source_id=proj.get("source_id"),
                )
            )

        # Project schema definitions.
        attr_rows = [
            AttributeDef(
                key=a.key,
                value_type=a.value_type,
                allowed_values=_allowed_values_as_strings(a.allowed_values),
                usage_count=a.usage_count,
                first_seen=a.first_seen,
            )
            for a in attrs_raw
        ]
        rel_rows = [
            RelationDef(
                key=r.key,
                source_types=list(r.source_types),
                target_types=list(r.target_types),
                inverse=r.inverse,
                usage_count=r.usage_count,
            )
            for r in rels_raw
        ]

        # Orphans = registered defs whose key never appears on any atom.
        defined_attr_keys = {a.key for a in attr_rows}
        defined_rel_keys = {r.key for r in rel_rows}
        orphan_attrs = sorted(defined_attr_keys - used_attr_keys)
        orphan_rels = sorted(defined_rel_keys - used_rel_keys)

        return RegistryView(
            atoms=atom_rows,
            attributes=attr_rows,
            relations=rel_rows,
            total_atoms=len(atom_rows),
            total_attrs=len(attr_rows),
            total_rels=len(rel_rows),
            orphan_attrs=orphan_attrs,
            orphan_rels=orphan_rels,
        )
