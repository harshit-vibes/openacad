"""Schema viewer — render the attribute + relation registry tables.

Orphans (usage_count == 0) are flagged with a ⚠️ in the relevant column so
the operator can spot them at a glance.
"""

from __future__ import annotations

import streamlit as st

from openacad.projections._models import AttributeDef, RelationDef


def render_attribute_schema(attrs: list[AttributeDef]) -> None:
    """Render the attribute registry. Orphans get a ⚠️ usage prefix."""
    if not attrs:
        st.info("No attribute defs registered yet.")
        return

    n_orphans = sum(1 for a in attrs if a.usage_count == 0)
    if n_orphans:
        st.warning(
            f"⚠️ {n_orphans} orphan attribute"
            f"{'s' if n_orphans != 1 else ''} (registered but never used)."
        )

    data = [
        {
            "key": a.key,
            "type": a.value_type,
            "allowed": ", ".join(a.allowed_values) if a.allowed_values else "—",
            "usage": ("⚠️ 0" if a.usage_count == 0 else str(a.usage_count)),
            "first seen": (
                a.first_seen.strftime("%Y-%m-%d") if a.first_seen else "—"
            ),
        }
        for a in attrs
    ]
    st.dataframe(data, use_container_width=True, hide_index=True)


def render_relation_schema(rels: list[RelationDef]) -> None:
    """Render the relation registry. Rows with no inverse get a ⚠️ flag."""
    if not rels:
        st.info("No relation defs registered yet.")
        return

    n_no_inverse = sum(1 for r in rels if not r.inverse)
    n_orphans = sum(1 for r in rels if r.usage_count == 0)
    if n_no_inverse:
        st.warning(
            f"⚠️ {n_no_inverse} relation"
            f"{'s' if n_no_inverse != 1 else ''} missing an inverse "
            "(graph traversal can't go backward)."
        )
    if n_orphans:
        st.info(
            f"{n_orphans} orphan relation"
            f"{'s' if n_orphans != 1 else ''} (registered but never used)."
        )

    data = [
        {
            "key": r.key,
            "source → target": (
                f"{','.join(r.source_types) or '*'} → "
                f"{','.join(r.target_types) or '*'}"
            ),
            "inverse": ("⚠️ —" if not r.inverse else r.inverse),
            "usage": ("⚠️ 0" if r.usage_count == 0 else str(r.usage_count)),
        }
        for r in rels
    ]
    st.dataframe(data, use_container_width=True, hide_index=True)
