"""Round-trip tests for SkillSpec markdown serialization."""

from __future__ import annotations

from openacad.runtime.skill_spec import SkillSpec


def test_minimal_skill_parses() -> None:
    md = """---
name: tiny
description: a tiny skill
tools: []
sub_agents: []
---

Workflow body."""
    spec = SkillSpec.from_markdown(md)
    assert spec.name == "tiny"
    assert spec.description == "a tiny skill"
    assert spec.tools == []
    assert spec.sub_agents == []
    assert spec.instruction == "Workflow body."


def test_skill_with_tools_and_sub_agents() -> None:
    md = """---
name: curate
description: curation
tools:
  - propose_atom
  - search_vault
sub_agents:
  - scorer
---

Curate stuff."""
    spec = SkillSpec.from_markdown(md)
    assert spec.tools == ["propose_atom", "search_vault"]
    assert spec.sub_agents == ["scorer"]


def test_roundtrip_preserves_essentials() -> None:
    original = SkillSpec(
        name="r1",
        description="d",
        tools=["a", "b"],
        sub_agents=["scorer"],
        instruction="hello body",
    )
    md = original.to_markdown()
    parsed = SkillSpec.from_markdown(md)
    assert parsed.name == original.name
    assert parsed.description == original.description
    assert parsed.tools == original.tools
    assert parsed.sub_agents == original.sub_agents
    assert parsed.instruction == original.instruction
