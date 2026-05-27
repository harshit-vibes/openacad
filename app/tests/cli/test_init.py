"""``openacad init`` tests — scaffold a fresh vault + idempotent re-run."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from openacad.cli.__main__ import app

runner = CliRunner()


def test_init_creates_sidecar_and_copies_agents(tmp_path: Path):
    vault = tmp_path / "v"
    result = runner.invoke(app, ["init", str(vault)])
    assert result.exit_code == 0, result.output

    sidecar = vault / ".openacad"
    assert sidecar.is_dir()
    agents_dir = sidecar / "agents"
    skills_dir = sidecar / "skills"
    assert agents_dir.is_dir()
    assert skills_dir.is_dir()

    # The four shipped agents must be present.
    agent_files = {p.name for p in agents_dir.glob("*.md")}
    assert agent_files == {
        "extractor.md",
        "answerer.md",
        "scorer.md",
        "meta_evaluator.md",
    }

    # Each shipped skill ships as <name>/SKILL.md.
    skill_dirs = {p.name for p in skills_dir.iterdir() if p.is_dir()}
    assert "atom-curation" in skill_dirs
    assert "pdf-ingestion" in skill_dirs
    assert "source-verification" in skill_dirs
    assert "split-and-merge" in skill_dirs
    assert "relation-traversal" in skill_dirs

    for sd in (skills_dir / d for d in skill_dirs):
        assert (sd / "SKILL.md").is_file(), sd


def test_init_is_idempotent(tmp_path: Path):
    vault = tmp_path / "v"
    r1 = runner.invoke(app, ["init", str(vault)])
    assert r1.exit_code == 0
    r2 = runner.invoke(app, ["init", str(vault)])
    assert r2.exit_code == 0
    # Second run should still see all four agents on disk.
    agents = list((vault / ".openacad" / "agents").glob("*.md"))
    assert len(agents) == 4
