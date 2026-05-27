"""``openacad query <subcommand>`` tests against the migrated demo vault.

These tests use the ``data/vault/`` fixture that M1 migrated from the legacy
SQLite vault. They are read-only.
"""

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


def test_query_search_returns_paths():
    result = runner.invoke(
        app,
        ["query", "search", "poverty", "--vault", str(DEMO_VAULT)],
    )
    assert result.exit_code == 0, result.output
    lines = [line for line in result.output.strip().splitlines() if line]
    assert len(lines) > 0
    # Every emitted line should be a real on-disk path to a vault atom.
    for line in lines:
        p = Path(line)
        assert p.exists(), f"emitted path does not exist on disk: {line}"
        assert p.parent.resolve() == DEMO_VAULT.resolve()


def test_query_atoms_filter_by_type():
    result = runner.invoke(
        app,
        ["query", "atoms", "--where", "type=claim", "--vault", str(DEMO_VAULT)],
    )
    assert result.exit_code == 0, result.output
    # At least one claim should match.
    lines = [line for line in result.output.strip().splitlines() if line]
    assert len(lines) > 0


def test_query_incoming_finds_wiki_link_referrers():
    """The 'failure consequences' atom is wiki-linked from the 'afford failure' atom."""
    target = "2023-sdg-briefing-claim-sdg-failure-consequences"
    result = runner.invoke(
        app,
        ["query", "incoming", target, "--vault", str(DEMO_VAULT)],
    )
    assert result.exit_code == 0, result.output
    out = result.output
    assert "2023-sdg-briefing-claim-no-country-afford-failure" in out


def test_query_source_returns_chunk_substring():
    atom_id = "2024-sdg1-target-1-1-extreme-poverty"
    atom_md = DEMO_VAULT / f"{atom_id}.md"
    assert atom_md.exists()

    result = runner.invoke(
        app,
        ["query", "source", atom_id, "--vault", str(DEMO_VAULT)],
    )
    assert result.exit_code == 0, result.output
    # source_text should produce non-empty content.
    assert len(result.output.strip()) > 0


def test_query_search_table_format():
    result = runner.invoke(
        app,
        ["query", "search", "poverty", "--format", "table", "--vault", str(DEMO_VAULT)],
    )
    assert result.exit_code == 0
    # Table view includes column headers.
    assert "id" in result.output and "type" in result.output
