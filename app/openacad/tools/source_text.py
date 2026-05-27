"""Return the exact source-text substring an atom was extracted from."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any

from openacad.runtime.tool_registry import tool

if TYPE_CHECKING:
    from openacad.vault import Vault


@tool
def source_text(
    atom_id: Annotated[str, "Atom id whose source-span text you want"],
    *,
    vault: "Vault",
) -> str:
    """Return chunk.text[span.start:span.end] for atom_id — the EXACT substring with no
    normalization. Empty string if the atom has no source span."""
    atom_fn: Any = vault.atom
    src_fn: Any = vault.source_text
    atom = atom_fn(atom_id)
    if atom is None:
        return ""
    return src_fn(atom) or ""
