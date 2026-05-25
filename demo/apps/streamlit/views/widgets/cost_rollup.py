"""Cost rollup — bar chart of CostRollupItem[] with a token-totals table below."""

from __future__ import annotations

import streamlit as st

from openacad.projections._models import CostRollupItem


def render_cost_rollup(items: list[CostRollupItem], group_label: str) -> None:
    """Render a cost-by-{group_label} bar chart + supporting token table.

    `group_label` is just a human label for the empty-state message
    ("role", "day", ...).
    """
    if not items:
        st.info(f"No cost data by {group_label} yet.")
        return

    chart_data = {item.bucket_label: item.cost_usd for item in items}
    st.bar_chart(chart_data, y_label="cost (USD)")

    rows = [
        {
            group_label: item.bucket_label,
            "tokens in": f"{item.tokens_in:,}",
            "tokens out": f"{item.tokens_out:,}",
            "cost (USD)": f"${item.cost_usd:.4f}",
        }
        for item in items
    ]
    st.dataframe(rows, use_container_width=True, hide_index=True)
