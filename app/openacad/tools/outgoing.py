"""List atoms that the given atom points OUT to via wiki-links / relations."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any

from openacad.runtime.tool_registry import tool

if TYPE_CHECKING:
    from openacad.vault import AtomicNote, Vault


@tool
def outgoing(
    atom_id: Annotated[str, "Source atom id whose outgoing links you want"],
    type: Annotated[
        str | None,
        "Optional relation type filter (e.g. 'supports', 'extends'). Omit for all relations.",
    ] = None,
    *,
    vault: "Vault",
) -> list["AtomicNote"]:
    """Return atoms reachable from atom_id via outgoing relations, optionally filtered by type."""
    fn: Any = vault.outgoing
    if type is None:
        return fn(atom_id)
    return fn(atom_id, type=type)
