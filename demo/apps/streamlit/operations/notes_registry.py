"""Notes & Registry — atoms, attribute schema, and relation schema (pinned)."""

from __future__ import annotations

import sys
from pathlib import Path

DEMO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(DEMO_ROOT) not in sys.path:
    sys.path.insert(0, str(DEMO_ROOT))
if str(DEMO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(DEMO_ROOT / "src"))

import streamlit as st

from apps.streamlit.views.pin import pinned
from apps.streamlit.views.widgets import (
    KPI,
    render_atom_table,
    render_attribute_schema,
    render_kpi_row,
    render_pinned_header,
    render_relation_schema,
)
from openacad.projections import registry_view


def render() -> None:
    with pinned():
        render_pinned_header(
            "Notes & Registry",
            "Atoms, attribute schema, relation schema.",
            "🧱",
        )

        view = registry_view()

        kpis = [
            KPI(label="⚛️ total atoms", value=f"{view.total_atoms:,}"),
            KPI(label="🏷️ attributes", value=f"{view.total_attrs:,}"),
            KPI(label="🕸️ relations", value=f"{view.total_rels:,}"),
        ]
        render_kpi_row(kpis)

        st.divider()
        tab_atoms, tab_attrs, tab_rels = st.tabs(
            ["⚛️ Atoms", "🏷️ Attributes", "🕸️ Relations"]
        )

        with tab_atoms:
            render_atom_table(view.atoms, page_key="notes_registry")

        with tab_attrs:
            render_attribute_schema(view.attributes)
            if view.orphan_attrs:
                st.warning(
                    f"⚠️ {len(view.orphan_attrs)} orphan attribute(s) "
                    f"(registered but never used): "
                    + ", ".join(f"`{k}`" for k in view.orphan_attrs[:20])
                    + (
                        f" (+{len(view.orphan_attrs) - 20} more)"
                        if len(view.orphan_attrs) > 20
                        else ""
                    )
                )

        with tab_rels:
            render_relation_schema(view.relations)
            if view.orphan_rels:
                st.warning(
                    f"⚠️ {len(view.orphan_rels)} orphan relation(s) "
                    f"(registered but never used): "
                    + ", ".join(f"`{k}`" for k in view.orphan_rels[:20])
                    + (
                        f" (+{len(view.orphan_rels) - 20} more)"
                        if len(view.orphan_rels) > 20
                        else ""
                    )
                )


render()
