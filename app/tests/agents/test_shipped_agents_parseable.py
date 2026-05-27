"""Every shipped agent .md must parse to a valid AgentSpec and reference live tools+skills."""

from __future__ import annotations

from importlib import resources
from pathlib import Path

import pytest

from openacad.runtime.agent_spec import AgentSpec
from openacad.runtime.loader import load_skills
from openacad.runtime.tool_registry import get_registry


def _shipped_agent_files() -> list[Path]:
    root = Path(str(resources.files("openacad.agents")))
    return sorted(root.glob("*.md"))


SHIPPED_AGENTS = _shipped_agent_files()


def test_at_least_four_shipped_agents() -> None:
    names = {p.stem for p in SHIPPED_AGENTS}
    assert {"extractor", "answerer", "scorer", "meta_evaluator"} <= names


@pytest.mark.parametrize("agent_path", SHIPPED_AGENTS, ids=lambda p: p.stem)
def test_agent_md_parses(agent_path: Path) -> None:
    spec = AgentSpec.from_markdown(agent_path.read_text(encoding="utf-8"))
    assert spec.name == agent_path.stem
    assert spec.description, f"{agent_path.name} missing description"
    assert spec.model, f"{agent_path.name} missing model"
    assert spec.instruction, f"{agent_path.name} has empty instruction"


@pytest.mark.parametrize("agent_path", SHIPPED_AGENTS, ids=lambda p: p.stem)
def test_agent_tools_are_registered(agent_path: Path) -> None:
    spec = AgentSpec.from_markdown(agent_path.read_text(encoding="utf-8"))
    reg = get_registry()
    for tool_name in spec.tools:
        assert reg.has(tool_name), (
            f"agent {spec.name!r} references unregistered tool {tool_name!r}"
        )


@pytest.mark.parametrize("agent_path", SHIPPED_AGENTS, ids=lambda p: p.stem)
def test_agent_skills_exist(agent_path: Path) -> None:
    spec = AgentSpec.from_markdown(agent_path.read_text(encoding="utf-8"))
    skill_names = set(load_skills(None).keys())
    for skill_name in spec.skills:
        assert skill_name in skill_names, (
            f"agent {spec.name!r} references unknown skill {skill_name!r}"
        )
