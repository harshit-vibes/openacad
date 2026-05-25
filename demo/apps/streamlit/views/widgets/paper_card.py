"""Paper card — expander showing PaperRow metadata + ingestion KPI tiles."""

from __future__ import annotations

import streamlit as st

from openacad.projections._models import PaperRow


def render_paper_card(paper: PaperRow) -> None:
    """Render one paper as an expander with title header + meta + KPI tiles."""
    title = paper.title or paper.source_id
    label = f"📄 **{title}** · `{paper.source_id}`"
    with st.expander(label, expanded=False):
        meta_cols = st.columns(3)
        authors = ", ".join(paper.authors) if paper.authors else "—"
        meta_cols[0].markdown(f"**authors:** {authors}")
        meta_cols[1].markdown(f"**year:** {paper.year if paper.year else '—'}")
        meta_cols[2].markdown(
            f"**pages:** {paper.pages if paper.pages is not None else '—'}"
        )

        kpi_cols = st.columns(3)
        kpi_cols[0].metric("📑 chunks", paper.chunks)
        kpi_cols[1].metric("⚛️ atoms", paper.atoms)
        kpi_cols[2].metric(
            "📥 ingested",
            paper.ingested_at.strftime("%Y-%m-%d"),
            help=paper.ingested_at.strftime("%Y-%m-%d %H:%M:%S"),
        )
