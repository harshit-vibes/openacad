"""``openacad agents`` tests — list + show against the migrated vault."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from openacad.cli.__main__ import app

DEMO_VAULT = Path(__file__).resolve().parents[2] / "data" / "vault"
runner = CliRunner()


pytestmark = pytest.mark.skipif(
    not (DEMO_VAULT / ".openacad").exists(),
    reason="migrated demo vault not present",
)


def test_agents_list_includes_four_shipped_agents():
    result = runner.invoke(app, ["agents", "list", "--vault", str(DEMO_VAULT)])
    assert result.exit_code == 0, result.output
    out = result.output
    for name in ("extractor", "answerer", "scorer", "meta_evaluat"):  # truncated by rich
        assert name in out, f"agent name {name!r} missing from list output"


def test_agents_show_extractor_prints_spec(tmp_path: Path):
    result = runner.invoke(app, ["agents", "show", "extractor", "--vault", str(DEMO_VAULT)])
    assert result.exit_code == 0, result.output
    # The extractor spec mentions "extraction" or "atomic notes" in its instruction body.
    assert "extract" in result.output.lower()
    # And the rendered frontmatter should mention the model.
    assert "model" in result.output.lower() or "gpt" in result.output.lower()


def test_agents_show_unknown_agent_exits_nonzero():
    result = runner.invoke(
        app, ["agents", "show", "nonexistent-agent", "--vault", str(DEMO_VAULT)]
    )
    assert result.exit_code != 0


def test_agents_versions_empty_initially(tmp_path: Path):
    """A freshly-initialised vault has no archived versions."""
    fresh = tmp_path / "v"
    runner.invoke(app, ["init", str(fresh)])
    result = runner.invoke(app, ["agents", "versions", "extractor", "--vault", str(fresh)])
    assert result.exit_code == 0
    # Should report 'no versions' rather than crash.
    assert "no versions" in result.output.lower() or "extractor" in result.output.lower()
