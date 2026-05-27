"""Pinned-page header — emoji icon, title, subtitle, and the 'pinned' pill."""

from __future__ import annotations

import streamlit as st


def render_pinned_header(title: str, subtitle: str, icon: str) -> None:
    """Render the standard header used by every Workflows / Operations page.

    Layout: a single h2 line `{icon} {title}`, a caption with `subtitle`,
    and a styled pill announcing the hard-pin to scenario 9.
    """
    st.markdown(f"## {icon} {title}")
    st.caption(subtitle)
    st.markdown(
        "<span style='display:inline-block;padding:2px 8px;border-radius:10px;"
        "background:#1e3a5f;color:#7fb3ff;font-size:0.75em;margin-top:4px;'>"
        "📌 pinned to scenario 9 · Self-Improving Assistant</span>",
        unsafe_allow_html=True,
    )
    st.write("")  # tiny spacer
