"""``openacad curate`` — HITL loop over pending draft atoms.

Walks ``.openacad/drafts/<doc-id>/draft-*.md`` files. For each, shows the body
preview + source span + neighbour atoms, and prompts the scholar for a verdict.

Verdicts:
    a  accept   — write draft → ``<vault>/<atom-id>.md`` as ``status: active``
    e  edit     — open $EDITOR; on save, treat as accept
    r  reject   — move draft to ``.openacad/drafts/<doc-id>/.rejected/``
    s  split    — defer to ``openacad atoms split`` after accept
    m  merge    — accumulate ids for batch merge (printed at end)
    d  defer    — leave the draft in place
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from openacad.cli.vault_helper import get_vault_from_ctx
from openacad.vault import AtomicNote, Vault

console = Console()


def _list_drafts(vault: Vault, doc: str | None) -> list[Path]:
    base = vault.drafts_dir
    if not base.exists():
        return []
    out: list[Path] = []
    iter_dirs = [base / doc] if doc else sorted(p for p in base.iterdir() if p.is_dir())
    for d in iter_dirs:
        if not d.exists() or not d.is_dir():
            continue
        for p in sorted(d.glob("draft-*.md")):
            out.append(p)
    return out


def _try_parse_atom(text: str, fallback_id: str) -> AtomicNote | None:
    try:
        return AtomicNote.from_markdown(text, id=fallback_id)
    except Exception:
        return None


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


def curate(
    ctx: typer.Context,
    doc: str | None = typer.Option(None, "--doc", help="Only curate drafts for this doc-id."),
    limit: int = typer.Option(0, "--limit", help="Cap drafts processed this run; 0 = no cap."),
    vault_path: Path | None = typer.Option(None, "--vault", help="Vault path."),
) -> None:
    """Interactive HITL loop over pending drafts."""
    vault = get_vault_from_ctx(ctx, vault_path)
    drafts = _list_drafts(vault, doc)
    if not drafts:
        console.print("[yellow]no pending drafts[/yellow] in .openacad/drafts/")
        vault.close()
        return

    if limit and limit > 0:
        drafts = drafts[:limit]

    console.print(f"[bold]{len(drafts)}[/bold] pending drafts. (a/e/r/s/m/d, q to quit)")

    merge_batch: list[str] = []
    n_accept = n_reject = n_defer = n_split = n_merge = 0

    for i, draft_path in enumerate(drafts, start=1):
        text = draft_path.read_text(encoding="utf-8")
        atom_id_guess = draft_path.stem  # e.g. "draft-001"
        atom = _try_parse_atom(text, atom_id_guess)

        # Render
        console.rule(f"[{i}/{len(drafts)}] {draft_path.relative_to(vault.path)}")
        if atom is not None:
            console.print(Panel(atom.body[:600], title=f"body — {atom.id}", border_style="cyan"))
            if atom.sources:
                try:
                    quote = vault.source_text(atom)
                    console.print(Panel(quote[:500], title="source quote", border_style="green"))
                except Exception as exc:
                    console.print(f"[yellow]source not available: {exc}[/yellow]")
            # Neighbour atoms: search for terms from the body
            try:
                neighbours = vault.search(atom.body[:80], top_k=3)
                if neighbours:
                    nblist = "\n".join(f"  - {a.id}" for a in neighbours)
                    console.print(Panel(nblist, title="nearby atoms (FTS)", border_style="magenta"))
            except Exception:
                pass
        else:
            console.print(Panel(text[:800], title="raw draft (unparsed)", border_style="yellow"))

        choice = Prompt.ask(
            "verdict",
            choices=["a", "e", "r", "s", "m", "d", "q"],
            default="d",
        )

        if choice == "q":
            console.print("[yellow]quit[/yellow]")
            break

        if choice == "a":
            if atom is None:
                console.print("[red]cannot accept un-parseable draft[/red]")
                continue
            atom = atom.model_copy(update={"status": "active"})
            vault.write(atom, reconcile=True, agent="curate")
            draft_path.unlink()
            n_accept += 1
            console.print(f"[green]✓ accepted[/green] {atom.id}")

        elif choice == "e":
            edited = _open_editor(text)
            if edited is None:
                console.print("[red]edit cancelled[/red]")
                continue
            atom = _try_parse_atom(edited, atom_id_guess)
            if atom is None:
                console.print("[red]edited draft still not parseable; skipping[/red]")
                continue
            atom = atom.model_copy(update={"status": "active"})
            vault.write(atom, reconcile=True, agent="curate")
            draft_path.unlink()
            n_accept += 1
            console.print(f"[green]✓ accepted (edited)[/green] {atom.id}")

        elif choice == "r":
            rejected_dir = draft_path.parent / ".rejected"
            rejected_dir.mkdir(exist_ok=True)
            shutil.move(str(draft_path), rejected_dir / draft_path.name)
            n_reject += 1
            console.print(f"[red]✗ rejected[/red]")

        elif choice == "s":
            if atom is None:
                console.print("[red]cannot split un-parseable draft[/red]")
                continue
            console.print(
                f"[blue]deferred to split[/blue] — run `openacad atoms split {atom.id}` "
                f"after accepting the parent."
            )
            n_split += 1

        elif choice == "m":
            if atom is None:
                console.print("[red]cannot merge un-parseable draft[/red]")
                continue
            merge_batch.append(atom.id)
            console.print(f"[blue]added to merge batch ({len(merge_batch)} total)[/blue]")
            n_merge += 1

        elif choice == "d":
            n_defer += 1
            console.print("[dim]deferred[/dim]")

    console.rule("session summary")
    console.print(
        f"accepted: {n_accept}  rejected: {n_reject}  deferred: {n_defer}  "
        f"split: {n_split}  merge-batch: {n_merge}"
    )
    if merge_batch:
        console.print(
            "[bold]merge batch[/bold] — run:  "
            f"openacad atoms merge {' '.join(merge_batch)}"
        )
    vault.close()
