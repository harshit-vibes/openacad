"""Round-trip tests for AgentSpec markdown serialization."""

from __future__ import annotations

from openacad.runtime.agent_spec import AgentSpec


def test_minimal_agent_parses() -> None:
    md = """---
name: tiny
description: a tiny agent
model: openai/gpt-4o-mini
tools: []
skills: []
---

You are a tiny agent. Be helpful."""
    spec = AgentSpec.from_markdown(md)
    assert spec.name == "tiny"
    assert spec.description == "a tiny agent"
    assert spec.model == "openai/gpt-4o-mini"
    assert spec.tools == []
    assert spec.skills == []
    assert spec.instruction.startswith("You are a tiny agent")


def test_agent_with_tools_and_skills() -> None:
    md = """---
name: rich
description: rich agent
model: openai/gpt-4o-mini
tools:
  - search_vault
  - get_atom
skills:
  - source-verification
---

Instructions body here."""
    spec = AgentSpec.from_markdown(md)
    assert spec.tools == ["search_vault", "get_atom"]
    assert spec.skills == ["source-verification"]
    assert spec.instruction == "Instructions body here."


def test_roundtrip_preserves_essentials() -> None:
    original = AgentSpec(
        name="r1",
        description="d",
        model="openai/gpt-4o-mini",
        tools=["a", "b"],
        skills=["s1"],
        instruction="hello body",
    )
    md = original.to_markdown()
    parsed = AgentSpec.from_markdown(md)
    assert parsed.name == original.name
    assert parsed.description == original.description
    assert parsed.model == original.model
    assert parsed.tools == original.tools
    assert parsed.skills == original.skills
    assert parsed.instruction == original.instruction


def test_missing_fields_default_safely() -> None:
    md = """---
name: only-name
---

Body."""
    spec = AgentSpec.from_markdown(md)
    assert spec.name == "only-name"
    assert spec.tools == []
    assert spec.skills == []
    assert spec.model == "openai/gpt-4o-mini"
    assert spec.instruction == "Body."
