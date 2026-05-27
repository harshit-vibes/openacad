"""``openacad ingest <pdf>`` — copy a PDF into the vault sidecar."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from openacad.cli.vault_helper import get_vault_from_ctx

console = Console()


def ingest(
    ctx: typer.Context,
    pdf: Path = typer.Argument(..., help="Path to a PDF on disk."),
    vault_path: Path | None = typer.Option(None, "--vault", help="Vault path."),
) -> None:
    """Copy ``pdf`` into ``.openacad/documents/`` and emit its ``doc_id``."""
    vault = get_vault_from_ctx(ctx, vault_path)
    if not pdf.exists():
        console.print(f"[red]PDF not found: {pdf}[/red]")
        raise typer.Exit(code=1)
    doc_id = vault.ingest(pdf)
    console.print(f"[green]ingested[/green] {pdf.name} → doc-id: [bold]{doc_id}[/bold]")
    vault.close()
