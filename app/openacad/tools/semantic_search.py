"""Semantic (embedding) search via the vault's MiniLM index."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any

from openacad.runtime.tool_registry import tool

if TYPE_CHECKING:
    from openacad.vault import AtomicNote, Vault


@tool
def semantic_search(
    query: Annotated[str, "Phrase or sentence to match against atom embeddings"],
    top_k: Annotated[int, "Maximum number of results to return"] = 10,
    *,
    vault: "Vault",
) -> list["AtomicNote"]:
    """Cosine-similarity search over atom embeddings. Use for paraphrase / concept match."""
    fn: Any = vault.semantic
    return fn(query, top_k=top_k)
