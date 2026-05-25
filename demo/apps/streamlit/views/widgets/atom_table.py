"""Atom table — paginated table over AtomRow[].

Pagination state lives in `st.session_state[f"atom_page_{page_key}"]`. Pages
that render two atom tables side by side should pass a distinct `page_key`
to keep their offsets independent.
"""

from __future__ import annotations

import streamlit as st

from openacad.projections._models import AtomRow

_PAGE_SIZE = 25


def render_atom_table(rows: list[AtomRow], page_key: str = "default") -> None:
    """Render a paginated atom table with prev/next controls.

    `page_key` namespaces the pagination state so multiple atom tables on the
    same page don't share a cursor.
    """
    if not rows:
        st.info("No atoms in the vault yet.")
        return

    state_key = f"atom_page_{page_key}"
    offset = st.session_state.get(state_key, 0)
    # Defensive: if rows shrank between renders, snap back into range.
    if offset >= len(rows):
        offset = 0
        st.session_state[state_key] = 0

    page = rows[offset : offset + _PAGE_SIZE]
    data = [
        {
            "id": r.atom_id,
            "kind": r.kind,
            "content": r.content_preview,
            "attrs": r.n_attrs,
            "rels": r.n_rels,
            "source": r.source_id or "—",
        }
        for r in page
    ]
    st.dataframe(data, use_container_width=True, hide_index=True)

    total = len(rows)
    last_shown = min(offset + _PAGE_SIZE, total)
    nav_cols = st.columns([1, 4, 1])
    prev_disabled = offset == 0
    next_disabled = last_shown >= total

    if nav_cols[0].button(
        "◀ prev", key=f"{state_key}_prev", disabled=prev_disabled, use_container_width=True
    ):
        st.session_state[state_key] = max(0, offset - _PAGE_SIZE)
        st.rerun()

    nav_cols[1].caption(
        f"showing {offset + 1}–{last_shown} of {total} atoms"
    )

    if nav_cols[2].button(
        "next ▶", key=f"{state_key}_next", disabled=next_disabled, use_container_width=True
    ):
        st.session_state[state_key] = offset + _PAGE_SIZE
        st.rerun()
