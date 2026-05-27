"""Test fixtures for the vault test suite.

All tests use the **hash encoder** for embeddings so they're fast and
deterministic. The encoder is selected via the
``OPENACAD_EMBEDDING_BACKEND=hash`` env var which is set at session
start; tests can also pass ``encoder=hash_encode`` directly.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

import pytest

# Make sure the hash encoder is selected for *all* tests in this
# suite — keeps things fast and offline.
os.environ.setdefault("OPENACAD_EMBEDDING_BACKEND", "hash")

from openacad.vault import (  # noqa: E402  (env var must be set first)
    AtomicNote,
    Chunk,
    Relation,
    Source,
    Span,
    Vault,
)


@pytest.fixture
def fresh_vault(tmp_path: Path) -> Iterator[Vault]:
    """A brand-new vault with no atoms and no chunks."""
    v = Vault(tmp_path / "vault")
    try:
        yield v
    finally:
        v.close()


@pytest.fixture
def sample_atom() -> AtomicNote:
    """A minimal but realistic atom."""
    return AtomicNote(
        id="atom-foo",
        type="claim",
        aliases=["foo-atom"],
        created_at="2026-05-27T10:00:00Z",
        updated_at="2026-05-27T10:00:00Z",
        status="active",
        tags=["sdg-1", "poverty"],
        attributes={"domain": "poverty", "evidence": "strong"},
        body="An atom about poverty",
    )


@pytest.fixture
def sourced_atom() -> tuple[AtomicNote, Chunk]:
    """An atom paired with its referenced chunk for span-fidelity tests."""
    chunk_text = (
        "Sustainable Development Goal 1 seeks to halve, by 2030, the "
        "proportion of people living in extreme poverty, defined as "
        "those subsisting on under $2.15 per day."
    )
    chunk = Chunk(
        id="ch1",
        doc_id="doc-sdg",
        page=1,
        char_start=0,
        char_end=len(chunk_text),
        text=chunk_text,
    )
    # Pick a span that points to the substring "extreme poverty".
    needle = "extreme poverty"
    start = chunk_text.index(needle)
    end = start + len(needle)
    atom = AtomicNote(
        id="atom-extreme-poverty",
        type="finding",
        body="Atom referencing extreme poverty",
        sources=[Source(document="doc-sdg", chunk="ch1", span=Span(start=start, end=end))],
    )
    return atom, chunk


@pytest.fixture
def linked_pair() -> tuple[AtomicNote, AtomicNote]:
    """Two atoms — one referencing the other via wiki-link + relation."""
    a = AtomicNote(id="atom-a", type="claim", body="Foundation claim")
    b = AtomicNote(
        id="atom-b",
        type="claim",
        body="Extends [[atom-a]]",
        relations=[Relation(type="extends", target="atom-a")],
    )
    return a, b
