"""Latency histogram — render LatencyBucket[] as a bar chart."""

from __future__ import annotations

import streamlit as st

from openacad.projections._models import LatencyBucket


def render_latency_histogram(buckets: list[LatencyBucket]) -> None:
    """Bar chart of tool-call latencies, x = bucket upper bound, y = count.

    Empty input renders an info message rather than a blank chart.
    """
    if not buckets:
        st.info("No latency data yet — run a query to populate.")
        return
    data = {f"≤{b.upper_ms}ms": b.count for b in buckets}
    st.bar_chart(data)
