"""``openacad ui`` — placeholder for the M4 Next.js playground."""

from __future__ import annotations

import typer
from rich.console import Console

console = Console()


def ui(
    ctx: typer.Context,
    dev: bool = typer.Option(False, "--dev", help="Run UI + FastAPI in dev mode."),
    port: int = typer.Option(3000, "--port", help="Port for the UI server."),
) -> None:
    """The Next.js playground is built in M4. For now, this command is a placeholder."""
    console.print("[yellow]openacad ui[/yellow] is part of Milestone 4 (Next.js playground).")
    console.print("Not built yet — use `openacad museum` for the frozen 9-rung Streamlit tour.")
    raise typer.Exit(code=0)
