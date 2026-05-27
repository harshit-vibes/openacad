"""``openacad init`` — bootstrap a vault directory + sidecar with shipped defaults."""

from __future__ import annotations

import shutil
from importlib import resources
from pathlib import Path

import typer
from rich.console import Console

from openacad.vault import SIDECAR_DIR, Vault

console = Console()


def _copy_shipped_agents(dest_dir: Path) -> int:
    """Copy shipped ``openacad/agents/*.md`` into ``<dest>/agents/``. Returns count."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    n = 0
    agents_root = resources.files("openacad.agents")
    for entry in agents_root.iterdir():
        # Skip Python infrastructure + subdirectories (only flat .md ships as agents).
        if not entry.is_file():
            continue
        name = entry.name
        if not name.endswith(".md"):
            continue
        target = dest_dir / name
        if target.exists():
            continue
        with resources.as_file(entry) as src_path:
            shutil.copy2(src_path, target)
        n += 1
    return n


def _copy_shipped_skills(dest_dir: Path) -> int:
    """Copy shipped skill bundles into ``<dest>/skills/<name>/SKILL.md``."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    n = 0
    skills_root = resources.files("openacad.skills")
    for entry in skills_root.iterdir():
        if not entry.is_dir():
            continue
        name = entry.name
        if name.startswith("_") or name.startswith("."):
            continue
        skill_md = entry / "SKILL.md"
        # ``Traversable.exists`` is available in 3.11+ via the joinpath result; guard anyway.
        try:
            if not skill_md.is_file():
                continue
        except Exception:
            continue
        target_dir = dest_dir / name
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / "SKILL.md"
        if target.exists():
            continue
        with resources.as_file(skill_md) as src_path:
            shutil.copy2(src_path, target)
        n += 1
    return n


def init(
    vault_dir: Path = typer.Argument(
        Path.cwd(),
        help="Vault directory to create (defaults to cwd).",
    ),
) -> None:
    """Create a vault at ``vault_dir`` with ``.openacad/`` sidecar + shipped agents/skills.

    Idempotent: re-running on an existing vault leaves files in place and just
    reports what was already there.
    """
    target = Path(vault_dir).expanduser().resolve()
    fresh = not (target / SIDECAR_DIR).exists()

    vault = Vault(target, create=True)
    n_agents = _copy_shipped_agents(vault.agents_dir)
    n_skills = _copy_shipped_skills(vault.skills_dir)

    if fresh:
        console.print(f"[green]initialised vault[/green] at {vault.path}")
    else:
        console.print(f"[yellow]vault already exists[/yellow] at {vault.path}")
    console.print(f"  shipped agents copied: [bold]{n_agents}[/bold]")
    console.print(f"  shipped skills copied: [bold]{n_skills}[/bold]")
    console.print(f"  sidecar at: {vault.sidecar}")
    vault.close()
