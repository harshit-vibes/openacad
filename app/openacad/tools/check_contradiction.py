"""Check whether two atoms are connected by a `contradicts` relation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any

from openacad.runtime.tool_registry import tool

if TYPE_CHECKING:
    from openacad.vault import Vault


@tool
def check_contradiction(
    atom_a: Annotated[str, "First atom id"],
    atom_b: Annotated[str, "Second atom id"],
    *,
    vault: "Vault",
) -> bool:
    """Return True if atom_a → contradicts → atom_b OR atom_b → contradicts → atom_a."""
    outgoing_fn: Any = vault.outgoing
    try:
        a_targets = outgoing_fn(atom_a, type="contradicts")
    except TypeError:
        a_targets = outgoing_fn(atom_a)
    for t in a_targets or []:
        tid = getattr(t, "id", None) or getattr(t, "atom_id", None) or str(t)
        if tid == atom_b:
            return True
    try:
        b_targets = outgoing_fn(atom_b, type="contradicts")
    except TypeError:
        b_targets = outgoing_fn(atom_b)
    for t in b_targets or []:
        tid = getattr(t, "id", None) or getattr(t, "atom_id", None) or str(t)
        if tid == atom_a:
            return True
    return False
