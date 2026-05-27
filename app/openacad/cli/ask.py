"""``openacad ask "<question>"`` — Q&A via the answerer agent."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel

from openacad.cli.vault_helper import get_vault_from_ctx
from openacad.runtime import AgentRunner

console = Console()


def ask(
    ctx: typer.Context,
    question: str = typer.Argument(..., help="The question to ask."),
    paper: str | None = typer.Option(
        None,
        "--paper",
        help="Comma-separated doc-ids to constrain retrieval (optional).",
    ),
    vault_path: Path | None = typer.Option(None, "--vault", help="Vault path."),
) -> None:
    """Run the answerer agent and pretty-print the result."""
    vault = get_vault_from_ctx(ctx, vault_path)
    paper_ids: list[str] = []
    if paper:
        paper_ids = [p.strip() for p in paper.split(",") if p.strip()]

    runner = AgentRunner(vault)
    try:
        result = runner.run("answerer", question=question, paper_ids=paper_ids)
    except Exception as exc:
        console.print(f"[red]ask failed: {exc}[/red]")
        raise typer.Exit(code=1) from exc

    answer = result.output
    console.print(Panel(str(answer), title="answer", border_style="cyan"))
    console.print(f"[dim]tools used: {', '.join(result.tools_used) or '(none)'}[/dim]")
    vault.close()
