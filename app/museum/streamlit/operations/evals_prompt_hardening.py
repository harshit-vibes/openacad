"""Evals & Prompt Hardening — comparison runs, rubric scores, prompt
timelines, and meta-evaluator proposals (pinned)."""

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
    render_prompt_timelines,
)
from openacad.projections import evals_summary


def _render_comparison_runs(runs) -> None:
    if not runs:
        st.info("No comparison runs recorded yet.")
        return
    rows = [
        {
            "question": (r.question or "")[:80],
            "tokens_in": r.tokens_in,
            "tokens_out": r.tokens_out,
            "latency_ms": r.latency_ms,
            "citations": r.citations,
            "run_at": r.run_at.strftime("%Y-%m-%d %H:%M:%S"),
            "id": r.id,
        }
        for r in runs
    ]
    st.dataframe(rows, use_container_width=True, hide_index=True)
    st.divider()
    st.markdown("##### Answers (preview)")
    for r in runs[:25]:
        with st.expander(f"`{r.id}` — {(r.question or '')[:80]}"):
            st.caption(
                f"{r.tokens_in:,} in · {r.tokens_out:,} out · "
                f"{r.latency_ms}ms · {r.citations} citation(s) · "
                f"{r.run_at.strftime('%Y-%m-%d %H:%M:%S')}"
            )
            st.write(r.answer_preview or "_(no answer preview)_")


def _render_rubric_scores(rubrics, avg_by_criterion) -> None:
    if not rubrics:
        st.info("No rubric submissions yet.")
        return
    if avg_by_criterion:
        st.markdown("##### Average score by criterion")
        st.bar_chart(avg_by_criterion, height=240)
    rows = [
        {
            "role": r.role,
            "criteria": ", ".join(f"{k}={v:.2f}" for k, v in (r.criteria or {}).items()),
            "notes": (r.notes or "")[:120],
            "when": r.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "id": r.id,
        }
        for r in rubrics
    ]
    st.dataframe(rows, use_container_width=True, hide_index=True)


def _render_meta_proposals(proposals) -> None:
    if not proposals:
        st.info("No meta-eval proposals yet.")
        return
    rows = [
        {
            "when": p.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "target_role": p.target_role,
            "insight_kind": p.insight_kind,
            "state": p.state,
            "proposed_change": (p.proposed_change_preview or "")[:160],
            "event_id": p.event_id,
        }
        for p in proposals
    ]
    st.dataframe(rows, use_container_width=True, hide_index=True)


def render() -> None:
    with pinned():
        render_pinned_header(
            "Evals & Prompt Hardening",
            "Comparison runs, rubric scores, prompt versions, and meta-evaluator proposals.",
            "⭐",
        )

        view = evals_summary()

        n_prompt_versions = sum(len(t.versions) for t in view.prompt_timelines)
        kpis = [
            KPI(label="⚖️ comparison runs", value=f"{len(view.comparison_runs):,}"),
            KPI(label="⭐ rubric submissions", value=f"{len(view.rubric_scores):,}"),
            KPI(label="🧬 prompt versions", value=f"{n_prompt_versions:,}"),
            KPI(label="💡 meta-eval proposals", value=f"{len(view.meta_proposals):,}"),
        ]
        render_kpi_row(kpis)

        st.divider()
        tab_runs, tab_rubrics, tab_prompts, tab_proposals = st.tabs(
            [
                "⚖️ Comparison Runs",
                "⭐ Rubric Scores",
                "🧬 Prompt Versions",
                "💡 Meta-Eval Proposals",
            ]
        )

        with tab_runs:
            _render_comparison_runs(view.comparison_runs)

        with tab_rubrics:
            _render_rubric_scores(view.rubric_scores, view.rubric_avg_by_criterion)

        with tab_prompts:
            render_prompt_timelines(view.prompt_timelines)

        with tab_proposals:
            _render_meta_proposals(view.meta_proposals)


render()
