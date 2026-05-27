"""Each tool function is testable in isolation given a stub Vault."""

from __future__ import annotations

import sys
from pathlib import Path

# Re-use the runtime conftest's StubVault.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "runtime"))
from conftest import StubAtom, StubChunk, StubVault  # type: ignore  # noqa: E402

from openacad.tools.check_contradiction import check_contradiction  # noqa: E402
from openacad.tools.get_atom import get_atom  # noqa: E402
from openacad.tools.incoming import incoming  # noqa: E402
from openacad.tools.outgoing import outgoing  # noqa: E402
from openacad.tools.propose_atom import propose_atom  # noqa: E402
from openacad.tools.read_chunk import read_chunk  # noqa: E402
from openacad.tools.search_vault import search_vault  # noqa: E402
from openacad.tools.semantic_search import semantic_search  # noqa: E402
from openacad.tools.source_text import source_text  # noqa: E402
from openacad.tools.traverse_relations import traverse_relations  # noqa: E402


def _populated_vault(tmp_path: Path) -> StubVault:
    v = StubVault(path=tmp_path)
    v.add_chunk(StubChunk(id="chunk-1", text="Hello world. The SDG targets 2030."))
    v.add_atom(
        StubAtom(
            id="atom-a",
            body="Hello world claim",
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
            relations=[{"type": "contradicts", "target": "atom-c"}],
        )
    )
    v.add_atom(StubAtom(id="atom-c", body="Unrelated atom"))
    return v


def test_search_vault(tmp_path: Path) -> None:
    v = _populated_vault(tmp_path)
    hits = search_vault("hello", vault=v)
    assert any(a.id == "atom-a" for a in hits)


def test_semantic_search(tmp_path: Path) -> None:
    v = _populated_vault(tmp_path)
    hits = semantic_search("SDG", vault=v)
    assert any(a.id == "atom-b" for a in hits)


def test_get_atom(tmp_path: Path) -> None:
    v = _populated_vault(tmp_path)
    a = get_atom("atom-a", vault=v)
    assert a is not None and a.id == "atom-a"
    assert get_atom("does-not-exist", vault=v) is None


def test_incoming(tmp_path: Path) -> None:
    v = _populated_vault(tmp_path)
    back = incoming("atom-b", vault=v)
    assert any(a.id == "atom-a" for a in back)


def test_outgoing_with_type_filter(tmp_path: Path) -> None:
    v = _populated_vault(tmp_path)
    out = outgoing("atom-a", type="supports", vault=v)
    assert any(a.id == "atom-b" for a in out)
    none_match = outgoing("atom-a", type="contradicts", vault=v)
    assert none_match == []


def test_traverse_relations(tmp_path: Path) -> None:
    v = _populated_vault(tmp_path)
    walked = traverse_relations("atom-a", max_hops=2, vault=v)
    ids = {a.id for a in walked}
    assert "atom-b" in ids
    assert "atom-c" in ids


def test_source_text(tmp_path: Path) -> None:
    v = _populated_vault(tmp_path)
    assert source_text("atom-a", vault=v) == "Hello world"
    assert source_text("atom-b", vault=v) == "SDG targets 2030"
    assert source_text("atom-c", vault=v) == ""  # no span on atom-c
    assert source_text("does-not-exist", vault=v) == ""


def test_read_chunk(tmp_path: Path) -> None:
    v = _populated_vault(tmp_path)
    chunk = read_chunk("chunk-1", vault=v)
    assert chunk is not None and chunk.text.startswith("Hello world")
    assert read_chunk("nope", vault=v) is None


def test_check_contradiction(tmp_path: Path) -> None:
    v = _populated_vault(tmp_path)
    assert check_contradiction("atom-b", "atom-c", vault=v) is True
    # symmetric:
    assert check_contradiction("atom-c", "atom-b", vault=v) is True
    assert check_contradiction("atom-a", "atom-b", vault=v) is False


def test_propose_atom_writes_draft(tmp_path: Path) -> None:
    v = StubVault(path=tmp_path)
    result = propose_atom(
        body="The SDG 1 target halves extreme poverty by 2030.",
        type="claim",
        tags=["poverty", "sdg-1"],
        doc_id="doi-test",
        chunk_id="chunk-1",
        span_start=0,
        span_end=49,
        page=5,
        vault=v,
    )
    assert "path" in result
    draft = Path(result["path"])
    assert draft.exists()
    text = draft.read_text(encoding="utf-8")
    assert "SDG 1 target" in text
    assert "claim" in text
    # Lives under <vault.path>/.openacad/drafts/<doc-id>/
    assert ".openacad/drafts/doi-test" in str(draft)
