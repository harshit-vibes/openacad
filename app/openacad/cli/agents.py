"""``openacad agents`` — list / show / edit / versions / diff / promote."""

from __future__ import annotations

import difflib
import os
import re
import shutil
import subprocess
from pathlib import Path

import typer
from rich.console import Console
from rich.syntax import Syntax
from rich.table import Table

from openacad.cli.vault_helper import get_vault_from_ctx
from openacad.runtime.loader import load_agents

console = Console()

agents_app = typer.Typer(
    name="agents",
    help="Manage agent .md files in the vault sidecar.",
    no_args_is_help=True,
)


@agents_app.callback()
def _agents_root(
    ctx: typer.Context,
    vault: Path | None = typer.Option(
        None,
        "--vault",
        help="Vault path (overrides the value passed on the root command).",
        show_default=False,
    ),
) -> None:
    ctx.ensure_object(dict)
    if vault is not None:
        ctx.obj["vault_path"] = vault


@agents_app.command("list", help="List active agents visible from this vault.")
def cmd_list(
    ctx: typer.Context,
    vault_path: Path | None = typer.Option(None, "--vault", help="Vault path."),
) -> None:
    vault = get_vault_from_ctx(ctx, vault_path)
    agents = load_agents(vault)
    table = Table(title="agents")
    table.add_column("name", style="bold cyan")
    table.add_column("model", style="magenta")
    table.add_column("tools", overflow="fold")
    table.add_column("skills", overflow="fold")
    table.add_column("description", overflow="fold")
    for name in sorted(agents):
        spec = agents[name]
        table.add_row(
            spec.name,
            spec.model,
            ", ".join(spec.tools),
            ", ".join(spec.skills),
            (spec.description or "")[:60],
        )
    console.print(table)
    vault.close()


def _active_path(vault, name: str) -> Path:
    return vault.agents_dir / f"{name}.md"


def _proposed_path(vault, name: str) -> Path:
    return vault.agents_dir / "proposed" / f"{name}.md"


def _versions_dir(vault, name: str) -> Path:
    return vault.agents_dir / "versions" / name


@agents_app.command("show", help="Print the agent .md (sidecar version if present, else shipped).")
def cmd_show(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Agent name (e.g. extractor)."),
    vault_path: Path | None = typer.Option(None, "--vault", help="Vault path."),
) -> None:
    vault = get_vault_from_ctx(ctx, vault_path)
    sidecar = _active_path(vault, name)
    if sidecar.exists():
        text = sidecar.read_text(encoding="utf-8")
        console.print(f"[dim]source: {sidecar}[/dim]")
    else:
        agents = load_agents(vault)
        spec = agents.get(name)
        if spec is None:
            console.print(f"[red]agent not found: {name}[/red]")
            vault.close()
            raise typer.Exit(code=1)
        text = spec.to_markdown()
        console.print(f"[dim]source: shipped (no sidecar copy at {sidecar})[/dim]")
    console.print(Syntax(text, "markdown", theme="ansi_dark", line_numbers=False))
    vault.close()


@agents_app.command("edit", help="Open the sidecar agent .md in $EDITOR (copies shipped on first edit).")
def cmd_edit(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Agent name."),
    vault_path: Path | None = typer.Option(None, "--vault", help="Vault path."),
) -> None:
    vault = get_vault_from_ctx(ctx, vault_path)
    target = _active_path(vault, name)
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        agents = load_agents(vault)
        spec = agents.get(name)
        if spec is None:
            console.print(f"[red]agent not found: {name}[/red]")
            vault.close()
            raise typer.Exit(code=1)
        target.write_text(spec.to_markdown(), encoding="utf-8")
        console.print(f"[dim]seeded sidecar from shipped default: {target}[/dim]")
    editor = os.environ.get("EDITOR", "vi")
    subprocess.call([editor, str(target)])
    console.print(f"[green]saved[/green] {target}")
    vault.close()


@agents_app.command("versions", help="List archived versions of an agent.")
def cmd_versions(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Agent name."),
    vault_path: Path | None = typer.Option(None, "--vault", help="Vault path."),
) -> None:
    vault = get_vault_from_ctx(ctx, vault_path)
    vdir = _versions_dir(vault, name)
    if not vdir.exists():
        console.print(f"[yellow]no versions archived for {name}[/yellow]")
        vault.close()
        return
    table = Table(title=f"versions: {name}")
    table.add_column("version", style="bold cyan")
    table.add_column("path", overflow="fold")
    for v in sorted(vdir.glob("v*.md")):
        table.add_row(v.stem, str(v))
    console.print(table)
    vault.close()


@agents_app.command("diff", help="Diff the active agent vs a pending proposed/ version.")
def cmd_diff(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Agent name."),
    vault_path: Path | None = typer.Option(None, "--vault", help="Vault path."),
) -> None:
    vault = get_vault_from_ctx(ctx, vault_path)
    active = _active_path(vault, name)
    proposed = _proposed_path(vault, name)
    if not proposed.exists():
        console.print(f"[yellow]no proposed/{name}.md — run `openacad evolve` first[/yellow]")
        vault.close()
        raise typer.Exit(code=1)
    a_text = active.read_text(encoding="utf-8").splitlines(keepends=True) if active.exists() else []
    b_text = proposed.read_text(encoding="utf-8").splitlines(keepends=True)
    diff = difflib.unified_diff(
        a_text,
        b_text,
        fromfile=str(active) if active.exists() else "(no active)",
        tofile=str(proposed),
        lineterm="",
    )
    for line in diff:
        if line.startswith("+++") or line.startswith("---"):
            console.print(f"[bold]{line}[/bold]")
        elif line.startswith("+"):
            console.print(f"[green]{line}[/green]")
        elif line.startswith("-"):
            console.print(f"[red]{line}[/red]")
        elif line.startswith("@@"):
            console.print(f"[cyan]{line}[/cyan]")
        else:
            console.print(line)
    vault.close()


def _next_version_number(versions_dir: Path) -> int:
    """Return ``max(v<N>.md) + 1``, or 1 if none exist."""
    if not versions_dir.exists():
        return 1
    nums: list[int] = []
    for p in versions_dir.glob("v*.md"):
        m = re.match(r"^v(\d+)$", p.stem)
        if m:
            nums.append(int(m.group(1)))
    return (max(nums) + 1) if nums else 1


@agents_app.command(
    "promote",
    help="Archive active → versions/<name>/v<N>.md, promote proposed/<name>.md to active.",
)
def cmd_promote(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Agent name."),
    vault_path: Path | None = typer.Option(None, "--vault", help="Vault path."),
) -> None:
    vault = get_vault_from_ctx(ctx, vault_path)
    active = _active_path(vault, name)
    proposed = _proposed_path(vault, name)
    if not proposed.exists():
        console.print(f"[red]no proposed/{name}.md to promote[/red]")
        vault.close()
        raise typer.Exit(code=1)

    versions_dir = _versions_dir(vault, name)
    versions_dir.mkdir(parents=True, exist_ok=True)

    if active.exists():
        v = _next_version_number(versions_dir)
        archived = versions_dir / f"v{v}.md"
        shutil.move(str(active), archived)
        console.print(f"[dim]archived → {archived}[/dim]")

    shutil.move(str(proposed), active)
    console.print(f"[green]promoted[/green] {name} → {active}")
    vault.close()
