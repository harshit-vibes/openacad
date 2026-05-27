"""Thin convenience wrapper over :class:`openacad.vault.store.Store` for FTS lookups.

The store does the actual work — this class exists so ``Vault.search()``
has a clean callsite and tests can stub the index in isolation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..store import Store


class FTSIndex:
    def __init__(self, store: Store) -> None:
        self._store = store

    def search(self, query: str, top_k: int = 10) -> list[str]:
        """Return matching atom ids in relevance order."""
        return self._store.search(query, top_k=top_k)


__all__ = ["FTSIndex"]
