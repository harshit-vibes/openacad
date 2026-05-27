"""Scorer agent — assigns confidence + duplicate-risk to a draft atom and
returns short structured feedback to the scholar.

Invoked by the curation queue when the scenario has both `has_curation=True`
and `has_meta_eval=True` — today that's only Self-Improving Assistant
(`evolving-notes`). For Curated Notes, the deterministic scorer in
`tools/atoms_extract.py::score()` handles confidence + duplicate_risk inline.
"""

from __future__ import annotations

from pydantic import BaseModel
from pydantic_ai import Agent

from openacad.runtime.llm import model_for, settings_for


class ScorerOutput(BaseModel):
    confidence: float
    duplicate_risk: float
    feedback: str


def _build_agent_with_prompt(body: str) -> Agent:
    return Agent(
        model_for("extraction"),
        system_prompt=body,
        output_type=ScorerOutput,
        retries=1,
        model_settings=settings_for("extraction"),
    )
