"""Fetch a single atom by id."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any

from openacad.runtime.tool_registry import tool

if TYPE_CHECKING:
    from openacad.vault import AtomicNote, Vault


@tool
def get_atom(
    atom_id: Annotated[str, "Atom identifier (filename without .md, e.g. 'atom-fa72')"],
    *,
    vault: "Vault",
) -> "AtomicNote | None":
    """Return the atom with this id, or None if no such atom exists in the vault."""
    fn: Any = vault.atom
    return fn(atom_id)
