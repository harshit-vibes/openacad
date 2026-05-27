"""Ingest — papers in the vault and the chunks → atoms pipeline."""

from __future__ import annotations

import sys
from pathlib import Path

DEMO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(DEMO_ROOT) not in sys.path:
    sys.path.insert(0, str(DEMO_ROOT))
if str(DEMO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(DEMO_ROOT / "src"))

import streamlit as st

from museum.streamlit.views.pin import pinned
from museum.streamlit.views.widgets import (
    KPI,
    render_kpi_row,
    render_paper_card,
    render_pinned_header,
)
from openacad.projections import paper_library


def _fmt_when(dt) -> str:
    if dt is None:
        return "—"
    return dt.strftime("%Y-%m-%d")


def render() -> None:
    with pinned():
        render_pinned_header(
            "Ingest",
            "Papers in the vault — chunks → atoms pipeline.",
            "📥",
        )

        # Pipeline strip — static explainer of the ingestion path.
        with st.container(border=True):
            st.markdown(
                "**🧪 Pipeline:** "
                "📄 PDF "
                "&nbsp;→&nbsp; ✂️ chunks (sentence-window) "
                "&nbsp;→&nbsp; ⚛️ atoms (Extractor agent) "
                "&nbsp;→&nbsp; 🧱 registry (attribute + relation defs)",
                unsafe_allow_html=True,
            )
            st.caption(
                "Each PDF is split into overlapping chunks, then the Extractor "
                "drafts atoms per chunk. Accepted atoms land in the vault; their "
                "attributes/relations extend the registry."
            )

        view = paper_library()

        # KPI row.
        kpis = [
            KPI(label="📄 papers", value=f"{view.total_papers:,}"),
            KPI(label="📑 chunks", value=f"{view.total_chunks:,}"),
            KPI(label="⚛️ atoms", value=f"{view.total_atoms:,}"),
            KPI(
                label="📥 last ingest",
                value=_fmt_when(view.last_ingested_at),
                help=(
                    view.last_ingested_at.strftime("%Y-%m-%d %H:%M:%S")
                    if view.last_ingested_at
                    else None
                ),
            ),
        ]
        render_kpi_row(kpis)

        st.divider()
        st.subheader("📚 Paper library")

        if not view.papers:
            st.info(
                "No PDFs ingested into the evolving-notes vault yet. "
                "Use the CLI or seed scripts to populate."
            )
            return

        for paper in view.papers:
            render_paper_card(paper)


render()
