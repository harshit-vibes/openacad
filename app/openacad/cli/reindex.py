"""``openacad reindex`` — rebuild FTS + embeddings + registry from on-disk atoms."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from openacad.cli.vault_helper import get_vault_from_ctx

console = Console()


def reindex(
    ctx: typer.Context,
    vault_path: Path | None = typer.Option(None, "--vault", help="Vault path."),
) -> None:
    """Rebuild the vault's FTS + embeddings + registry caches from disk."""
    vault = get_vault_from_ctx(ctx, vault_path)
    n = len(vault.atoms)
    console.print(f"reindexing [bold]{n}[/bold] atoms from {vault.path} …")
    vault.reindex()
    console.print("[green]reindex complete[/green]")
    vault.close()
