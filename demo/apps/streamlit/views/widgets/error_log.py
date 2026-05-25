"""Error log — only shows ToolCallRows whose error_message is set.

Visually distinct from the main tool_call_table: highlighted heading + full
error text instead of a truncated preview, so debugging is easier.
"""

from __future__ import annotations

import streamlit as st

from openacad.projections._models import ToolCallRow


def render_error_log(rows: list[ToolCallRow]) -> None:
    """Render error-bearing tool calls. No-op if `rows` is empty."""
    if not rows:
        return

    st.markdown(f"#### 🚨 Errors ({len(rows)})")
    for r in rows:
        with st.container(border=True):
            head_cols = st.columns([2, 2, 1, 2])
            head_cols[0].markdown(f"**`{r.tool_name}`**")
            head_cols[1].caption(f"agent: {r.agent}")
            head_cols[2].caption(f"{r.latency_ms}ms")
            head_cols[3].caption(r.timestamp.strftime("%Y-%m-%d %H:%M:%S"))
            st.error(r.error_message or "(no error message recorded)")
            if r.arguments:
                with st.expander("arguments", expanded=False):
                    st.json(r.arguments)
