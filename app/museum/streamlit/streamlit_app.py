"""openacad — frozen 9-rung capability ladder demo (the thesis museum).

This Streamlit app is the original product demonstration that motivated the
new openacad product (`openacad/` Python package + Next.js UI). It walks
through 9 increasing tiers of AI agent capability — from cold-read PDF dump
to a self-improving meta-evaluator loop — and shows why rung 9 is the right
configuration.

This museum is **frozen at git tag `thesis-v1`** and is no longer maintained.
To explore the current product, use the `openacad` CLI or `openacad ui`.

Sidebar layout:
  • OVERVIEW: Welcome + Conclusion (Goodness as a tab)
  • THE 9-RUNG LADDER: 1 sequential link per scenario
"""

from __future__ import annotations

import sys
from pathlib import Path

DEMO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(DEMO_ROOT) not in sys.path:
    sys.path.insert(0, str(DEMO_ROOT))

import streamlit as st


st.set_page_config(
    page_title="openacad — thesis museum (frozen)",
    page_icon="⚛️",
    layout="wide",
    initial_sidebar_state="expanded",
)


if "active_scenario_key" not in st.session_state:
    st.session_state["active_scenario_key"] = "cold-read"


# ── pages ────────────────────────────────────────────────────────────────


PAGE_WELCOME = st.Page("walkthrough/00_welcome.py", title="Welcome", icon="🏠", default=True)
PAGE_CONCLUSION = st.Page("walkthrough/90_conclusion.py", title="Conclusion", icon="🎓")


# 9 scenario pages — one per rung.
SCENARIO_PAGE_DEFS = [
    ("cold-read",         "scenarios/cold_read.py",         "Cold Read",                "🥶"),
    ("keyword-snippets",  "scenarios/keyword_snippets.py",  "Keyword Snippets",         "🧩"),
    ("semantic-snippets", "scenarios/semantic_snippets.py", "Semantic Snippets",        "🧩"),
    ("atoms-only",        "scenarios/atoms_only.py",        "Atomic Chunks",            "⚛️"),
    ("atoms-attrs",       "scenarios/atoms_attrs.py",       "+ Attributes",             "⚛️"),
    ("atoms-attrs-rels",  "scenarios/atoms_attrs_rels.py",  "+ Relations",              "⚛️"),
    ("drafted-notes",     "scenarios/drafted_notes.py",     "+ Atom Embeddings",        "⚛️"),
    ("curated-notes",     "scenarios/curated_notes.py",     "+ HITL Curation",          "⚛️"),
    ("evolving-notes",    "scenarios/evolving_notes.py",    "Self-Improving Assistant", "⚛️"),
]


SCENARIO_PAGES = [
    st.Page(path, title=f"{i+1}. {emoji} {title}")
    for i, (key, path, title, emoji) in enumerate(SCENARIO_PAGE_DEFS)
]


PAGES = [PAGE_WELCOME, *SCENARIO_PAGES, PAGE_CONCLUSION]


# ── sidebar layout ──────────────────────────────────────────────────────


def _section_label(label: str) -> None:
    st.sidebar.markdown(
        f"<div style='color:#888; font-size:0.75em; "
        f"text-transform:uppercase; letter-spacing:0.05em; "
        f"margin-top:0.6em;'>{label}</div>",
        unsafe_allow_html=True,
    )


def _render_sidebar() -> None:
    # Brand
    st.sidebar.markdown(
        "<div style='font-size:1.5em; font-weight:700; line-height:1.1;'>"
        "⚛️ openacad <span style='font-size:0.6em; color:#888;'>museum</span></div>"
        "<div style='color:#888; font-size:0.85em; margin-bottom:0.8em;'>"
        "9-rung capability ladder — frozen at thesis-v1</div>",
        unsafe_allow_html=True,
    )

    _section_label("Overview")
    st.sidebar.page_link(PAGE_WELCOME, icon=PAGE_WELCOME.icon)
    st.sidebar.page_link(PAGE_CONCLUSION, icon=PAGE_CONCLUSION.icon)

    st.sidebar.markdown("---")
    _section_label("The 9-rung ladder")
    for page in SCENARIO_PAGES:
        st.sidebar.page_link(page)


_render_sidebar()


def _sync_scenario_contextvar() -> None:
    """Push the session-state active scenario into the ContextVar that every
    scenario-aware service call reads."""
    from openacad.runtime.scenario import SCENARIOS_BY_KEY, _active
    key = st.session_state.get("active_scenario_key", "cold-read")
    if key in SCENARIOS_BY_KEY:
        _active.set(key)


_sync_scenario_contextvar()

pg = st.navigation(PAGES, position="hidden")
pg.run()
