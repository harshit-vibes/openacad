"""Smoke tests for AgentRunner construction and wiring (no live LLM calls)."""

from __future__ import annotations

from typing import Any

from openacad.runtime.runner import AgentRunner


def test_runner_constructs_with_stub_vault(stub_vault: Any) -> None:
    runner = AgentRunner(stub_vault)
    assert set(runner.agents.keys()) >= {
        "extractor",
        "answerer",
        "scorer",
        "meta_evaluator",
    }
    assert len(runner.tools) >= 10


def test_runner_constructs_with_none_vault() -> None:
    """AgentRunner must construct even when no vault exists yet (e.g. CLI introspection)."""
    runner = AgentRunner(None)
    assert "extractor" in runner.agents


def test_compose_instruction_concatenates_skill_instructions(stub_vault: Any) -> None:
    runner = AgentRunner(stub_vault)
    extractor = runner.agents["extractor"]
    composed = runner._compose_instruction(extractor)
    # The extractor's own body must appear...
    assert "extraction agent" in composed.lower()
    # ... and each referenced skill's instruction must be folded in.
    for skill_name in extractor.skills:
        assert f"## Skill: {skill_name}" in composed


def test_resolve_tools_binds_vault(stub_vault: Any) -> None:
    runner = AgentRunner(stub_vault)
    extractor = runner.agents["extractor"]
    names, callables = runner._resolve_tools(extractor)
    # Agent tools + skill tools, no duplicates.
    expected = set(extractor.tools) | {
        t
        for sk in extractor.skills
        for t in runner.skills[sk].tools
        if sk in runner.skills
    }
    assert set(names) == expected
    # Each callable is invocable without `vault=` since it was bound via a closure.
    for name, fn in zip(names, callables, strict=True):
        assert callable(fn)
        assert fn.__name__ == name


def test_bound_tool_signature_hides_vault_from_pydantic_ai(stub_vault: Any) -> None:
    """Regression: PydanticAI introspects via inspect.signature; `vault` MUST NOT leak.

    If `vault` appears in the signature, the LLM-facing schema lists it as a parameter
    and the LLM will be asked (and fail) to supply it.
    """
    import inspect

    runner = AgentRunner(stub_vault)
    for spec in runner.agents.values():
        _, callables = runner._resolve_tools(spec)
        for fn in callables:
            sig = inspect.signature(fn)
            assert "vault" not in sig.parameters, (
                f"tool {fn.__name__!r} leaks 'vault' in its signature: {list(sig.parameters)}"
            )


def test_bound_tool_invokes_with_stub_vault(stub_vault: Any) -> None:
    """The closure actually injects the vault — the tool sees it without LLM passing it."""
    runner = AgentRunner(stub_vault)
    answerer = runner.agents["answerer"]
    names, callables = runner._resolve_tools(answerer)
    by_name = dict(zip(names, callables, strict=True))
    # search_vault has signature (query, top_k=10) after vault binding.
    hits = by_name["search_vault"]("hello")
    assert any(getattr(a, "id", None) == "atom-a" for a in hits)


def test_each_shipped_agent_resolves_its_tools(stub_vault: Any) -> None:
    """Every shipped agent's tools must exist in the registry."""
    runner = AgentRunner(stub_vault)
    for agent_name, spec in runner.agents.items():
        try:
            runner._resolve_tools(spec)
        except KeyError as e:
            raise AssertionError(f"agent {agent_name!r} references missing tool: {e}") from e


def test_run_invokes_pydantic_agent(monkeypatch, stub_vault: Any) -> None:
    """`runner.run()` builds a PydanticAI agent and calls run_sync on it (mocked)."""

    class _FakeResult:
        def __init__(self) -> None:
            self.output = "stub-answer"

    class _FakeAgent:
        def __init__(self, *a, **kw) -> None:
            self.init_kwargs = kw

        def run_sync(self, *args, **kwargs) -> _FakeResult:
            return _FakeResult()

    runner = AgentRunner(stub_vault)
    monkeypatch.setattr(runner, "_build_pydantic_agent", lambda *a, **kw: _FakeAgent())

    result = runner.run("answerer", question="What is SDG 1?")
    assert result.agent == "answerer"
    assert result.output == "stub-answer"
    assert "search_vault" in result.tools_used
