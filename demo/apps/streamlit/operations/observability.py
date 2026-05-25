"""Observability — tool calls, latency, cost rollup, activity feed, errors
(pinned to evolving-notes)."""

from __future__ import annotations

import sys
from pathlib import Path

DEMO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(DEMO_ROOT) not in sys.path:
    sys.path.insert(0, str(DEMO_ROOT))
if str(DEMO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(DEMO_ROOT / "src"))

import streamlit as st

from apps.streamlit.views.pin import pinned
from apps.streamlit.views.widgets import (
    KPI,
    render_activity_feed,
    render_cost_rollup,
    render_error_log,
    render_kpi_row,
    render_latency_histogram,
    render_pinned_header,
    render_tool_call_table,
)
from openacad.projections import observability_rollup


def render() -> None:
    with pinned():
        render_pinned_header(
            "Observability",
            "Tool calls, latency, cost rollup, activity feed, errors.",
            "📡",
        )

        view = observability_rollup()

        kpis = [
            KPI(label="⚙️ tool calls", value=f"{view.n_tool_calls:,}"),
            KPI(label="⚡ avg latency", value=f"{int(view.avg_latency_ms)}ms"),
            KPI(label="💵 total cost", value=f"${view.total_cost_usd:.4f}"),
            KPI(label="🚨 errors", value=f"{view.n_errors:,}"),
        ]
        render_kpi_row(kpis)

        st.divider()
        st.subheader("🕐 Latency histogram")
        render_latency_histogram(view.latency_histogram)

        st.divider()
        st.subheader("💵 Cost rollup")
        tab_role, tab_day = st.tabs(["By role", "By day"])
        with tab_role:
            render_cost_rollup(view.cost_by_role, "role")
        with tab_day:
            render_cost_rollup(view.cost_by_day, "day")

        st.divider()
        st.subheader("⚙️ Tool calls")
        render_tool_call_table(view.tool_calls)

        st.divider()
        st.subheader("📡 Activity feed")
        render_activity_feed(view.activity_feed)

        if view.errors:
            st.divider()
            st.subheader("⚠️ Errors")
            render_error_log(view.errors)


render()
