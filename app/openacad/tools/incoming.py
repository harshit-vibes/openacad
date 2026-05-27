"""List atoms that point INTO the given atom via wiki-links / relations."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any

from openacad.runtime.tool_registry import tool

if TYPE_CHECKING:
    from openacad.vault import AtomicNote, Vault


@tool
def incoming(
    atom_id: Annotated[str, "Target atom id whose backlinks you want"],
    *,
    vault: "Vault",
) -> list["AtomicNote"]:
    """Return atoms that link to atom_id (wiki-link / relation inverse)."""
    fn: Any = vault.incoming
    return fn(atom_id)
