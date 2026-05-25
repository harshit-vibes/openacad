"""Verdict table — chronological record of scholar accept/edit/reject events."""

from __future__ import annotations

import json

import streamlit as st

from openacad.projections._models import VerdictRow

_KIND_BADGE: dict[str, str] = {
    "accept": "✅ accept",
    "edit": "✏️ edit",
    "reject": "❌ reject",
    "deprecate": "🗑️ deprecate",
}


def render_verdict_table(rows: list[VerdictRow]) -> None:
    """Render `rows` as a compact dataframe sorted newest-first by caller."""
    if not rows:
        st.info("No verdicts recorded yet.")
        return

    data = [
        {
            "time": r.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "kind": _KIND_BADGE.get(r.kind, r.kind),
            "actor": r.actor,
            "draft": r.draft_id or "—",
            "delta": (json.dumps(r.delta, default=str)[:80] if r.delta else ""),
        }
        for r in rows
    ]
    st.dataframe(data, use_container_width=True, hide_index=True)
