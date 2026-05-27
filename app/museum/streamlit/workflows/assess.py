"""Assess Artifact — coverage analysis vs. the evolving-notes vault.

Hard-pinned to scenario 9. Given an external artifact, the Assessor splits it
into passages, scores each passage against the vault's atom embeddings, and
flags which atoms support the artifact vs. which it never approached.
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
from openacad.artifacts.assessment.coverage import assess_coverage
from openacad.feedback.timeline import list_events
from openacad.notes.persistence import vault as vault_io
from openacad.projections import evals_summary


def _kpi_row_for_assess(n_atoms: int) -> list[KPI]:
    view = evals_summary()
    runs = view.comparison_runs
    n_runs = len(runs)
    total_tokens = sum(r.tokens_in + r.tokens_out for r in runs)
    avg_latency = (sum(r.latency_ms for r in runs) / n_runs) if n_runs else 0.0
    total_cost = sum(
        r.tokens_in * 0.15e-6 + r.tokens_out * 0.60e-6 for r in runs
    )
    return [
        KPI(label="⚛️ vault atoms", value=f"{n_atoms:,}"),
        KPI(label="🔤 total tokens", value=f"{total_tokens:,}"),
        KPI(label="💵 total cost", value=f"${total_cost:.4f}"),
        KPI(label="⚡ avg latency", value=f"{int(avg_latency)}ms"),
    ]


def _render_assess_history() -> None:
    events = list_events(scenario_key="evolving-notes", kind="artifact_assessed", limit=20)
    if not events:
        st.caption(
            "No artifacts assessed against the evolving-notes vault yet. "
            "Use the form above to score one."
        )
        return
    rows = []
    for ev in events:
        payload = ev.get("payload") or {}
        ts = ev["timestamp"]
        rows.append({
            "when": ts.strftime("%Y-%m-%d %H:%M"),
            "kind": payload.get("kind", "—"),
            "referenced": payload.get("referenced_count", "—"),
            "coverage": payload.get("coverage_ratio", "—"),
            "assessment": payload.get("assessment_id", "—"),
        })
    st.dataframe(rows, use_container_width=True, hide_index=True)


def render() -> None:
    with pinned():
        render_pinned_header(
            "Assess Artifact",
            "Score an external artifact against the evolving-notes vault — "
            "which atoms it covers and which it missed.",
            "🔍",
        )

        atoms = vault_io.list_atoms()
        render_kpi_row(_kpi_row_for_assess(len(atoms)))

        if not atoms:
            st.warning(
                "The evolving-notes vault is empty — assessment against nothing isn't "
                "meaningful. Ingest + curate atoms first."
            )
            return

        st.divider()
        tab_paste, tab_upload = st.tabs(["📝 Paste text", "📤 Upload .txt/.md"])
        artifact_text = ""

        with tab_paste:
            artifact_text = st.text_area(
                "External artifact text",
                height=300,
                placeholder="Paste a paper abstract + intro + conclusion, or a draft you want assessed…",
            )

        with tab_upload:
            uploaded = st.file_uploader("Plain text artifact (.txt or .md)", type=["txt", "md"])
            if uploaded is not None:
                artifact_text = uploaded.read().decode("utf-8", errors="replace")
                st.caption(f"Loaded {len(artifact_text)} chars from {uploaded.name}")

        cols = st.columns([1, 1, 1])
        passage_size = cols[0].number_input(
            "Passage size (chars)",
            value=800,
            min_value=200,
            max_value=4000,
            step=100,
        )
        top_k = cols[1].number_input(
            "Top-K per passage", value=5, min_value=1, max_value=20
        )
        threshold = cols[2].slider(
            "Similarity threshold",
            min_value=0.0,
            max_value=1.0,
            value=0.45,
            step=0.05,
        )

        if st.button("🔍 Run coverage assessment", type="primary", use_container_width=True):
            if not artifact_text.strip():
                st.error("Provide artifact text first.")
            else:
                with st.spinner(
                    f"Embedding {len(artifact_text)} chars and searching {len(atoms)} atoms…"
                ):
                    try:
                        assessment = assess_coverage(
                            artifact_text=artifact_text,
                            passage_size=passage_size,
                            top_k_per_passage=top_k,
                            similarity_threshold=threshold,
                        )
                        st.session_state["assessment_result"] = assessment.model_dump(mode="json")
                    except Exception as e:
                        st.error(f"Assessment failed: {e}")

        if "assessment_result" in st.session_state:
            a = st.session_state["assessment_result"]
            st.divider()
            st.subheader(f"📊 Coverage Assessment `{a['id']}`")
            st.info(a["summary"])

            covered = a["supporting_notes"]
            missing = a["missing_topics"]

            c1, c2, c3 = st.columns(3)
            c1.metric("✅ Covered notes", len(covered))
            c2.metric("⚠️ Missing notes", len(missing))
            c3.metric("📍 Match findings", len(a["findings"]))

            if covered:
                with st.expander(
                    f"✅ {len(covered)} notes the artifact covers", expanded=True
                ):
                    for nid in covered[:30]:
                        st.markdown(f"- `{nid}`")
                    if len(covered) > 30:
                        st.caption(f"(showing 30 of {len(covered)})")

            if missing:
                with st.expander(
                    f"⚠️ {len(missing)} notes the artifact never approached"
                ):
                    for nid in missing[:30]:
                        atom = next((x for x in atoms if x.metas.id == nid), None)
                        if atom:
                            st.markdown(f"- `{nid}` — {atom.content[:80]}…")
                        else:
                            st.markdown(f"- `{nid}`")

            with st.expander(f"🔍 Raw findings ({len(a['findings'])} passage matches)"):
                st.dataframe(a["findings"][:200], use_container_width=True, hide_index=True)

        st.divider()
        st.subheader("📊 Assessment history (evolving-notes only)")
        _render_assess_history()


render()
