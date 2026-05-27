"""``openacad atoms merge <id1> <id2> [...]`` — merge atoms via $EDITOR.

Opens ``$EDITOR`` with each parent atom's body concatenated under a header.
The scholar writes a unified body. On save, ``vault.merge`` is called which:

- creates a new merged atom (id is auto-generated from parent ids)
- archives each parent atom (status: archived)
- unions all source spans into ``sources: list``
"""

from __future__ import annotations

import os
import re
import subprocess
import tempfile
from pathlib import Path

import typer
from rich.console import Console

from openacad.cli.vault_helper import get_vault_from_ctx

console = Console()


def _open_editor(initial_text: str) -> str | None:
    editor = os.environ.get("EDITOR", "vi")
    with tempfile.NamedTemporaryFile(suffix=".md", mode="w+", delete=False) as fh:
        fh.write(initial_text)
        tmp_path = fh.name
    try:
        subprocess.call([editor, tmp_path])
        return Path(tmp_path).read_text(encoding="utf-8")
    except Exception as exc:
        console.print(f"[red]editor failed: {exc}[/red]")
        return None
    finally:
        try:
            Path(tmp_path).unlink()
        except FileNotFoundError:
            pass


def _strip_comments(text: str) -> str:
    return "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("#"))


def merge(
    ctx: typer.Context,
    atom_ids: list[str] = typer.Argument(..., help="Two or more atom ids to merge."),
    merged_id: str | None = typer.Option(
        None,
        "--merged-id",
        help="Explicit id for the merged atom (default: auto-generated).",
    ),
    vault_path: Path | None = typer.Option(None, "--vault", help="Vault path."),
) -> None:
    """Open $EDITOR on the concatenated bodies; on save, call vault.merge."""
    if len(atom_ids) < 2:
        console.print("[red]merge requires at least 2 atom ids[/red]")
        raise typer.Exit(code=1)

    vault = get_vault_from_ctx(ctx, vault_path)
    parents = []
    for aid in atom_ids:
        p = vault.atom(aid)
        if p is None:
            console.print(f"[red]atom not found: {aid}[/red]")
            raise typer.Exit(code=1)
        parents.append(p)

    initial_lines: list[str] = [
        "# Merge atoms: " + ", ".join(p.id for p in parents),
        "# Write the unified body below. Comment lines (starting with '#') will be stripped.",
        "#",
    ]
    for p in parents:
        initial_lines.append(f"# ── from {p.id} ──")
        initial_lines.append(p.body.strip())
        initial_lines.append("")
    initial = "\n".join(initial_lines) + "\n"

    edited = _open_editor(initial)
    if edited is None:
        console.print("[red]edit cancelled[/red]")
        raise typer.Exit(code=1)

    unified_body = _strip_comments(edited).strip()
    if not unified_body:
        console.print("[red]merged body is empty; aborting[/red]")
        raise typer.Exit(code=1)

    merged = vault.merge(
        atom_ids,
        body=unified_body,
        type=parents[0].type,
        merged_id=merged_id,
        agent="cli.atoms.merge",
    )
    console.print(f"[green]merged[/green] {len(atom_ids)} atoms → [bold]{merged.id}[/bold]")
    console.print(f"  parents archived: {', '.join(atom_ids)}")
    vault.close()
