"""Read-only projections for the Ops Console.

Each top-level function returns a single Pydantic DTO defined in `_models`.
Every function takes `scenario_key: str = "evolving-notes"` and wraps its
domain reads in `with use_scenario(scenario_key):` so the projection is
self-contained.

Public API (consumed by `apps/streamlit/views/` widgets):
"""

from openacad.projections.curation import curation_summary
from openacad.projections.evals import evals_summary
from openacad.projections.ingest import paper_library
from openacad.projections.observability import observability_rollup
from openacad.projections.registry import registry_view

__all__ = [
    "curation_summary",
    "evals_summary",
    "observability_rollup",
    "paper_library",
    "registry_view",
]
