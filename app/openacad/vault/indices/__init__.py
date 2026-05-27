"""Index backends for the vault.

- ``fts.py``  — SQLite FTS5 full-text search (thin wrapper over ``store.py``)
- ``embeddings.py`` — sentence-transformers MiniLM embeddings persisted to ``.npz``
"""

from .embeddings import EmbeddingIndex
from .fts import FTSIndex

__all__ = ["FTSIndex", "EmbeddingIndex"]
