"""Vault resolution + shared helpers for the new CLI.

Every command (except ``openacad init``) calls :func:`resolve_vault` to obtain
a ``Vault`` pointing at:

1. The path supplied via ``--vault`` on the command line, if given.
2. The current working directory, if it already has a ``.openacad/`` sidecar.
3. ``~/.openacad/default``, if it already has a sidecar.
4. Otherwise: emit a clean error telling the user to run ``openacad init``.

The Vault constructor defaults to ``create=True`` — we deliberately pass
``create=False`` so a typo doesn't silently scaffold a fresh vault under
``~/Documents/openacad/some-typo/``.
"""

from __future__ import annotations

from pathlib import Path

import typer

from openacad.vault import SIDECAR_DIR, Vault


def _has_sidecar(path: Path) -> bool:
    return (path / SIDECAR_DIR).is_dir()


def resolve_vault(path: Path | None) -> Vault:
    """Return a ``Vault`` for the chosen path, or exit cleanly if none resolves.

    Never creates a vault — callers that want to bootstrap a vault (``init``)
    should construct ``Vault(path, create=True)`` directly.
    """
    if path is not None:
        candidate = Path(path).expanduser().resolve()
        if not candidate.exists():
            typer.echo(f"vault path does not exist: {candidate}", err=True)
            raise typer.Exit(code=1)
        if not _has_sidecar(candidate):
            typer.echo(
                f"no .openacad/ sidecar at {candidate} — run `openacad init {candidate}` first",
                err=True,
            )
            raise typer.Exit(code=1)
        return Vault(candidate, create=False)

    cwd = Path.cwd().resolve()
    if _has_sidecar(cwd):
        return Vault(cwd, create=False)

    default = (Path.home() / ".openacad" / "default").resolve()
    if _has_sidecar(default):
        return Vault(default, create=False)

    typer.echo(
        "no vault found. Run `openacad init` (or pass --vault <path>) first.",
        err=True,
    )
    raise typer.Exit(code=1)


def get_vault_from_ctx(ctx: typer.Context, override: Path | None = None) -> Vault:
    """Pull the resolved Vault off ``ctx.obj`` (set by each sub-typer callback).

    ``override`` (a per-leaf ``--vault`` option, if supplied) wins over both
    the sub-typer's stash and the root's stash.
    """
    if override is not None:
        return resolve_vault(override)
    if ctx.obj is None or "vault_path" not in ctx.obj:
        return resolve_vault(None)
    return resolve_vault(ctx.obj["vault_path"])


__all__ = ["resolve_vault", "get_vault_from_ctx"]
