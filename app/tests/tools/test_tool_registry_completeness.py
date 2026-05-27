"""Every tool referenced by any shipped agent/skill must exist in the global registry."""

from __future__ import annotations

from openacad.runtime.loader import load_agents, load_skills
from openacad.runtime.tool_registry import get_registry


def test_all_shipped_agent_tools_registered() -> None:
    reg = get_registry()
    for name, spec in load_agents(None).items():
        for tool_name in spec.tools:
            assert reg.has(tool_name), (
                f"agent {name!r} references unregistered tool {tool_name!r}"
            )


def test_all_shipped_skill_tools_registered() -> None:
    reg = get_registry()
    for name, spec in load_skills(None).items():
        for tool_name in spec.tools:
            assert reg.has(tool_name), (
                f"skill {name!r} references unregistered tool {tool_name!r}"
            )


def test_ten_canonical_tools_present() -> None:
    reg = get_registry()
    for name in [
        "search_vault",
        "semantic_search",
        "traverse_relations",
        "incoming",
        "outgoing",
        "get_atom",
        "propose_atom",
        "check_contradiction",
        "read_chunk",
        "source_text",
    ]:
        assert reg.has(name), f"canonical tool {name!r} missing"


def test_resolved_tools_are_callable() -> None:
    reg = get_registry()
    for name in reg.names():
        fn = reg.resolve(name)
        assert callable(fn), f"resolved tool {name!r} is not callable"
