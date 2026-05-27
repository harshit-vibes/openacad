"""Programmatic split/merge tests via the Vault API.

We deliberately skip the ``$EDITOR``-driven CLI path (that's a UX test, hard
to drive in unittest land) and test the underlying ``vault.split`` /
``vault.merge`` plumbing the CLI delegates to.
"""

from __future__ import annotations

from pathlib import Path

from openacad.vault import AtomicNote, Source, Span, Vault


def _fresh_vault(tmp_path: Path) -> Vault:
    return Vault(tmp_path / "v", create=True)


def test_split_inherits_parent_source(tmp_path: Path):
    vault = _fresh_vault(tmp_path)
    parent = AtomicNote(
        id="atom-parent",
        type="claim",
        body="Parent claim A. Parent claim B.",
        sources=[
            Source(
                document="doc1",
                chunk="chunk1",
                span=Span(start=0, end=100),
                page=1,
            )
        ],
    )
    vault.write(parent)

    children = [
        AtomicNote(id="atom-parent-pt1", type="claim", body="Parent claim A."),
        AtomicNote(id="atom-parent-pt2", type="claim", body="Parent claim B."),
    ]
    written = vault.split("atom-parent", children, agent="test")
    assert len(written) == 2
    for child in written:
        assert len(child.sources) == 1
        assert child.sources[0].document == "doc1"
        assert child.sources[0].chunk == "chunk1"

    # Parent should now be superseded but still on disk.
    parent_after = vault.atom("atom-parent")
    assert parent_after is not None
    assert parent_after.status == "superseded"
    vault.close()


def test_merge_unions_sources(tmp_path: Path):
    vault = _fresh_vault(tmp_path)
    a = AtomicNote(
        id="atom-a",
        type="claim",
        body="Claim A.",
        sources=[
            Source(document="doc1", chunk="chunk1", span=Span(start=0, end=20))
        ],
    )
    b = AtomicNote(
        id="atom-b",
        type="claim",
        body="Claim B.",
        sources=[
            Source(document="doc2", chunk="chunk2", span=Span(start=50, end=80))
        ],
    )
    vault.write(a)
    vault.write(b)

    merged = vault.merge(
        ["atom-a", "atom-b"],
        body="Combined claim A + B.",
        type="claim",
        merged_id="atom-merged",
        agent="test",
    )
    assert merged.id == "atom-merged"
    assert len(merged.sources) == 2
    # Parents should be archived.
    for pid in ("atom-a", "atom-b"):
        p = vault.atom(pid)
        assert p is not None
        assert p.status == "archived"
    vault.close()


def test_split_marker_parser():
    """The CLI split body-parser splits on the marker line."""
    from openacad.cli.atoms_split import _split_body

    body = "first part\n\n--- split here ---\n\nsecond part\n\n--- split here ---\n\nthird"
    parts = _split_body(body)
    assert parts == ["first part", "second part", "third"]
