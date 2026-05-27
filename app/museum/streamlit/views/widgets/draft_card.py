"""Draft card — one expander showing a pending extractor draft."""

from __future__ import annotations

import streamlit as st

from openacad.projections._models import DraftRow


def render_draft_card(draft: DraftRow) -> None:
    """Render a single pending draft as a collapsible card."""
    ts = draft.drafted_at.strftime("%Y-%m-%d %H:%M:%S")
    label = f"📋 `{draft.draft_id}` · drafted {ts}"
    with st.expander(label, expanded=False):
        if draft.source_id:
            st.caption(f"source: `{draft.source_id}`")
        st.caption(f"prompt: `{draft.prompt_version}`")
        st.markdown("**Payload preview**")
        st.write(draft.payload_preview)
