"""Scenario type system + ContextVar that scopes every scenario-aware function
(db, vault_io, semantic_service, agents).

Scenario *instances* (the 6+ rungs of the openacad.runtime ladder) live in
`scenarios/definitions.py`. This module only defines the types and runtime
mechanism — keeping the type-vs-instance split clean lets new scenarios be added
without touching the openacad.runtime internals.

Scenarios are stored on disk as isolated vault directories under
`data/vaults/<key>/`.
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from enum import StrEnum
from pathlib import Path
from typing import Iterator

from pydantic import BaseModel

from openacad.runtime.settings import settings


class Tier(StrEnum):
    COLD = "cold"      # no memory — the LLM reads from scratch each time
    CHUNK = "chunk"    # chunk-level memory (vector or keyword retrieval)
    ATOMS = "atoms"    # atomic-note memory (extraction + curation + tool-calling agent)


class AgentRole(StrEnum):
    ANSWERER = "answerer"
    EXTRACTOR = "extractor"
    SCORER = "scorer"
    META_EVAL = "meta_evaluator"


class Step(BaseModel):
    """A walkthrough step shown in the sidebar for a given scenario."""
    page_path: str
    title: str
    icon: str


# Step catalog — each scenario picks a subset based on its capabilities.
STEP_LIBRARY = Step(page_path="walkthrough/10_papers.py", title="Your Library", icon="📚")
STEP_CURATE = Step(page_path="walkthrough/20_curate.py", title="Read & Take Notes", icon="📝")
STEP_INSPECT = Step(page_path="walkthrough/21_inspect.py", title="Your Notes Web", icon="🕸️")
STEP_ASK = Step(page_path="walkthrough/30_ask.py", title="Ask Your Library", icon="🔎")
STEP_AUDIT = Step(page_path="walkthrough/32_gold_test.py", title="Audit Quality", icon="🧪")
STEP_REFINE = Step(page_path="walkthrough/40_tune.py", title="Refine Your Assistant", icon="🎚️")

# Global pages outside the per-scenario walkthrough.
STEP_WELCOME = Step(page_path="walkthrough/00_welcome.py", title="Welcome", icon="🏠")
STEP_CONCLUSION = Step(page_path="walkthrough/90_conclusion.py", title="Conclusion", icon="🎓")


class Scenario(BaseModel):
    key: str
    name: str
    tier: Tier
    description: str
    agents: list[AgentRole]
    has_extraction: bool
    has_curation: bool
    has_meta_eval: bool
    # P2 capability flags — decouple what atom-tier scenarios bundle so each
    # rung of the ladder adds exactly one capability.
    has_attributes: bool = True       # extractor produces typed attributes
    has_relations: bool = True        # extractor produces typed relations between atoms
    has_atom_embeddings: bool = True  # MiniLM embeddings on accepted atoms (enables find_similar_atoms)
    rubric_criteria: dict[AgentRole, list[str]]

    @property
    def steps(self) -> list[Step]:
        """Walkthrough steps shown in the sidebar for this scenario."""
        if self.tier in (Tier.COLD, Tier.CHUNK):
            return [STEP_LIBRARY, STEP_ASK]
        # Atom-tier scenarios
        steps = [STEP_LIBRARY]
        if self.has_curation:
            steps.append(STEP_CURATE)
        steps.append(STEP_INSPECT)
        steps.append(STEP_ASK)
        steps.append(STEP_AUDIT)
        if self.has_meta_eval:
            steps.append(STEP_REFINE)
        return steps

    @property
    def vault_dir(self) -> Path:
        return settings.data_dir / "vaults" / self.key

    @property
    def state_db_path(self) -> Path:
        return self.vault_dir / "state.sqlite"

    @property
    def prompts_dir(self) -> Path:
        return self.vault_dir / "prompts"

    @property
    def notes_dir(self) -> Path:
        return self.vault_dir / "notes"

    @property
    def registry_dir(self) -> Path:
        return self.vault_dir / "registry"

    @property
    def atoms_npz_path(self) -> Path:
        return self.vault_dir / "embeddings" / "atoms.npz"

    @property
    def scoring_dir(self) -> Path:
        return self.vault_dir / "scoring"


# ── Scenario instances live in scenarios/definitions.py ─────────────────
#
# `harness/scenario.py` re-exports them for back-compat so the (many) consumers
# that import SCENARIOS / SCENARIOS_BY_KEY from `openacad.runtime.scenario` keep working.


def _load_scenarios() -> tuple[list[Scenario], dict[str, Scenario]]:
    # Lazy import to avoid a top-level cycle: openacad.scenarios._definitions_python imports
    # from this module to get the Scenario type.
    from openacad.scenarios._definitions_python import SCENARIOS, SCENARIOS_BY_KEY
    return SCENARIOS, SCENARIOS_BY_KEY


SCENARIOS, SCENARIOS_BY_KEY = _load_scenarios()


# ── ContextVar machinery ────────────────────────────────────────────────


# The default scenario is the legacy single-vault location ("curated-notes" gets
# the 7 seeded atoms in Step 1's migration). When no scenario is set, fall back
# to this so legacy code paths and ad-hoc scripts still work.
DEFAULT_SCENARIO_KEY = "curated-notes"

_active: ContextVar[str | None] = ContextVar("active_scenario", default=None)


def active_scenario() -> Scenario:
    """Return the currently-scoped Scenario, or the default if none is set."""
    key = _active.get() or DEFAULT_SCENARIO_KEY
    return SCENARIOS_BY_KEY[key]


def active_scenario_key() -> str:
    return _active.get() or DEFAULT_SCENARIO_KEY


@contextmanager
def use_scenario(key: str) -> Iterator[Scenario]:
    """Temporarily scope all scenario-aware service calls to the given scenario.

        with use_scenario("cold-read"):
            db.list_sources()  # operates against cold-read's state.sqlite
    """
    if key not in SCENARIOS_BY_KEY:
        raise ValueError(
            f"unknown scenario key: {key!r}. "
            f"valid: {sorted(SCENARIOS_BY_KEY)}"
        )
    token = _active.set(key)
    try:
        yield SCENARIOS_BY_KEY[key]
    finally:
        _active.reset(token)


# ── shared paths (not scenario-scoped) ──────────────────────────────────


def shared_db_path() -> Path:
    """Sources + chunks + chunks_fts live here — shared across all scenarios."""
    return settings.data_dir / "shared.sqlite"


def shared_chunks_npz_path() -> Path:
    """Chunk embeddings — shared across scenarios (only Semantic Snippets reads them)."""
    return settings.embeddings_dir / "chunks.npz"
