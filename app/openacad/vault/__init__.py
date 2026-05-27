"""openacad.vault — the engineering IP.

A markdown-on-disk atomic-note vault with:

- Round-trip-pure markdown serialization
- Wiki-link / relations reconciliation invariant
- Char-offset source span fidelity
- Auto-promoting attribute + relation registry
- Atomic write that updates FTS + embeddings together
- Split / merge with source-span inheritance

Quick start::

    from openacad.vault import Vault, AtomicNote, Source, Span, Relation

    vault = Vault("/path/to/my-vault")
    vault.write(AtomicNote(
        id="atom-foo",
        type="claim",
        body="Climate target requires action per [[atom-bar]]",
        relations=[Relation(type="supports", target="atom-bar")],
    ))
"""

from .atoms import AtomicNote, Relation, Source, Span
from .chunks import Chunk, ChunkStore, chunk_pdf, read_chunks, write_chunks
from .indices import EmbeddingIndex, FTSIndex
from .markdown import (
    WikiLinkMismatch,
    append_missing_wiki_links,
    check_wiki_link_invariant,
    extract_wiki_link_targets,
)
from .registry import AttributeDef, Registry, RelationDef
from .store import Store
from .vault import SIDECAR_DIR, Vault

__all__ = [
    # core
    "Vault",
    "AtomicNote",
    "Chunk",
    "Source",
    "Span",
    "Relation",
    # subsystems
    "Registry",
    "AttributeDef",
    "RelationDef",
    "Store",
    "FTSIndex",
    "EmbeddingIndex",
    "ChunkStore",
    # IO helpers
    "chunk_pdf",
    "read_chunks",
    "write_chunks",
    # markdown helpers
    "WikiLinkMismatch",
    "extract_wiki_link_targets",
    "check_wiki_link_invariant",
    "append_missing_wiki_links",
    # constants
    "SIDECAR_DIR",
]
