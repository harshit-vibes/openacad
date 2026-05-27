"""Compose Artifact — produce a paper / chapter / briefing from the notes vault.

Hard-pinned to scenario 9 (`evolving-notes`). The Self-Improving Assistant's
answerer drafts each section. Outputs are saved as Artifact entities and
logged to the feedback timeline; artifact history below is filtered to runs
on this pinned scenario.
"""

from __future__ import annotations

import sys
from pathlib import Path

DEMO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(DEMO_ROOT) not in sys.path:
    sys.path.insert(0, str(DEMO_ROOT))
if str(DEMO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(DEMO_ROOT / "src"))

import streamlit as st

from museum.streamlit.views.pin import pinned
from museum.streamlit.views.widgets import (
    KPI,
    render_kpi_row,
    render_pinned_header,
)
from openacad.artifacts.composition.orchestrator import compose
from openacad.feedback.timeline import list_events
from openacad.projections import evals_summary
from openacad.runtime import db as db_module


PRESETS = {
    "Research paper on SDG 1 (poverty)": dict(
        kind="paper",
        title="Strategies for Ending Poverty — Insights from the SDG Briefing",
        sections=[
            "Abstract",
            "Introduction: framing of SDG 1",
            "Key strategies identified",
            "Empirical evidence and indicators",
            "Open questions and gaps",
            "Conclusion",
        ],
        brief="Draw on every relevant atom in the vault. Cite atoms inline.",
    ),
    "Briefing on SDG 5 (gender equality)": dict(
        kind="briefing",
        title="Gender Equality — A One-Page Briefing",
        sections=[
            "What SDG 5 targets",
            "Where we stand (key indicators)",
            "What's working",
            "What's blocking progress",
        ],
        brief="Be concise; one paragraph per section.",
    ),
    "Book chapter outline on SDGs 6-10": dict(
        kind="chapter",
        title="From Clean Water to Inequality — SDGs 6-10",
        sections=[
            "Chapter introduction",
            "Clean Water and Sanitation (SDG 6)",
            "Affordable and Clean Energy (SDG 7)",
            "Decent Work and Economic Growth (SDG 8)",
            "Industry, Innovation, and Infrastructure (SDG 9)",
            "Reduced Inequalities (SDG 10)",
            "Cross-cutting themes",
        ],
        brief="Treat each goal as a sub-section; conclude with cross-cutting reflections.",
    ),
}


def _kpi_row_for_compose() -> list[KPI]:
    """KPI row from the evals projection for the evolving-notes scenario."""
    view = evals_summary()
    runs = view.comparison_runs
    n_runs = len(runs)
    total_tokens = sum(r.tokens_in + r.tokens_out for r in runs)
    avg_latency = (sum(r.latency_ms for r in runs) / n_runs) if n_runs else 0.0
    # gpt-4o-mini pricing: $0.15/M in, $0.60/M out
    total_cost = sum(
        r.tokens_in * 0.15e-6 + r.tokens_out * 0.60e-6 for r in runs
    )
    return [
        KPI(label="⚖️ comparison runs", value=f"{n_runs:,}"),
        KPI(label="🔤 total tokens", value=f"{total_tokens:,}"),
        KPI(label="💵 total cost", value=f"${total_cost:.4f}"),
        KPI(label="⚡ avg latency", value=f"{int(avg_latency)}ms"),
    ]


def _render_artifact_history() -> None:
    """Compose history — `artifact_composed` events in the pinned scenario."""
    events = list_events(scenario_key="evolving-notes", kind="artifact_composed", limit=20)
    if not events:
        st.caption(
            "No artifacts composed in the evolving-notes vault yet. "
            "Use the form above to draft one."
        )
        return
    rows = []
    for ev in events:
        payload = ev.get("payload") or {}
        ts = ev["timestamp"]
        rows.append({
            "when": ts.strftime("%Y-%m-%d %H:%M"),
            "title": payload.get("title", "—"),
            "kind": payload.get("kind", "—"),
            "sections": payload.get("section_count", "—"),
            "citations": payload.get("citation_count", "—"),
            "id": payload.get("artifact_id", "—"),
        })
    st.dataframe(rows, use_container_width=True, hide_index=True)


def render() -> None:
    with pinned() as s:
        render_pinned_header(
            "Compose Artifact",
            "Draft a paper, chapter, or briefing from the evolving-notes vault.",
            "📜",
        )

        render_kpi_row(_kpi_row_for_compose())

        sources = db_module.list_sources()
        if not sources:
            st.info(
                "No PDFs in the vault — composition can still run but synthesis "
                "quality is bounded by what's been ingested."
            )

        st.divider()
        st.subheader("Pick a preset (or customize)")
        preset_name = st.selectbox(
            "Preset",
            options=list(PRESETS.keys()) + ["✏️ Custom…"],
        )
        if preset_name == "✏️ Custom…":
            kind = st.selectbox(
                "Artifact kind",
                options=["paper", "chapter", "review", "briefing", "slides"],
            )
            title = st.text_input("Title")
            sections_str = st.text_area(
                "Section titles (one per line)",
                placeholder="Section 1\nSection 2\n…",
                height=140,
            )
            brief = st.text_area("Brief / instructions for the answerer", height=80)
            sections = [s.strip() for s in sections_str.splitlines() if s.strip()]
        else:
            preset = PRESETS[preset_name]
            kind = preset["kind"]
            title = preset["title"]
            sections = preset["sections"]
            brief = preset["brief"]
            with st.expander(f"Preset details — {kind.upper()}"):
                st.markdown(f"**Title:** {title}")
                st.markdown("**Sections:**")
                for sec in sections:
                    st.markdown(f"- {sec}")
                st.markdown(f"**Brief:** _{brief}_")

        paper_pick = st.multiselect(
            "Source PDFs to restrict retrieval to (optional)",
            options=[src.id for src in sources],
            default=[],
            format_func=lambda sid: next(src.filename for src in sources if src.id == sid),
        )

        st.divider()
        if st.button("✨ Compose artifact", type="primary", use_container_width=True):
            if not title or not sections:
                st.error("Title and at least one section are required.")
            else:
                with st.spinner(f"Drafting {len(sections)} section(s) with {s.name}…"):
                    try:
                        artifact = compose(
                            kind=kind,
                            title=title,
                            sections=sections,
                            paper_ids=paper_pick,
                            brief=brief,
                        )
                        st.session_state["composed_artifact"] = artifact.model_dump(mode="json")
                    except Exception as e:
                        st.error(f"Composition failed: {e}")

        if "composed_artifact" in st.session_state:
            art = st.session_state["composed_artifact"]
            st.divider()
            st.subheader(f"📜 {art['title']}")
            st.caption(
                f"`{art['id']}` · kind: **{art['kind']}** · "
                f"{len(art['sections'])} sections · "
                f"{len(art['note_citations'])} unique citations"
            )
            for sec in art["sections"]:
                st.markdown(f"### {sec['title']}")
                st.write(sec["body"])
                if sec["note_citations"]:
                    st.caption(
                        "cited: "
                        + ", ".join(f"`{c}`" for c in sec["note_citations"][:8])
                        + (
                            f" +{len(sec['note_citations']) - 8} more"
                            if len(sec["note_citations"]) > 8
                            else ""
                        )
                    )

            with st.expander("📋 Full citation list"):
                for c in art["note_citations"]:
                    st.markdown(f"- `{c}`")

        st.divider()
        st.subheader("📜 Compose history (evolving-notes only)")
        _render_artifact_history()


render()
