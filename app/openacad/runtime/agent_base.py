"""Scenario-aware PydanticAI agent construction (formerly api/services/agent_factory.py).

Each agent role (Answerer / Extractor / Scorer / Meta-Evaluator) is built fresh
per scenario from the active prompt version recorded in that scenario's
state.sqlite `prompts` table. The active prompt body comes from a `.md` file in
`<vault>/prompts/<role>.v{N}.md`.

The cache is keyed by (scenario_key, role, version) so prompt promotion is a
hot-reload — the next call to `build_*` picks up the new version automatically.
"""

from __future__ import annotations

from pydantic_ai import Agent

from openacad.runtime.scenario import AgentRole, Tier, active_scenario
from openacad.runtime.llm import model_for, settings_for
from openacad.runtime import db
# (scenario_key, role) → (version, agent) of the currently-cached agent
_cache: dict[tuple[str, AgentRole], tuple[str, Agent]] = {}


def _active_prompt_body(role: AgentRole) -> tuple[str, str]:
    """Return (version, body) for the active prompt of the given role in the
    active scenario. Falls back to v1 from disk if no DB record exists."""
    s = active_scenario()
    prompts = [p for p in db.list_prompts(name=role.value) if p.state == "active"]
    if prompts:
        active = sorted(prompts, key=lambda p: p.created_at, reverse=True)[0]
        return active.version, active.body
    fn = s.prompts_dir / f"{role.value}.v1.md"
    if fn.exists():
        return f"{role.value}.v1", fn.read_text(encoding="utf-8")
    raise RuntimeError(
        f"no prompt for role={role.value} in scenario={s.key}; "
        f"run scripts/seed_scenarios.py"
    )


def _build_or_cached(role: AgentRole, builder) -> Agent:
    s = active_scenario()
    version, body = _active_prompt_body(role)
    cache_key = (s.key, role)
    cached = _cache.get(cache_key)
    if cached is not None and cached[0] == version:
        return cached[1]
    agent = builder(body)
    _cache[cache_key] = (version, agent)
    return agent


def _bust_cache_for(role: AgentRole) -> None:
    """Force the next build_* call to re-read the prompt. Used after promote."""
    s = active_scenario()
    _cache.pop((s.key, role), None)


# ── Public build_* dispatchers ──────────────────────────────────────────


def build_answerer() -> Agent:
    s = active_scenario()
    if s.tier == Tier.ATOMS:
        from openacad.agents.synthesizer.agent import _build_agent_with_prompt
        return _build_or_cached(AgentRole.ANSWERER, _build_agent_with_prompt)
    # COLD or CHUNK: simple Agent, no openacad — caller injects retrieved context.
    return _build_or_cached(
        AgentRole.ANSWERER,
        lambda body: Agent(
            model_for("synthesis"),
            system_prompt=body,
            output_type=str,
            retries=1,
            model_settings=settings_for("synthesis"),
        ),
    )


def build_extractor() -> Agent:
    from openacad.agents.extractor.agent import _build_agent_with_prompt
    return _build_or_cached(AgentRole.EXTRACTOR, _build_agent_with_prompt)


def build_scorer() -> Agent:
    from openacad.agents.scorer.agent import _build_agent_with_prompt
    return _build_or_cached(AgentRole.SCORER, _build_agent_with_prompt)


def build_meta_evaluator() -> Agent:
    from openacad.agents.meta_evaluator.agent import _build_agent_with_prompt
    return _build_or_cached(AgentRole.META_EVAL, _build_agent_with_prompt)


__all__ = [
    "build_answerer",
    "build_extractor",
    "build_scorer",
    "build_meta_evaluator",
    "_bust_cache_for",
]
