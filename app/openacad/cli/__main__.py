"""``openacad`` — Typer root for the new CLI surface.

Subcommand layout (mirrors the plan's CLI surface):

::

    openacad init [vault-dir]
    openacad reindex
    openacad ingest <pdf>
    openacad chunk <doc-id>
    openacad extract <doc-id>
    openacad curate
    openacad atoms split <atom-id>
    openacad atoms merge <a> <b> [...]
    openacad ask "<question>"
    openacad evolve
    openacad eval
    openacad query <subcommand>           # search/semantic/atoms/incoming/...
    openacad agents <subcommand>          # list/show/edit/versions/diff/promote
    openacad ui [--dev] [--port 3000]
    openacad museum

Every command (except ``init``) accepts ``--vault <path>``; the value is
stashed on ``ctx.obj`` by the root callback and consumed by the helpers in
:mod:`openacad.cli.vault_helper`.
"""

from __future__ import annotations

from pathlib import Path

import typer

from openacad.cli import (
    agents as agents_cmd,
    ask as ask_cmd,
    atoms_merge as atoms_merge_cmd,
    atoms_split as atoms_split_cmd,
    chunk as chunk_cmd,
    curate as curate_cmd,
    eval as eval_cmd,
    evolve as evolve_cmd,
    extract as extract_cmd,
    ingest as ingest_cmd,
    init as init_cmd,
    museum as museum_cmd,
    query as query_cmd,
    reindex as reindex_cmd,
    ui as ui_cmd,
)

app = typer.Typer(
    name="openacad",
    help=(
        "AI-first scholarly research platform. "
        "A markdown vault of atomic notes + a Claude Code-style agent harness."
    ),
    no_args_is_help=True,
    add_completion=False,
    context_settings={"help_option_names": ["-h", "--help"]},
)


@app.callback()
def _root(
    ctx: typer.Context,
    vault: Path | None = typer.Option(
        None,
        "--vault",
        help="Path to the vault root. Defaults to cwd, then ~/.openacad/default.",
        show_default=False,
    ),
) -> None:
    """Stash the chosen vault path on ``ctx.obj`` for sub-typer callbacks."""
    ctx.ensure_object(dict)
    ctx.obj["vault_path"] = vault


# ── Top-level commands ──────────────────────────────────────────────────────

app.command("init", help="Bootstrap a vault: create .openacad/ + copy shipped agents/skills.")(
    init_cmd.init
)
app.command("reindex", help="Rebuild FTS + embeddings + registry from atoms on disk.")(
    reindex_cmd.reindex
)
app.command("ingest", help="Copy a PDF into the vault sidecar and return its doc-id.")(
    ingest_cmd.ingest
)
app.command("chunk", help="Extract text chunks from an ingested PDF.")(chunk_cmd.chunk)
app.command("extract", help="Run the extractor agent over a doc's chunks → draft atoms.")(
    extract_cmd.extract
)
app.command("curate", help="Interactive HITL loop over pending draft atoms.")(curate_cmd.curate)
app.command("ask", help="Ask the answerer agent a question against the vault.")(ask_cmd.ask)
app.command("evolve", help="Run the meta-evaluator → write proposals to .openacad/agents/proposed/.")(
    evolve_cmd.evolve
)
app.command("eval", help="Run the answerer over the canonical gold question set.")(eval_cmd.eval)
app.command("ui", help="Launch the Next.js playground UI (M4; placeholder for now).")(ui_cmd.ui)
app.command("museum", help="Launch the frozen 9-rung Streamlit tour.")(museum_cmd.museum)


# ── Sub-typer-apps ──────────────────────────────────────────────────────────

# ``openacad atoms split/merge``
atoms_app = typer.Typer(
    name="atoms",
    help="Atom-level operations: split + merge with source-span inheritance.",
    no_args_is_help=True,
)
atoms_app.command("split", help="Split an atom into N parts via $EDITOR.")(atoms_split_cmd.split)
atoms_app.command("merge", help="Merge several atoms into a single unified atom via $EDITOR.")(
    atoms_merge_cmd.merge
)
app.add_typer(atoms_app, name="atoms")

# ``openacad query <subcommand>``
app.add_typer(query_cmd.query_app, name="query")

# ``openacad agents <subcommand>``
app.add_typer(agents_cmd.agents_app, name="agents")


if __name__ == "__main__":
    app()
