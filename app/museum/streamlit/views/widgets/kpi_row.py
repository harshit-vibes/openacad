"""KPI row — a horizontal strip of `st.metric` tiles."""

from __future__ import annotations

import streamlit as st
from pydantic import BaseModel


class KPI(BaseModel):
    """A single KPI tile.

    `value` MUST be pre-formatted (e.g. "1,234", "$0.42", "12.3%"). The widget
    does not do number formatting — that's the caller's job, because units +
    precision are tile-specific.
    """

    label: str
    value: str
    help: str | None = None
    delta: str | None = None


def render_kpi_row(items: list[KPI]) -> None:
    """Render `items` as N equal-width metric tiles in a single row.

    Empty `items` renders nothing (no error). Single-item input still works.
    """
    if not items:
        return
    cols = st.columns(len(items))
    for col, item in zip(cols, items):
        col.metric(
            label=item.label,
            value=item.value,
            delta=item.delta,
            help=item.help,
        )
