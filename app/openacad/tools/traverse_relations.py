"""Multi-hop graph walk over the atom relation graph."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any

from openacad.runtime.tool_registry import tool

if TYPE_CHECKING:
    from openacad.vault import AtomicNote, Vault


@tool
def traverse_relations(
    atom_id: Annotated[str, "Starting atom id"],
    max_hops: Annotated[int, "Maximum number of relation hops to follow"] = 2,
    type: Annotated[
        str | None,
        "Optional relation type filter (e.g. 'supports'). Omit to follow all types.",
    ] = None,
    *,
    vault: "Vault",
) -> list["AtomicNote"]:
    """Breadth-first walk of outgoing relations up to max_hops. Returns the reached atoms."""
    seen: set[str] = {atom_id}
    frontier: list[str] = [atom_id]
    out: list[Any] = []
    outgoing_fn: Any = vault.outgoing
    atom_fn: Any = vault.atom
    for _ in range(max_hops):
        next_frontier: list[str] = []
        for current in frontier:
            neighbours = (
                outgoing_fn(current) if type is None else outgoing_fn(current, type=type)
            )
            for n in neighbours:
                nid = getattr(n, "id", None) or getattr(n, "atom_id", None) or str(n)
                if nid in seen:
                    continue
                seen.add(nid)
                out.append(n)
                next_frontier.append(nid)
        frontier = next_frontier
        if not frontier:
            break
    # If outgoing() returned ids instead of atoms, hydrate them.
    hydrated: list[Any] = []
    for item in out:
        if isinstance(item, str):
            atom = atom_fn(item)
            if atom is not None:
                hydrated.append(atom)
        else:
            hydrated.append(item)
    return hydrated
