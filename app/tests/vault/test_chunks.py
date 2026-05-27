"""Chunk model + JSONL I/O + PDF chunking."""

from __future__ import annotations

from pathlib import Path

import pytest

from openacad.vault import Chunk, Vault, chunk_pdf, read_chunks, write_chunks
from openacad.vault.chunks import ChunkStore, _split_text_sliding_window

SAMPLE_PDF = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "sources"
    / "sdg-briefing-ch01-front-matter.pdf"
)


def test_chunk_requires_non_negative_offsets() -> None:
    with pytest.raises(Exception):  # noqa: B017
        Chunk(id="c", doc_id="d", char_start=-1, char_end=0, text="")


def test_chunk_rejects_inverted_offsets() -> None:
    with pytest.raises(ValueError):
        Chunk(id="c", doc_id="d", char_start=10, char_end=5, text="x" * 5)


def test_chunk_slice_returns_substring() -> None:
    c = Chunk(id="c", doc_id="d", char_start=0, char_end=10, text="0123456789")
    assert c.slice(3, 7) == "3456"


def test_write_and_read_chunks_roundtrip(tmp_path: Path) -> None:
    chunks = [
        Chunk(id=f"c{i}", doc_id="d", char_start=i * 10, char_end=i * 10 + 5, text="hello")
        for i in range(3)
    ]
    out = tmp_path / "chunks.jsonl"
    write_chunks(out, chunks)
    reloaded = read_chunks(out)
    assert [c.id for c in reloaded] == ["c0", "c1", "c2"]
    assert reloaded[1].text == "hello"


def test_read_chunks_returns_empty_for_missing(tmp_path: Path) -> None:
    assert read_chunks(tmp_path / "nope.jsonl") == []


def test_write_chunks_creates_parent_dir(tmp_path: Path) -> None:
    out = tmp_path / "nested" / "subdir" / "chunks.jsonl"
    c = Chunk(id="c", doc_id="d", char_start=0, char_end=1, text="x")
    write_chunks(out, [c])
    assert out.exists()


def test_split_sliding_window_handles_short_text() -> None:
    pages = [(1, "Short content.")]
    chunks = list(_split_text_sliding_window(pages, target_tokens=100, overlap=10))
    assert len(chunks) == 1
    _, _, char_start, char_end, text = chunks[0]
    assert text == "Short content."


def test_split_sliding_window_handles_empty_pages() -> None:
    chunks = list(_split_text_sliding_window([], target_tokens=100, overlap=10))
    assert chunks == []


def test_split_sliding_window_handles_only_whitespace() -> None:
    chunks = list(
        _split_text_sliding_window([(1, "   "), (2, "")], target_tokens=100, overlap=10)
    )
    # whitespace-only chunk should be filtered
    assert chunks == []


def test_split_sliding_window_paginates_long_text() -> None:
    long = "Sentence one. " * 200  # ~2800 chars
    pages = [(1, long)]
    chunks = list(_split_text_sliding_window(pages, target_tokens=100, overlap=20))
    assert len(chunks) > 1
    # Coverage of first and last char
    assert chunks[0][2] == 0  # char_start of first chunk
    assert chunks[-1][3] >= len(long) - 1


def test_split_sliding_window_tracks_page_boundaries() -> None:
    pages = [(1, "Page one text."), (2, "Page two text.")]
    chunks = list(_split_text_sliding_window(pages, target_tokens=100, overlap=10))
    # Should produce one chunk covering both pages
    page_starts = {c[0] for c in chunks}
    page_ends = {c[1] for c in chunks}
    assert 1 in page_starts
    # The last chunk should end on page 2
    assert 2 in page_ends


@pytest.mark.skipif(not SAMPLE_PDF.exists(), reason="sample PDF not present")
def test_chunk_pdf_extracts_chunks() -> None:
    chunks = chunk_pdf(SAMPLE_PDF, target_tokens=200, overlap=20)
    assert len(chunks) > 0
    # Every chunk has non-empty text and valid offsets
    for c in chunks:
        assert c.text.strip()
        assert c.char_end > c.char_start
        assert c.doc_id == SAMPLE_PDF.stem


@pytest.mark.skipif(not SAMPLE_PDF.exists(), reason="sample PDF not present")
def test_chunk_pdf_assigns_unique_ids() -> None:
    chunks = chunk_pdf(SAMPLE_PDF, target_tokens=200, overlap=20)
    assert len({c.id for c in chunks}) == len(chunks)


def test_chunk_store_indexes_by_id_and_doc() -> None:
    store = ChunkStore()
    chunks = [
        Chunk(id="c1", doc_id="d", char_start=0, char_end=5, text="hello"),
        Chunk(id="c2", doc_id="d", char_start=5, char_end=11, text="world"),
        Chunk(id="c3", doc_id="other", char_start=0, char_end=5, text="other"),
    ]
    store.extend(chunks)
    assert len(store) == 3
    assert "c1" in store
    assert "missing" not in store
    assert store.get("c1") is not None
    assert store.get("missing") is None
    assert len(store.for_doc("d")) == 2
    assert len(store.for_doc("other")) == 1


@pytest.mark.skipif(not SAMPLE_PDF.exists(), reason="sample PDF not present")
def test_vault_ingest_and_chunk(tmp_path: Path) -> None:
    v = Vault(tmp_path / "v")
    try:
        doc_id = v.ingest(SAMPLE_PDF)
        assert (v.sidecar / "documents" / f"{doc_id}.pdf").exists()
        chunks = v.chunk(doc_id, target_tokens=200, overlap=20)
        assert len(chunks) > 0
        # Subsequent reads pick up the chunks
        first_chunk = chunks[0]
        assert v.chunk_by_id(first_chunk.id) is not None
    finally:
        v.close()


def test_vault_ingest_missing_pdf_raises(tmp_path: Path) -> None:
    v = Vault(tmp_path / "v")
    try:
        with pytest.raises(FileNotFoundError):
            v.ingest(tmp_path / "does-not-exist.pdf")
    finally:
        v.close()


def test_vault_chunk_before_ingest_raises(tmp_path: Path) -> None:
    v = Vault(tmp_path / "v")
    try:
        with pytest.raises(FileNotFoundError):
            v.chunk("never-ingested")
    finally:
        v.close()


def test_chunk_text_length_mismatch_allowed() -> None:
    """``len(text) != char_end - char_start`` is permitted (different coord systems)."""
    # Should not raise — the model allows the divergence with a docstring note.
    c = Chunk(id="c", doc_id="d", char_start=0, char_end=100, text="short")
    assert c.text == "short"
