"""``openacad atoms split <atom-id>`` — split an atom into N parts via $EDITOR.

We open ``$EDITOR`` with the atom's body annotated by split markers. The
scholar inserts more ``--- split here ---`` lines to delimit parts (or removes
them to combine). On save, each part becomes its own atom with id
``<original-id>-pt<N>``; the source span is inherited from the parent unchanged.

The actual split is funneled through ``vault.split()`` which enforces the
source-span invariant.
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
from openacad.vault import AtomicNote

console = Console()

SPLIT_MARKER = "--- split here ---"


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


def _split_body(text: str) -> list[str]:
    """Split on the marker, trim whitespace, drop empties."""
    parts = re.split(r"(?m)^\s*" + re.escape(SPLIT_MARKER) + r"\s*$", text)
    return [p.strip() for p in parts if p.strip()]


def split(
    ctx: typer.Context,
    atom_id: str = typer.Argument(..., help="Atom id to split."),
    vault_path: Path | None = typer.Option(None, "--vault", help="Vault path."),
) -> None:
    """Open $EDITOR on the atom's body with split markers; persist the parts."""
    vault = get_vault_from_ctx(ctx, vault_path)
    parent = vault.atom(atom_id)
    if parent is None:
        console.print(f"[red]atom not found: {atom_id}[/red]")
        raise typer.Exit(code=1)

    initial = (
        f"# Split atom: {atom_id}\n"
        f"# Insert lines containing '{SPLIT_MARKER}' to split into multiple atoms.\n"
        f"# Comment lines (starting with '#') will be stripped before parsing.\n"
        f"#\n"
        f"{parent.body.strip()}\n"
    )
    edited = _open_editor(initial)
    if edited is None:
        console.print("[red]edit cancelled[/red]")
        raise typer.Exit(code=1)

    # Strip comment lines (those starting with '#' at column 0).
    cleaned = "\n".join(
        line for line in edited.splitlines() if not line.lstrip().startswith("#")
    )

    parts = _split_body(cleaned)
    if len(parts) < 2:
        console.print(
            f"[yellow]found {len(parts)} part(s); need at least 2 to split.[/yellow] "
            f"Add '{SPLIT_MARKER}' lines."
        )
        raise typer.Exit(code=1)

    children: list[AtomicNote] = []
    for i, part_body in enumerate(parts, start=1):
        child = AtomicNote(
            id=f"{atom_id}-pt{i}",
            type=parent.type,
            status="active",
            tags=list(parent.tags),
            attributes=dict(parent.attributes),
            sources=list(parent.sources),
            relations=list(parent.relations),
            body=part_body,
        )
        children.append(child)

    written = vault.split(atom_id, children, agent="cli.atoms.split")
    console.print(f"[green]split {atom_id}[/green] into {len(written)} parts:")
    for c in written:
        console.print(f"  - {c.id}")
    vault.close()
