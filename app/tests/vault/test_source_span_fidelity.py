"""The trust test: ``vault.source_text(atom)`` returns the EXACT substring.

No whitespace normalisation, no canonical form rewriting. If the atom
claims its source is ``chunk.text[1234:1456]``, that's what comes back.
This is the property scholars verify when accepting / auditing atoms.
"""

from __future__ import annotations

import pytest

from openacad.vault import AtomicNote, Chunk, Source, Span, Vault


def _atom_for_span(
    chunk: Chunk,
    *,
    needle: str,
    atom_id: str = "atom-span",
    body: str | None = None,
) -> AtomicNote:
    start = chunk.text.index(needle)
    end = start + len(needle)
    return AtomicNote(
        id=atom_id,
        type="finding",
        sources=[
            Source(
                document=chunk.doc_id,
                chunk=chunk.id,
                span=Span(start=start, end=end),
            )
        ],
        body=body or f"Atom citing {atom_id}",
    )


def test_source_text_returns_exact_substring(fresh_vault: Vault) -> None:
    chunk = Chunk(
        id="c1",
        doc_id="d1",
        page=1,
        char_start=0,
        char_end=50,
        text="The quick brown fox jumps over the lazy dog every day",
    )
    fresh_vault.import_chunks("d1", [chunk])
    atom = _atom_for_span(chunk, needle="brown fox")
    fresh_vault.write(atom)
    assert fresh_vault.source_text(atom) == "brown fox"


def test_source_text_preserves_whitespace_and_punctuation(fresh_vault: Vault) -> None:
    chunk_text = "Sentence one.  Sentence two!  Sentence-three?"
    chunk = Chunk(id="c", doc_id="d", page=1, char_start=0, char_end=len(chunk_text), text=chunk_text)
    fresh_vault.import_chunks("d", [chunk])
    atom = _atom_for_span(chunk, needle="Sentence one.  Sentence two!")
    fresh_vault.write(atom)
    assert fresh_vault.source_text(atom) == "Sentence one.  Sentence two!"


def test_source_text_unicode(fresh_vault: Vault) -> None:
    chunk_text = "Krishna's teaching to Arjuna — 18 chapters, ~700 verses."
    chunk = Chunk(id="c", doc_id="d", page=1, char_start=0, char_end=len(chunk_text), text=chunk_text)
    fresh_vault.import_chunks("d", [chunk])
    atom = _atom_for_span(chunk, needle="18 chapters, ~700 verses")
    fresh_vault.write(atom)
    assert fresh_vault.source_text(atom) == "18 chapters, ~700 verses"


def test_source_text_empty_for_atom_without_source(fresh_vault: Vault) -> None:
    atom = AtomicNote(id="atom-no-source", type="insight", body="An idea")
    fresh_vault.write(atom)
    assert fresh_vault.source_text(atom) == ""


def test_source_text_raises_when_chunk_missing(fresh_vault: Vault) -> None:
    atom = AtomicNote(
        id="atom-ghost",
        type="claim",
        sources=[Source(document="d", chunk="missing-chunk", span=Span(start=0, end=5))],
        body="claim",
    )
    fresh_vault.write(atom)
    with pytest.raises(LookupError, match="missing-chunk"):
        fresh_vault.source_text(atom)


def test_source_text_multi_source_joined_with_separator(fresh_vault: Vault) -> None:
    chunks = [
        Chunk(id="c1", doc_id="d1", page=1, char_start=0, char_end=11, text="First quote"),
        Chunk(id="c2", doc_id="d2", page=1, char_start=0, char_end=12, text="Second quote"),
    ]
    fresh_vault.import_chunks("d1", [chunks[0]])
    fresh_vault.import_chunks("d2", [chunks[1]])
    atom = AtomicNote(
        id="atom-merged",
        type="finding",
        sources=[
            Source(document="d1", chunk="c1", span=Span(start=0, end=5)),
            Source(document="d2", chunk="c2", span=Span(start=0, end=6)),
        ],
        force_plural_sources=True,
        body="merged finding",
    )
    fresh_vault.write(atom)
    assert fresh_vault.source_text(atom) == "First\n\n---\n\nSecond"


def test_chunk_by_id_returns_chunk(fresh_vault: Vault) -> None:
    chunk = Chunk(id="c1", doc_id="d", page=1, char_start=0, char_end=4, text="text")
    fresh_vault.import_chunks("d", [chunk])
    fetched = fresh_vault.chunk_by_id("c1")
    assert fetched is not None
    assert fetched.text == "text"


def test_chunk_by_id_returns_none_when_missing(fresh_vault: Vault) -> None:
    assert fresh_vault.chunk_by_id("does-not-exist") is None


def test_source_span_inside_chunk_bounds(sourced_atom) -> None:
    """The fixture sourced atom's span maps to 'extreme poverty'."""
    atom, chunk = sourced_atom
    src = atom.sources[0]
    assert chunk.text[src.span.start : src.span.end] == "extreme poverty"


def test_source_text_after_roundtrip(fresh_vault: Vault) -> None:
    """Span fidelity survives write → read → roundtrip."""
    chunk = Chunk(
        id="c1",
        doc_id="d",
        page=1,
        char_start=0,
        char_end=40,
        text="An entire chunk of academic prose here.",
    )
    fresh_vault.import_chunks("d", [chunk])
    atom = _atom_for_span(chunk, needle="academic prose")
    fresh_vault.write(atom)

    # Re-open as a fresh Vault instance (forcing read from disk)
    fresh_vault.close()
    from openacad.vault import Vault as VaultClass

    v2 = VaultClass(fresh_vault.path)
    try:
        # We need to re-add the chunk too; production code persists
        # via .openacad/chunks/*.jsonl which import_chunks already wrote.
        reloaded = v2.atom("atom-span")
        assert reloaded is not None
        assert v2.source_text(reloaded) == "academic prose"
    finally:
        v2.close()
