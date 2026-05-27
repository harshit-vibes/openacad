"""Curate — pending extractor drafts + scholar verdict history (pinned)."""

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
    render_draft_card,
    render_kpi_row,
    render_pinned_header,
    render_verdict_table,
)
from openacad.projections import curation_summary


def render() -> None:
    with pinned():
        render_pinned_header(
            "Curate",
            "Pending extractor drafts and the scholar verdict history.",
            "✍️",
        )

        view = curation_summary()
        counts = view.counts or {}

        kpis = [
            KPI(label="⏳ pending", value=str(counts.get("pending", 0))),
            KPI(label="✅ accept", value=str(counts.get("accept", 0))),
            KPI(label="✏️ edit", value=str(counts.get("edit", 0))),
            KPI(label="❌ reject", value=str(counts.get("reject", 0))),
        ]
        render_kpi_row(kpis)

        st.divider()
        st.subheader("📋 Pending drafts")
        if not view.pending_drafts:
            st.info("No pending drafts.")
        else:
            for draft in view.pending_drafts:
                render_draft_card(draft)

        st.divider()
        st.subheader("📜 Verdict history")
        if not view.verdict_history:
            st.info("No verdicts recorded yet.")
        else:
            render_verdict_table(view.verdict_history)


render()
