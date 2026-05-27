"""Full-text search via the vault's FTS5 index."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any

from openacad.runtime.tool_registry import tool

if TYPE_CHECKING:
    from openacad.vault import AtomicNote, Vault


@tool
def search_vault(
    query: Annotated[str, "Keyword or phrase to search atom bodies and titles"],
    top_k: Annotated[int, "Maximum number of results to return"] = 10,
    *,
    vault: "Vault",
) -> list["AtomicNote"]:
    """Full-text search over the vault. Returns up to top_k atoms ranked by FTS relevance."""
    fn: Any = vault.search
    return fn(query, top_k=top_k)
