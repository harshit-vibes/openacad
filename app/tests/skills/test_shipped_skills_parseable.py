"""Every shipped SKILL.md must parse to a valid SkillSpec and reference live tools."""

from __future__ import annotations

from importlib import resources
from pathlib import Path

import pytest

from openacad.runtime.skill_spec import SkillSpec
from openacad.runtime.tool_registry import get_registry


def _shipped_skill_files() -> list[Path]:
    root = Path(str(resources.files("openacad.skills")))
    return sorted(p for p in root.glob("*/SKILL.md"))


SHIPPED_SKILLS = _shipped_skill_files()


def test_at_least_five_shipped_skills() -> None:
    names = {p.parent.name for p in SHIPPED_SKILLS}
    assert {
        "atom-curation",
        "pdf-ingestion",
        "source-verification",
        "split-and-merge",
        "relation-traversal",
    } <= names


@pytest.mark.parametrize("skill_path", SHIPPED_SKILLS, ids=lambda p: p.parent.name)
def test_skill_md_parses(skill_path: Path) -> None:
    spec = SkillSpec.from_markdown(skill_path.read_text(encoding="utf-8"))
    assert spec.name == skill_path.parent.name, (
        f"{skill_path} frontmatter name {spec.name!r} != dir name {skill_path.parent.name!r}"
    )
    assert spec.description
    assert spec.instruction


@pytest.mark.parametrize("skill_path", SHIPPED_SKILLS, ids=lambda p: p.parent.name)
def test_skill_tools_are_registered(skill_path: Path) -> None:
    spec = SkillSpec.from_markdown(skill_path.read_text(encoding="utf-8"))
    reg = get_registry()
    for tool_name in spec.tools:
        assert reg.has(tool_name), (
            f"skill {spec.name!r} references unregistered tool {tool_name!r}"
        )
