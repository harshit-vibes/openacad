"""``openacad extract <doc-id>`` — run the extractor agent over a doc's chunks.

For each chunk, we invoke the ``extractor`` agent and write the agent's textual
output as ``draft-NNN.md`` under ``.openacad/drafts/<doc-id>/``. The agent's
output schema is intentionally not enforced here — the curate command is where
drafts become atoms (or are discarded).
"""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from openacad.cli.vault_helper import get_vault_from_ctx
from openacad.runtime import AgentRunner
from openacad.vault.chunks import read_chunks

console = Console()


def extract(
    ctx: typer.Context,
    doc_id: str = typer.Argument(..., help="doc-id whose chunks should be extracted from."),
    limit: int = typer.Option(0, "--limit", help="Cap chunk count; 0 = no cap."),
    vault_path: Path | None = typer.Option(None, "--vault", help="Vault path."),
) -> None:
    """Run the extractor agent on each chunk, persisting drafts to disk."""
    vault = get_vault_from_ctx(ctx, vault_path)
    chunks_path = vault.chunks_dir / f"{doc_id}.jsonl"
    if not chunks_path.exists():
        console.print(
            f"[red]no chunks for {doc_id}[/red] — run `openacad chunk {doc_id}` first.",
            style="red",
        )
        raise typer.Exit(code=1)

    chunks = list(read_chunks(chunks_path))
    if limit and limit > 0:
        chunks = chunks[:limit]

    drafts_dir = vault.drafts_dir / doc_id
    drafts_dir.mkdir(parents=True, exist_ok=True)

    runner = AgentRunner(vault)
    n_written = 0
    with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as progress:
        task = progress.add_task(f"extracting {doc_id}", total=len(chunks))
        for i, c in enumerate(chunks, start=1):
            progress.update(task, description=f"chunk {i}/{len(chunks)}: {c.id}")
            try:
                result = runner.run(
                    "extractor",
                    chunk_id=c.id,
                    doc_id=doc_id,
                    chunk_text=c.text,
                    char_start=getattr(c, "char_start", 0),
                    char_end=getattr(c, "char_end", len(c.text)),
                    page=getattr(c, "page", None),
                )
            except Exception as exc:  # noqa: BLE001 — never abort the loop
                console.print(f"[red]chunk {c.id} failed: {exc}[/red]")
                progress.advance(task)
                continue

            draft_path = drafts_dir / f"draft-{i:03d}.md"
            draft_path.write_text(str(result.output), encoding="utf-8")
            n_written += 1
            progress.advance(task)

    console.print(f"[green]extracted[/green] {n_written}/{len(chunks)} drafts → {drafts_dir}")
    vault.close()
