"""openacad demo — Streamlit walkthrough entrypoint.

Sidebar layout (top → bottom):
  • Brand block (title + tagline)
  • OVERVIEW: Welcome + Conclusion (Goodness is a tab on Conclusion)
  • THE 9-RUNG LADDER: 1 sequential link per scenario (no dropdown)
  • 🧰 WORKFLOWS: Ingest, Compose Artifact, Assess Artifact (all pinned to rung 9)
  • 🛠️ OPERATIONS: Notes & Registry, Curate, Evals & Prompt Hardening,
    Observability (all pinned to rung 9)

Per-scenario UX lives in `apps/streamlit/scenarios/<key>.py`, each of which is
a 3-line file that delegates to `apps/streamlit/scenario_view.render_scenario`.
The Workflows + Operations pages are *not* scenario-aware — they document the
production system (rung 9 / evolving-notes) and are hard-pinned via
`apps.streamlit.views.pin.pinned()`.
"""

from __future__ import annotations

import sys
from pathlib import Path

DEMO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(DEMO_ROOT) not in sys.path:
    sys.path.insert(0, str(DEMO_ROOT))
if str(DEMO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(DEMO_ROOT / "src"))

import streamlit as st


st.set_page_config(
    page_title="openacad — scholarly research AI agent harness",
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


# Workflows + Operations — each hard-pinned to evolving-notes (rung 9).
WORKFLOWS_PAGES = [
    st.Page("workflows/ingest.py",  title="📥 Ingest"),
    st.Page("workflows/compose.py", title="📜 Compose Artifact"),
    st.Page("workflows/assess.py",  title="🔍 Assess Artifact"),
]
OPERATIONS_PAGES = [
    st.Page("operations/notes_registry.py",        title="🧱 Notes & Registry"),
    st.Page("operations/curate.py",                title="✍️ Curate"),
    st.Page("operations/evals_prompt_hardening.py", title="⭐ Evals & Prompt Hardening"),
    st.Page("operations/observability.py",         title="📡 Observability"),
]


PAGES = [
    PAGE_WELCOME,
    *SCENARIO_PAGES,
    PAGE_CONCLUSION,
    *WORKFLOWS_PAGES,
    *OPERATIONS_PAGES,
]


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
        "⚛️ openacad</div>"
        "<div style='color:#888; font-size:0.85em; margin-bottom:0.8em;'>"
        "scholarly research AI agent harness</div>",
        unsafe_allow_html=True,
    )

    # OVERVIEW ─────────────────────────────────────────────────────────────
    _section_label("Overview")
    st.sidebar.page_link(PAGE_WELCOME, icon=PAGE_WELCOME.icon)
    st.sidebar.page_link(PAGE_CONCLUSION, icon=PAGE_CONCLUSION.icon)

    # THE 9-RUNG LADDER ───────────────────────────────────────────────────
    st.sidebar.markdown("---")
    _section_label("The 9-rung ladder")
    for page in SCENARIO_PAGES:
        st.sidebar.page_link(page)

    # WORKFLOWS ───────────────────────────────────────────────────────────
    st.sidebar.markdown("---")
    _section_label("Workflows")
    for page in WORKFLOWS_PAGES:
        st.sidebar.page_link(page)

    # OPERATIONS ──────────────────────────────────────────────────────────
    st.sidebar.markdown("---")
    _section_label("Operations")
    for page in OPERATIONS_PAGES:
        st.sidebar.page_link(page)


_render_sidebar()


def _sync_scenario_contextvar() -> None:
    """Push the session-state active scenario into the ContextVar that every
    scenario-aware service call reads. Scenario pages themselves overwrite this
    when they render; this default-set covers the global pages."""
    from openacad.runtime.scenario import SCENARIOS_BY_KEY, _active
    key = st.session_state.get("active_scenario_key", "cold-read")
    if key in SCENARIOS_BY_KEY:
        _active.set(key)


_sync_scenario_contextvar()

pg = st.navigation(PAGES, position="hidden")
pg.run()
