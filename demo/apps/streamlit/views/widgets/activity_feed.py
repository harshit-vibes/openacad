"""Activity feed — chronological vertical list of system events."""

from __future__ import annotations

import streamlit as st

from openacad.projections._models import ActivityFeedItem

# Map kind → emoji icon. Kinds not listed get the generic dot.
_KIND_ICONS: dict[str, str] = {
    "tool_call": "⚙️",
    "accept": "✅",
    "reject": "❌",
    "edit": "✏️",
    "deprecate": "🗑️",
    "verdict": "✋",
    "prompt_promote": "🧬",
    "prompt_propose": "💡",
    "rubric": "⭐",
    "comparison": "⚖️",
    "ingest": "📥",
}


def _icon_for(kind: str) -> str:
    return _KIND_ICONS.get(kind, "•")


def render_activity_feed(items: list[ActivityFeedItem]) -> None:
    """Render a vertical chronological feed. Empty input shows an info message."""
    if not items:
        st.info("No activity recorded yet.")
        return

    for item in items:
        ts = item.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        icon = _icon_for(item.kind)
        st.markdown(
            f"`{ts}` {icon} **{item.actor}** &nbsp; {item.summary}",
            unsafe_allow_html=True,
        )
