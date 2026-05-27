"""Loader behaviour: shipped defaults + vault sidecar override."""

from __future__ import annotations

from pathlib import Path

from openacad.runtime.loader import load_agents, load_skills


def test_loads_shipped_agents_when_vault_is_none() -> None:
    specs = load_agents(None)
    assert "extractor" in specs
    assert "answerer" in specs
    assert "scorer" in specs
    assert "meta_evaluator" in specs


def test_loads_shipped_skills_when_vault_is_none() -> None:
    specs = load_skills(None)
    for name in [
        "atom-curation",
        "pdf-ingestion",
        "source-verification",
        "split-and-merge",
        "relation-traversal",
    ]:
        assert name in specs, f"missing shipped skill {name}"


def test_vault_sidecar_overrides_shipped(tmp_path: Path) -> None:
    """A vault-side answerer.md should win over the shipped one."""
    side = tmp_path / ".openacad" / "agents"
    side.mkdir(parents=True)
    (side / "answerer.md").write_text(
        """---
name: answerer
description: vault-side override
model: openai/gpt-4o-mini
tools: []
skills: []
---

Custom prompt from the vault.
""",
        encoding="utf-8",
    )

    class _V:
        path = tmp_path

    specs = load_agents(_V())
    assert specs["answerer"].description == "vault-side override"
    assert specs["answerer"].instruction.startswith("Custom prompt from the vault.")

    # Other shipped agents still load.
    assert "extractor" in specs


def test_vault_with_no_sidecar_falls_back_to_shipped(tmp_path: Path) -> None:
    class _V:
        path = tmp_path

    specs = load_agents(_V())
    assert "extractor" in specs
    assert "answerer" in specs
