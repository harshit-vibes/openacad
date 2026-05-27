"""Tool call table — paginated dataframe of recent ToolCallRow entries."""

from __future__ import annotations

import streamlit as st

from openacad.projections._models import ToolCallRow


def render_tool_call_table(rows: list[ToolCallRow]) -> None:
    """Render `rows` as a compact dataframe; empty input shows an info message."""
    if not rows:
        st.info("No tool calls logged yet.")
        return

    data = [
        {
            "tool": r.tool_name,
            "agent": r.agent,
            "ms": r.latency_ms,
            "n": r.n_results,
            "time": r.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "error": (r.error_message[:80] if r.error_message else ""),
        }
        for r in rows
    ]
    st.dataframe(data, use_container_width=True, hide_index=True)
