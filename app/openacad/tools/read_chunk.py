"""Read a chunk by id (text + page + offsets)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any

from openacad.runtime.tool_registry import tool

if TYPE_CHECKING:
    from openacad.vault import Chunk, Vault


@tool
def read_chunk(
    chunk_id: Annotated[str, "Chunk identifier (e.g. 'chunk-fa72')"],
    *,
    vault: "Vault",
) -> "Chunk | None":
    """Return the chunk with this id (text + page + char offsets), or None if missing."""
    fn: Any = getattr(vault, "chunk", None) or getattr(vault, "read_chunk", None)
    if fn is None:
        raise AttributeError("vault has no chunk/read_chunk method")
    return fn(chunk_id)
