"""Chunk model + JSONL I/O + PDF chunking.

A ``Chunk`` is a contiguous slice of a source document's text. Char
offsets are inside ``chunk.text`` (not the parent document) — atoms
reference substrings via ``Source.span``. PDF chunking uses ``pymupdf``
to extract text page-by-page, then a sliding-window splitter measured
in approximate tokens (1 token ≈ 4 chars by default).
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Chunk(BaseModel):
    """A piece of text extracted from a document."""

    model_config = ConfigDict(extra="forbid")

    id: str
    doc_id: str
    page: int = 1  # first page where this chunk's text appears (1-indexed)
    char_start: int = Field(ge=0)  # offset inside the *document* (not the chunk)
    char_end: int = Field(ge=0)
    text: str
    page_end: int | None = None  # last page (multi-page chunks)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)
        if self.char_end < self.char_start:
            raise ValueError("char_end must be >= char_start")
        if len(self.text) != self.char_end - self.char_start:
            # We allow this — sometimes char offsets refer to the
            # *original* document text and chunk.text is the extracted
            # form. The Source.span fidelity test uses chunk.text only.
            pass

    def slice(self, start: int, end: int) -> str:
        """Return the substring referenced by a ``Source.span`` (inside ``self.text``)."""
        return self.text[start:end]


# ---------------------------------------------------------------------------
# JSONL I/O
# ---------------------------------------------------------------------------


def read_chunks(path: str | Path) -> list[Chunk]:
    """Read a JSONL file of chunks."""
    p = Path(path)
    if not p.exists():
        return []
    out: list[Chunk] = []
    with p.open("r", encoding="utf-8") as fp:
        for line in fp:
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            out.append(Chunk(**data))
    return out


def write_chunks(path: str | Path, chunks: Iterable[Chunk]) -> None:
    """Atomically write a JSONL file of chunks (overwrites)."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as fp:
        for chunk in chunks:
            fp.write(chunk.model_dump_json())
            fp.write("\n")
    tmp.replace(p)


# ---------------------------------------------------------------------------
# PDF chunking
# ---------------------------------------------------------------------------


def _approx_tokens(text: str) -> int:
    """Approximate token count using the 4-chars-per-token heuristic."""
    return max(1, len(text) // 4)


def _split_text_sliding_window(
    pages: list[tuple[int, str]],
    *,
    target_tokens: int,
    overlap: int,
) -> Iterator[tuple[int, int | None, int, int, str]]:
    """Yield ``(page_start, page_end, char_start, char_end, text)`` chunks.

    Concatenates the pages into one string (with a single ``\\n``
    separator), tracks per-character page indices, then slides a window
    sized in ~tokens (here, characters / 4). Overlap is in tokens as well.
    """
    if not pages:
        return
    sep = "\n"
    parts: list[str] = []
    char_to_page: list[int] = []  # parallel array: char index → page number
    for page_num, page_text in pages:
        if parts:
            parts.append(sep)
            char_to_page.extend([page_num] * len(sep))
        parts.append(page_text)
        char_to_page.extend([page_num] * len(page_text))
    full = "".join(parts)
    if not full:
        return

    # Convert token sizes to char sizes (4-char ≈ 1 token heuristic)
    window_chars = max(target_tokens * 4, 200)
    step_chars = max(window_chars - overlap * 4, 1)

    pos = 0
    n = len(full)
    while pos < n:
        end = min(pos + window_chars, n)
        # Try to snap to a sentence/paragraph boundary near `end`
        if end < n:
            window_view = full[pos:end]
            # Prefer a paragraph break, then sentence
            for needle in ("\n\n", ". ", "\n"):
                idx = window_view.rfind(needle)
                if idx > window_chars // 2:  # only snap if not too far back
                    end = pos + idx + len(needle)
                    break
        chunk_text = full[pos:end]
        if chunk_text.strip():
            page_start = char_to_page[pos]
            page_end_idx = min(end - 1, len(char_to_page) - 1)
            page_end = char_to_page[page_end_idx]
            yield (page_start, page_end, pos, end, chunk_text)
        if end == n:
            break
        pos = max(end - overlap * 4, pos + step_chars)


def _read_pdf_pages(pdf_path: Path) -> list[tuple[int, str]]:
    """Return ``[(page_number, text), ...]`` using ``pymupdf``."""
    import pymupdf  # type: ignore[import-not-found]

    pages: list[tuple[int, str]] = []
    with pymupdf.open(pdf_path) as doc:
        for i, page in enumerate(doc, start=1):
            text = page.get_text("text")
            pages.append((i, text))
    return pages


def chunk_pdf(
    pdf_path: str | Path,
    *,
    doc_id: str | None = None,
    target_tokens: int = 400,
    overlap: int = 50,
) -> list[Chunk]:
    """Extract chunks from a PDF.

    Each chunk records its char span inside the concatenated document
    text. ``Chunk.text`` is the chunk's own substring — atoms reference
    further sub-substrings via ``Source.span`` (relative to ``chunk.text``).
    """
    pdf_path = Path(pdf_path)
    if doc_id is None:
        doc_id = pdf_path.stem
    pages = _read_pdf_pages(pdf_path)
    chunks: list[Chunk] = []
    for ordinal, (page_start, page_end, char_start, char_end, text) in enumerate(
        _split_text_sliding_window(
            pages,
            target_tokens=target_tokens,
            overlap=overlap,
        )
    ):
        chunks.append(
            Chunk(
                id=f"{doc_id}-chunk-{ordinal:04d}",
                doc_id=doc_id,
                page=page_start,
                page_end=page_end if page_end != page_start else None,
                char_start=char_start,
                char_end=char_end,
                text=text,
            )
        )
    return chunks


# ---------------------------------------------------------------------------
# in-memory chunk store (used by Vault for source-text lookup)
# ---------------------------------------------------------------------------


class ChunkStore:
    """Indexed view over ``(doc_id, chunk_id) -> Chunk``.

    The Vault hydrates one of these from the ``.openacad/chunks/*.jsonl``
    files so ``vault.source_text(atom)`` is fast.
    """

    def __init__(self) -> None:
        self._by_id: dict[str, Chunk] = {}
        self._by_doc: dict[str, list[Chunk]] = {}

    def add(self, chunk: Chunk) -> None:
        self._by_id[chunk.id] = chunk
        self._by_doc.setdefault(chunk.doc_id, []).append(chunk)

    def extend(self, chunks: Iterable[Chunk]) -> None:
        for c in chunks:
            self.add(c)

    def get(self, chunk_id: str) -> Chunk | None:
        return self._by_id.get(chunk_id)

    def for_doc(self, doc_id: str) -> list[Chunk]:
        return list(self._by_doc.get(doc_id, []))

    def __len__(self) -> int:
        return len(self._by_id)

    def __contains__(self, chunk_id: object) -> bool:
        return isinstance(chunk_id, str) and chunk_id in self._by_id


__all__ = [
    "Chunk",
    "ChunkStore",
    "read_chunks",
    "write_chunks",
    "chunk_pdf",
]
