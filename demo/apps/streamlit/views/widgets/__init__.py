"""Pure-render Streamlit widgets for the Workflows / Operations pages.

All widgets take pydantic DTOs (from `openacad.projections._models`) and call
`st.*` — they do NOT touch the DB, scenario context, or projections directly.
"""

from __future__ import annotations

from .activity_feed import render_activity_feed
from .atom_table import render_atom_table
from .cost_rollup import render_cost_rollup
from .draft_card import render_draft_card
from .error_log import render_error_log
from .header import render_pinned_header
from .kpi_row import KPI, render_kpi_row
from .latency_hist import render_latency_histogram
from .paper_card import render_paper_card
from .prompt_history import render_prompt_timelines
from .schema_viewer import render_attribute_schema, render_relation_schema
from .tool_call_table import render_tool_call_table
from .verdict_table import render_verdict_table

__all__ = [
    "KPI",
    "render_activity_feed",
    "render_atom_table",
    "render_attribute_schema",
    "render_cost_rollup",
    "render_draft_card",
    "render_error_log",
    "render_kpi_row",
    "render_latency_histogram",
    "render_paper_card",
    "render_pinned_header",
    "render_prompt_timelines",
    "render_relation_schema",
    "render_tool_call_table",
    "render_verdict_table",
]
