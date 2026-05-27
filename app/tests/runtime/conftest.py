"""Stub Vault for M2 tests — M1's real Vault is still in flight.

This stub implements only the methods the runtime + tools call. It mirrors the
expected M1 interface but stores everything in memory so tests don't touch disk.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest


@dataclass
class StubAtom:
    """Minimal atom shape for tests — id + body + relations + source span."""

    id: str
    body: str = ""
    relations: list[dict] = field(default_factory=list)
    chunk_id: str | None = None
    span_start: int | None = None
    span_end: int | None = None


@dataclass
class StubChunk:
    """Minimal chunk shape for tests."""

    id: str
    text: str
    page: int = 1


class StubVault:
    """In-memory Vault for unit tests.

    Implements the subset of the M1 interface that the runtime + tools consume:
      atoms, atom(id), search(q), semantic(q), incoming(id), outgoing(id, type=),
      source_text(atom), chunk(id), path.
    """

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or Path("/tmp/stub-vault")
        self._atoms: dict[str, StubAtom] = {}
        self._chunks: dict[str, StubChunk] = {}

    # ── read API ─────────────────────────────────────────────────────────

    @property
    def atoms(self) -> list[StubAtom]:
        return list(self._atoms.values())

    def atom(self, atom_id: str) -> StubAtom | None:
        return self._atoms.get(atom_id)

    def search(self, query: str, top_k: int = 10) -> list[StubAtom]:
        q = query.lower()
        hits = [a for a in self._atoms.values() if q in a.body.lower() or q in a.id.lower()]
        return hits[:top_k]

    def semantic(self, query: str, top_k: int = 10) -> list[StubAtom]:
        # Stub: same as FTS for test purposes.
        return self.search(query, top_k=top_k)

    def incoming(self, atom_id: str) -> list[StubAtom]:
        return [
            a
            for a in self._atoms.values()
            if any(r.get("target") == atom_id for r in a.relations)
        ]

    def outgoing(self, atom_id: str, *, type: str | None = None) -> list[StubAtom]:
        a = self._atoms.get(atom_id)
        if a is None:
            return []
        out: list[StubAtom] = []
        for r in a.relations:
            if type is not None and r.get("type") != type:
                continue
            target = self._atoms.get(r.get("target", ""))
            if target is not None:
                out.append(target)
        return out

    def source_text(self, atom: Any) -> str:
        if atom is None:
            return ""
        chunk_id = getattr(atom, "chunk_id", None)
        s = getattr(atom, "span_start", None)
        e = getattr(atom, "span_end", None)
        if not chunk_id or s is None or e is None:
            return ""
        chunk = self._chunks.get(chunk_id)
        if chunk is None:
            return ""
        return chunk.text[s:e]

    def chunk(self, chunk_id: str) -> StubChunk | None:
        return self._chunks.get(chunk_id)

    # ── helpers used by tests to seed data ──────────────────────────────

    def add_atom(self, atom: StubAtom) -> None:
        self._atoms[atom.id] = atom

    def add_chunk(self, chunk: StubChunk) -> None:
        self._chunks[chunk.id] = chunk


@pytest.fixture
def stub_vault(tmp_path: Path) -> StubVault:
    """A populated stub vault with two atoms and one chunk."""
    v = StubVault(path=tmp_path)
    v.add_chunk(StubChunk(id="chunk-1", text="Hello world. The SDG targets 2030."))
    v.add_atom(
        StubAtom(
            id="atom-a",
            body="Hello world",
            chunk_id="chunk-1",
            span_start=0,
            span_end=11,
            relations=[{"type": "supports", "target": "atom-b"}],
        )
    )
    v.add_atom(
        StubAtom(
            id="atom-b",
            body="SDG targets 2030",
            chunk_id="chunk-1",
            span_start=17,
            span_end=33,
        )
    )
    return v
