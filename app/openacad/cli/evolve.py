"""``openacad evolve`` — run the meta-evaluator agent.

The meta-evaluator inspects recent activity + agent specs and proposes new
versions of selected agents. We write any proposed agents to
``.openacad/agents/proposed/<name>.md`` for the user to inspect, diff, and
optionally promote.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import typer
from rich.console import Console

from openacad.cli.vault_helper import get_vault_from_ctx
from openacad.runtime import AgentRunner

console = Console()


def _extract_proposals(output: Any) -> list[dict[str, str]]:
    """Try several shapes the meta-evaluator might return.

    Accepted shapes:
        - ``{"proposals": [{"role": "...", "spec": "..."}]}``
        - ``[{"role": "...", "spec": "..."}]``
        - JSON string of the above
    """
    if isinstance(output, str):
        try:
            output = json.loads(output)
        except Exception:
            return []
    if isinstance(output, dict):
        ps = output.get("proposals") or output.get("agents") or []
        return [p for p in ps if isinstance(p, dict)]
    if isinstance(output, list):
        return [p for p in output if isinstance(p, dict)]
    return []


def evolve(
    ctx: typer.Context,
    vault_path: Path | None = typer.Option(None, "--vault", help="Vault path."),
) -> None:
    """Run the meta-evaluator and write any proposed agents to disk."""
    vault = get_vault_from_ctx(ctx, vault_path)
    runner = AgentRunner(vault)
    try:
        result = runner.run("meta_evaluator")
    except Exception as exc:
        console.print(f"[red]evolve failed: {exc}[/red]")
        raise typer.Exit(code=1) from exc

    proposed_dir = vault.agents_dir / "proposed"
    proposed_dir.mkdir(parents=True, exist_ok=True)

    proposals = _extract_proposals(result.output)
    if not proposals:
        console.print("[yellow]meta-evaluator produced no structured proposals[/yellow]")
        # Save the raw output as a single advisory dump.
        dump = proposed_dir / "_raw.md"
        dump.write_text(str(result.output), encoding="utf-8")
        console.print(f"raw output saved to {dump}")
        vault.close()
        return

    n_written = 0
    for p in proposals:
        role = str(p.get("role") or p.get("name") or "").strip()
        spec = str(p.get("spec") or p.get("body") or "").strip()
        if not role or not spec:
            continue
        target = proposed_dir / f"{role}.md"
        target.write_text(spec, encoding="utf-8")
        n_written += 1
        console.print(f"[green]proposed[/green] {role}.md")

    console.print(f"[bold]{n_written}[/bold] proposals written to {proposed_dir}")
    vault.close()
