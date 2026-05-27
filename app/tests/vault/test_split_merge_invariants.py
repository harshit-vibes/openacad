"""Split / merge invariants.

- **Split**: each child inherits the parent's source(s), unless it
  specifies its own. A child's span on a shared chunk must lie within
  the parent's span (narrower or equal).
- **Merge**: the merged atom's ``sources`` is the union (deduped by
  ``(chunk, span)``) of the parents' sources. The originals are
  archived (``status=archived``), not deleted.
"""

from __future__ import annotations

import pytest

from openacad.vault import AtomicNote, Chunk, Source, Span, Vault


def _make_chunk(vault: Vault, *, chunk_id: str = "c1", text: str = "x" * 40) -> Chunk:
    chunk = Chunk(
        id=chunk_id,
        doc_id="d",
        page=1,
        char_start=0,
        char_end=len(text),
        text=text,
    )
    vault.import_chunks("d", [chunk])
    return chunk


def test_split_marks_parent_superseded(fresh_vault: Vault) -> None:
    parent = AtomicNote(id="parent", type="finding", body="parent body")
    fresh_vault.write(parent)
    fresh_vault.split(
        "parent",
        parts=[
            AtomicNote(id="child-1", type="finding", body="c1"),
            AtomicNote(id="child-2", type="finding", body="c2"),
        ],
    )
    reloaded = fresh_vault.atom("parent")
    assert reloaded is not None
    assert reloaded.status == "superseded"


def test_split_children_inherit_parent_source(fresh_vault: Vault) -> None:
    chunk = _make_chunk(fresh_vault, text="A B C D E F G H I J")
    parent = AtomicNote(
        id="parent",
        type="finding",
        sources=[Source(document="d", chunk=chunk.id, span=Span(start=0, end=20))],
        body="parent",
    )
    fresh_vault.write(parent)

    children = fresh_vault.split(
        "parent",
        parts=[
            AtomicNote(id="c1", type="finding", body="c1"),
            AtomicNote(id="c2", type="finding", body="c2"),
        ],
    )
    for c in children:
        assert c.sources, c.id
        assert c.sources[0].chunk == chunk.id


def test_split_allows_narrower_child_span(fresh_vault: Vault) -> None:
    chunk = _make_chunk(fresh_vault, text="aaa bbb ccc ddd")
    parent = AtomicNote(
        id="parent",
        type="finding",
        sources=[Source(document="d", chunk=chunk.id, span=Span(start=0, end=15))],
        body="parent",
    )
    fresh_vault.write(parent)

    children = fresh_vault.split(
        "parent",
        parts=[
            AtomicNote(
                id="c1",
                type="finding",
                sources=[Source(document="d", chunk=chunk.id, span=Span(start=0, end=3))],
                body="aaa",
            ),
            AtomicNote(
                id="c2",
                type="finding",
                sources=[Source(document="d", chunk=chunk.id, span=Span(start=4, end=7))],
                body="bbb",
            ),
        ],
    )
    assert fresh_vault.source_text(children[0]) == "aaa"
    assert fresh_vault.source_text(children[1]) == "bbb"


def test_split_rejects_child_span_outside_parent(fresh_vault: Vault) -> None:
    chunk = _make_chunk(fresh_vault, text="abcdefghij")
    parent = AtomicNote(
        id="parent",
        type="finding",
        sources=[Source(document="d", chunk=chunk.id, span=Span(start=2, end=8))],
        body="parent",
    )
    fresh_vault.write(parent)
    with pytest.raises(ValueError, match="outside parent"):
        fresh_vault.split(
            "parent",
            parts=[
                AtomicNote(
                    id="c1",
                    type="finding",
                    sources=[Source(document="d", chunk=chunk.id, span=Span(start=0, end=4))],
                    body="abcd",
                ),
            ],
        )


def test_split_rejects_empty_parts_list(fresh_vault: Vault) -> None:
    fresh_vault.write(AtomicNote(id="p", type="claim", body="x"))
    with pytest.raises(ValueError, match="at least one part"):
        fresh_vault.split("p", parts=[])


def test_split_rejects_unknown_atom(fresh_vault: Vault) -> None:
    with pytest.raises(LookupError):
        fresh_vault.split(
            "nope",
            parts=[AtomicNote(id="c", type="claim", body="c")],
        )


def test_merge_archives_parents(fresh_vault: Vault) -> None:
    fresh_vault.write(AtomicNote(id="p1", type="claim", body="one"))
    fresh_vault.write(AtomicNote(id="p2", type="claim", body="two"))
    fresh_vault.merge(["p1", "p2"], body="combined", merged_id="merged")
    assert fresh_vault.atom("p1").status == "archived"
    assert fresh_vault.atom("p2").status == "archived"


def test_merge_unions_sources(fresh_vault: Vault) -> None:
    c1 = _make_chunk(fresh_vault, chunk_id="c1", text="a" * 10)
    c2 = _make_chunk(fresh_vault, chunk_id="c2", text="b" * 10)
    fresh_vault.write(
        AtomicNote(
            id="p1",
            type="finding",
            sources=[Source(document="d", chunk=c1.id, span=Span(start=0, end=5))],
            body="one",
        )
    )
    fresh_vault.write(
        AtomicNote(
            id="p2",
            type="finding",
            sources=[Source(document="d", chunk=c2.id, span=Span(start=0, end=5))],
            body="two",
        )
    )
    merged = fresh_vault.merge(["p1", "p2"], body="combined", merged_id="merged")
    chunks = {s.chunk for s in merged.sources}
    assert chunks == {"c1", "c2"}
    assert merged.force_plural_sources is True


def test_merge_dedupes_identical_source_spans(fresh_vault: Vault) -> None:
    c = _make_chunk(fresh_vault, text="x" * 20)
    fresh_vault.write(
        AtomicNote(
            id="p1",
            type="finding",
            sources=[Source(document="d", chunk=c.id, span=Span(start=0, end=10))],
            body="one",
        )
    )
    fresh_vault.write(
        AtomicNote(
            id="p2",
            type="finding",
            sources=[Source(document="d", chunk=c.id, span=Span(start=0, end=10))],
            body="two",
        )
    )
    merged = fresh_vault.merge(["p1", "p2"], body="combined", merged_id="m")
    assert len(merged.sources) == 1


def test_merge_emits_plural_sources_on_disk(fresh_vault: Vault) -> None:
    _make_chunk(fresh_vault, chunk_id="c1")
    _make_chunk(fresh_vault, chunk_id="c2")
    fresh_vault.write(
        AtomicNote(
            id="p1",
            type="finding",
            sources=[Source(document="d", chunk="c1", span=Span(start=0, end=2))],
            body="one",
        )
    )
    fresh_vault.write(
        AtomicNote(
            id="p2",
            type="finding",
            sources=[Source(document="d", chunk="c2", span=Span(start=0, end=2))],
            body="two",
        )
    )
    fresh_vault.merge(["p1", "p2"], body="combined", merged_id="m")
    md = (fresh_vault.path / "m.md").read_text("utf-8")
    assert "sources:" in md and "\nsource:" not in md


def test_merge_unions_tags(fresh_vault: Vault) -> None:
    fresh_vault.write(AtomicNote(id="p1", type="claim", tags=["a", "b"], body="x"))
    fresh_vault.write(AtomicNote(id="p2", type="claim", tags=["b", "c"], body="y"))
    merged = fresh_vault.merge(["p1", "p2"], body="z", merged_id="m")
    assert sorted(merged.tags) == ["a", "b", "c"]


def test_merge_rejects_empty_list(fresh_vault: Vault) -> None:
    with pytest.raises(ValueError):
        fresh_vault.merge([], body="x")


def test_merge_rejects_unknown_atom(fresh_vault: Vault) -> None:
    with pytest.raises(LookupError):
        fresh_vault.merge(["does-not-exist"], body="x")


def test_split_and_merge_logged_to_activity(fresh_vault: Vault) -> None:
    fresh_vault.write(AtomicNote(id="p1", type="claim", body="x"))
    fresh_vault.write(AtomicNote(id="p2", type="claim", body="y"))
    fresh_vault.merge(["p1", "p2"], body="z", merged_id="m")
    fresh_vault.split(
        "m",
        parts=[
            AtomicNote(id="c1", type="claim", body="c1"),
            AtomicNote(id="c2", type="claim", body="c2"),
        ],
    )

    events = list(fresh_vault.store.read_activity())
    event_types = [e["event"] for e in events]
    assert "atom.merge" in event_types
    assert "atom.split" in event_types
