"""``openacad chunk <doc-id>`` — extract chunks from an ingested PDF."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from openacad.cli.vault_helper import get_vault_from_ctx

console = Console()


def chunk(
    ctx: typer.Context,
    doc_id: str = typer.Argument(..., help="doc-id from `openacad ingest`."),
    target_tokens: int = typer.Option(400, "--target-tokens", help="Approx tokens per chunk."),
    overlap: int = typer.Option(50, "--overlap", help="Token overlap between adjacent chunks."),
    vault_path: Path | None = typer.Option(None, "--vault", help="Vault path."),
) -> None:
    """Extract chunks from a previously-ingested PDF and write to ``.openacad/chunks/``."""
    vault = get_vault_from_ctx(ctx, vault_path)
    chunks = vault.chunk(doc_id, target_tokens=target_tokens, overlap=overlap)
    console.print(f"[green]chunked[/green] {doc_id}: [bold]{len(chunks)}[/bold] chunks")
    vault.close()
