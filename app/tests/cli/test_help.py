"""``--help`` smoke tests for every CLI subcommand.

These tests don't need a vault, an LLM key, or any I/O — they just confirm
that the Typer wiring is intact and every command is discoverable.
"""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

from openacad.cli.__main__ import app

runner = CliRunner()


def test_root_help_lists_every_subcommand():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0, result.output
    out = result.output
    # Top-level commands
    for cmd in [
        "init",
        "reindex",
        "ingest",
        "chunk",
        "extract",
        "curate",
        "ask",
        "evolve",
        "eval",
        "ui",
        "museum",
        "atoms",
        "query",
        "agents",
    ]:
        assert cmd in out, f"missing top-level command in --help: {cmd!r}"


@pytest.mark.parametrize(
    "cmd",
    [
        ["init", "--help"],
        ["reindex", "--help"],
        ["ingest", "--help"],
        ["chunk", "--help"],
        ["extract", "--help"],
        ["curate", "--help"],
        ["ask", "--help"],
        ["evolve", "--help"],
        ["eval", "--help"],
        ["ui", "--help"],
        ["museum", "--help"],
        ["atoms", "--help"],
        ["atoms", "split", "--help"],
        ["atoms", "merge", "--help"],
        ["query", "--help"],
        ["query", "search", "--help"],
        ["query", "semantic", "--help"],
        ["query", "atoms", "--help"],
        ["query", "incoming", "--help"],
        ["query", "outgoing", "--help"],
        ["query", "path", "--help"],
        ["query", "source", "--help"],
        ["agents", "--help"],
        ["agents", "list", "--help"],
        ["agents", "show", "--help"],
        ["agents", "edit", "--help"],
        ["agents", "versions", "--help"],
        ["agents", "diff", "--help"],
        ["agents", "promote", "--help"],
    ],
)
def test_subcommand_help_renders(cmd: list[str]):
    result = runner.invoke(app, cmd)
    assert result.exit_code == 0, f"--help failed for {cmd}: {result.output}"
    # Each help output should at least include the program name or some usage banner
    assert "Usage:" in result.output or "Options" in result.output


def test_query_help_mentions_shell_equivalent():
    """The query sub-typer should advertise shell equivalents for grep-able patterns."""
    result = runner.invoke(app, ["query", "search", "--help"])
    assert result.exit_code == 0
    # We document `rg` as the shell equivalent for FTS
    assert "rg" in result.output

    result = runner.invoke(app, ["query", "incoming", "--help"])
    assert result.exit_code == 0
    assert "rg" in result.output
