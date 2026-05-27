"""``openacad eval`` — run the answerer against canonical questions in data/gold/."""

from __future__ import annotations

from pathlib import Path

import typer
import yaml
from rich.console import Console
from rich.table import Table

from openacad.cli.vault_helper import get_vault_from_ctx
from openacad.runtime import AgentRunner

console = Console()


def _find_questions_yaml() -> Path | None:
    """Locate ``data/gold/questions.yaml`` next to the app root."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "data" / "gold" / "questions.yaml"
        if candidate.exists():
            return candidate
    return None


def run_eval(
    ctx: typer.Context,
    questions_yaml: Path | None = typer.Option(
        None,
        "--questions",
        help="Path to questions.yaml (default: app/data/gold/questions.yaml).",
    ),
    limit: int = typer.Option(0, "--limit", help="Cap question count; 0 = all."),
    vault_path: Path | None = typer.Option(None, "--vault", help="Vault path."),
) -> None:
    """Run the answerer over the canonical gold question set and print a summary."""
    qpath = questions_yaml or _find_questions_yaml()
    if qpath is None or not qpath.exists():
        console.print("[red]questions.yaml not found[/red] - supply --questions.")
        raise typer.Exit(code=1)

    questions = yaml.safe_load(qpath.read_text(encoding="utf-8")) or []
    if limit and limit > 0:
        questions = questions[:limit]

    vault = get_vault_from_ctx(ctx, vault_path)
    runner = AgentRunner(vault)

    table = Table(title=f"eval - {qpath}")
    table.add_column("id", style="bold cyan")
    table.add_column("question", overflow="fold")
    table.add_column("answer preview", overflow="fold")
    table.add_column("status")

    for q in questions:
        qid = q.get("id", "?")
        text = q.get("question", "")
        try:
            result = runner.run("answerer", question=text)
            preview = str(result.output)[:120].replace("\n", " ")
            table.add_row(qid, text[:60], preview, "[green]ok[/green]")
        except Exception as exc:
            table.add_row(qid, text[:60], "", f"[red]error: {exc}[/red]")

    console.print(table)
    vault.close()


# Alias so __main__ can import as ``eval_cmd.eval``.
# Avoids shadowing the builtin in this module's namespace.
globals()["eval"] = run_eval  # noqa: A001
