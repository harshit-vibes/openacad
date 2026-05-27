"""``openacad query`` — sub-typer-app with bash-equivalent help text.

Every command's ``--help`` lists the shell-only equivalent (typically
``rg`` / ``yq``) so the user understands these are conveniences, not magic.

Output default: greppable atom paths (one per line). Use ``--format table``
for the human-friendly view.
"""

from __future__ import annotations

from collections import deque
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from openacad.cli.vault_helper import get_vault_from_ctx
from openacad.vault import AtomicNote, Vault

console = Console()

query_app = typer.Typer(
    name="query",
    help=(
        "Search + traverse atoms in the vault. Most commands have a "
        "shell-only equivalent (rg / yq) — listed under each command's --help."
    ),
    no_args_is_help=True,
)


@query_app.callback()
def _query_root(
    ctx: typer.Context,
    vault: Path | None = typer.Option(
        None,
        "--vault",
        help="Vault path (overrides the value passed on the root command).",
        show_default=False,
    ),
) -> None:
    """Stash the per-sub-typer vault override on ctx.obj."""
    ctx.ensure_object(dict)
    # Per-subcommand --vault overrides root --vault.
    if vault is not None:
        ctx.obj["vault_path"] = vault


# ── Helpers ─────────────────────────────────────────────────────────────────


def _atom_path_str(vault: Vault, atom_id: str) -> str:
    """Return the on-disk path string for an atom id (greppable output)."""
    return str(vault.path / f"{atom_id}.md")


def _emit(vault: Vault, atoms: list[AtomicNote], fmt: str) -> None:
    if fmt == "table":
        if not atoms:
            console.print("[dim](no results)[/dim]")
            return
        table = Table(show_lines=False)
        table.add_column("id", style="bold cyan")
        table.add_column("type", style="magenta")
        table.add_column("status", style="green")
        table.add_column("body preview", overflow="fold")
        for a in atoms:
            preview = a.body.replace("\n", " ")[:80]
            table.add_row(a.id, a.type, a.status, preview)
        console.print(table)
    else:
        # default: one greppable path per line via raw print (no rich markup).
        for a in atoms:
            print(_atom_path_str(vault, a.id))


# ── search ──────────────────────────────────────────────────────────────────


@query_app.command(
    "search",
    help=(
        "FTS5 full-text search over atom bodies + ids + tags.\n\n"
        "Shell equivalent (when you don't need ranking):\n"
        "    rg -l '<keyword>' <vault>/*.md"
    ),
)
def cmd_search(
    ctx: typer.Context,
    keyword: str = typer.Argument(..., help="Keyword or phrase."),
    top_k: int = typer.Option(20, "--top-k", help="Max results."),
    fmt: str = typer.Option("paths", "--format", help="'paths' (greppable) or 'table'."),
    vault_path: Path | None = typer.Option(None, "--vault", help="Vault path."),
) -> None:
    vault = get_vault_from_ctx(ctx, vault_path)
    atoms = vault.search(keyword, top_k=top_k)
    _emit(vault, atoms, fmt)
    vault.close()


# ── semantic ────────────────────────────────────────────────────────────────


@query_app.command(
    "semantic",
    help=(
        "MiniLM-cosine semantic search over atom bodies.\n\n"
        "No shell-only equivalent — embeddings live in .openacad/index/embeddings.npz."
    ),
)
def cmd_semantic(
    ctx: typer.Context,
    phrase: str = typer.Argument(..., help="Phrase to search for semantically."),
    top_k: int = typer.Option(10, "--top-k", help="Max results."),
    fmt: str = typer.Option("paths", "--format", help="'paths' or 'table'."),
    vault_path: Path | None = typer.Option(None, "--vault", help="Vault path."),
) -> None:
    vault = get_vault_from_ctx(ctx, vault_path)
    atoms = vault.semantic(phrase, top_k=top_k)
    _emit(vault, atoms, fmt)
    vault.close()


# ── atoms (filter by frontmatter) ───────────────────────────────────────────


def _eval_where(atom: AtomicNote, predicate: str) -> bool:
    """Evaluate a tiny ``--where`` predicate against an atom.

    Supported forms:
        attr=value          # exact match
        attr!=value         # not-equal
        attr>=value         # numeric / string >=
        attr<=value
        attr>value
        attr<value

    The LHS resolves against:
        - reserved keys: id, type, status, created_at, updated_at
        - tags  (membership: ``tags=poverty`` is true iff "poverty" in tags)
        - any open-vocab attribute in ``atom.attributes``
    """
    for op in ("!=", ">=", "<=", "=", ">", "<"):
        if op in predicate:
            key, value = predicate.split(op, 1)
            key = key.strip()
            value = value.strip()
            actual = _lookup(atom, key)
            return _compare(actual, op, value)
    return True


def _lookup(atom: AtomicNote, key: str):
    if key == "id":
        return atom.id
    if key == "type":
        return atom.type
    if key == "status":
        return atom.status
    if key == "tags":
        return atom.tags
    if key == "created_at":
        return atom.created_at
    if key == "updated_at":
        return atom.updated_at
    return atom.attributes.get(key)


def _compare(actual, op: str, value: str) -> bool:
    # tags is list — membership check for = and !=
    if isinstance(actual, list):
        is_in = value in [str(x) for x in actual]
        if op == "=":
            return is_in
        if op == "!=":
            return not is_in
        return False
    a_str = "" if actual is None else str(actual)
    if op == "=":
        return a_str == value
    if op == "!=":
        return a_str != value
    # Try numeric comparison; fall back to string.
    try:
        a_num = float(a_str)
        v_num = float(value)
        if op == ">=":
            return a_num >= v_num
        if op == "<=":
            return a_num <= v_num
        if op == ">":
            return a_num > v_num
        if op == "<":
            return a_num < v_num
    except ValueError:
        pass
    if op == ">=":
        return a_str >= value
    if op == "<=":
        return a_str <= value
    if op == ">":
        return a_str > value
    if op == "<":
        return a_str < value
    return False


@query_app.command(
    "atoms",
    help=(
        "Filter atoms by frontmatter attributes.\n\n"
        "Repeat ``--where`` for AND-ed predicates. Operators: = != > < >= <=.\n"
        "Shell equivalent (per-file yq):\n"
        "    rg --files <vault> -g '*.md' | xargs -I{} yq -r 'select(.domain==\"poverty\") | input_filename' {}"
    ),
)
def cmd_atoms(
    ctx: typer.Context,
    where: list[str] = typer.Option(
        [],
        "--where",
        help="Predicate (repeatable). e.g. domain=poverty, year>=2020, type=claim.",
    ),
    fmt: str = typer.Option("paths", "--format", help="'paths' or 'table'."),
    vault_path: Path | None = typer.Option(None, "--vault", help="Vault path."),
) -> None:
    vault = get_vault_from_ctx(ctx, vault_path)
    atoms = vault.atoms
    for predicate in where:
        atoms = [a for a in atoms if _eval_where(a, predicate)]
    _emit(vault, atoms, fmt)
    vault.close()


# ── incoming ────────────────────────────────────────────────────────────────


@query_app.command(
    "incoming",
    help=(
        "Atoms whose body wiki-links (or relations) point at <atom-id>.\n\n"
        "Shell equivalent:\n"
        "    rg -l '\\[\\[<atom-id>\\]\\]' <vault>/*.md"
    ),
)
def cmd_incoming(
    ctx: typer.Context,
    atom_id: str = typer.Argument(..., help="Target atom id."),
    fmt: str = typer.Option("paths", "--format", help="'paths' or 'table'."),
    vault_path: Path | None = typer.Option(None, "--vault", help="Vault path."),
) -> None:
    vault = get_vault_from_ctx(ctx, vault_path)
    atoms = vault.incoming(atom_id)
    _emit(vault, atoms, fmt)
    vault.close()


# ── outgoing ────────────────────────────────────────────────────────────────


@query_app.command(
    "outgoing",
    help=(
        "Atoms targeted by <atom-id>'s relations (optionally filtered by --type).\n\n"
        "Shell equivalent:\n"
        "    yq -r '.relations[] | select(.type==\"supports\") | .target' <vault>/<atom-id>.md"
    ),
)
def cmd_outgoing(
    ctx: typer.Context,
    atom_id: str = typer.Argument(..., help="Source atom id."),
    type_filter: str | None = typer.Option(None, "--type", help="Filter by relation type."),
    fmt: str = typer.Option("paths", "--format", help="'paths' or 'table'."),
    vault_path: Path | None = typer.Option(None, "--vault", help="Vault path."),
) -> None:
    vault = get_vault_from_ctx(ctx, vault_path)
    atoms = vault.outgoing(atom_id, type=type_filter)
    _emit(vault, atoms, fmt)
    vault.close()


# ── path (BFS over relations) ───────────────────────────────────────────────


@query_app.command(
    "path",
    help=(
        "Shortest path between two atoms via outgoing relations.\n\n"
        "Shell equivalent: none — graph traversal is the point of this command."
    ),
)
def cmd_path(
    ctx: typer.Context,
    atom_a: str = typer.Argument(..., help="Start atom id."),
    atom_b: str = typer.Argument(..., help="Target atom id."),
    max_hops: int = typer.Option(3, "--max-hops", help="Max BFS depth."),
    fmt: str = typer.Option("paths", "--format", help="'paths' or 'table'."),
    vault_path: Path | None = typer.Option(None, "--vault", help="Vault path."),
) -> None:
    vault = get_vault_from_ctx(ctx, vault_path)
    start = vault.atom(atom_a)
    target = vault.atom(atom_b)
    if start is None:
        console.print(f"[red]start atom not found: {atom_a}[/red]")
        raise typer.Exit(code=1)
    if target is None:
        console.print(f"[red]target atom not found: {atom_b}[/red]")
        raise typer.Exit(code=1)
    if atom_a == atom_b:
        _emit(vault, [start], fmt)
        vault.close()
        return

    # BFS over outgoing relations.
    queue: deque[tuple[str, list[str]]] = deque([(atom_a, [atom_a])])
    visited: set[str] = {atom_a}
    found_path: list[str] | None = None
    while queue:
        node, history = queue.popleft()
        if len(history) - 1 >= max_hops:
            continue
        for neighbour in vault.outgoing(node):
            nid = neighbour.id
            if nid in visited:
                continue
            new_history = history + [nid]
            if nid == atom_b:
                found_path = new_history
                queue.clear()
                break
            visited.add(nid)
            queue.append((nid, new_history))

    if not found_path:
        console.print(f"[yellow]no path within {max_hops} hops[/yellow]")
        raise typer.Exit(code=1)

    atoms = [vault.atom(aid) for aid in found_path]
    atoms = [a for a in atoms if a is not None]
    _emit(vault, atoms, fmt)
    vault.close()


# ── source ──────────────────────────────────────────────────────────────────


@query_app.command(
    "source",
    help=(
        "Print the exact chunk substring referenced by <atom-id>.source.span.\n\n"
        "This is the trust test — the substring must match what the atom claims."
    ),
)
def cmd_source(
    ctx: typer.Context,
    atom_id: str = typer.Argument(..., help="Atom id whose source text to fetch."),
    vault_path: Path | None = typer.Option(None, "--vault", help="Vault path."),
) -> None:
    vault = get_vault_from_ctx(ctx, vault_path)
    atom = vault.atom(atom_id)
    if atom is None:
        console.print(f"[red]atom not found: {atom_id}[/red]")
        raise typer.Exit(code=1)
    if not atom.sources:
        console.print(f"[yellow]atom {atom_id} has no source[/yellow]")
        raise typer.Exit(code=1)
    try:
        text = vault.source_text(atom)
    except Exception as exc:
        console.print(f"[red]could not load source: {exc}[/red]")
        raise typer.Exit(code=1) from exc
    # raw print so the output is greppable / pipe-friendly.
    print(text)
    vault.close()
