"""Prompt history — per-role expander showing version timelines + bodies."""

from __future__ import annotations

import streamlit as st

from openacad.projections._models import PromptTimeline


def render_prompt_timelines(timelines: list[PromptTimeline]) -> None:
    """Render one expander per role; inside, a versions table + per-version body."""
    if not timelines:
        st.info("No prompt timelines yet.")
        return

    for tl in timelines:
        n = len(tl.versions)
        active = next(
            (v.version for v in tl.versions if getattr(v, "state", None) == "active"),
            "—",
        )
        label = f"🧬 **{tl.role}** — {n} version{'s' if n != 1 else ''} · active: `{active}`"
        with st.expander(label, expanded=False):
            if not tl.versions:
                st.caption("No prompt versions recorded for this role.")
                continue

            rows = [
                {
                    "version": v.version,
                    "state": getattr(v, "state", "—"),
                    "created": (
                        v.created_at.strftime("%Y-%m-%d %H:%M")
                        if getattr(v, "created_at", None)
                        else "—"
                    ),
                    "accept rate": (
                        f"{getattr(v, 'accept_rate', None):.2f}"
                        if getattr(v, "accept_rate", None) is not None
                        else "—"
                    ),
                }
                for v in tl.versions
            ]
            st.dataframe(rows, use_container_width=True, hide_index=True)

            picker_key = f"prompt-pick-{tl.role}"
            choice = st.selectbox(
                "Show body for version",
                options=[v.version for v in tl.versions],
                key=picker_key,
            )
            chosen = next((v for v in tl.versions if v.version == choice), None)
            if chosen is not None:
                body = getattr(chosen, "body", "") or ""
                st.code(body, language="markdown")
