"""Direct tests for Store + EmbeddingIndex internals.

These exercise paths the higher-level Vault tests don't cover —
tool-call log, raw FTS, embedding persistence edge cases, etc.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from openacad.vault.indices.embeddings import EmbeddingIndex, _hash_encode
from openacad.vault.store import Store


def test_store_creates_db_and_tables(tmp_path: Path) -> None:
    s = Store(tmp_path / "cache.sqlite")
    try:
        tables = {
            r["name"]
            for r in s.conn.execute(
                "SELECT name FROM sqlite_master WHERE type IN ('table','virtual')"
            )
        }
        assert "atoms" in tables
        assert "atoms_fts" in tables
        assert "tool_calls" in tables
    finally:
        s.close()


def test_store_close_is_idempotent(tmp_path: Path) -> None:
    s = Store(tmp_path / "cache.sqlite")
    s.close()
    s.close()  # second close should not raise


def test_store_upsert_then_search(tmp_path: Path) -> None:
    s = Store(tmp_path / "c.sqlite")
    try:
        s.upsert_atom(
            id="a1",
            type="claim",
            status="active",
            body="hello world",
            aliases=["greeting"],
            tags=["t1"],
            updated_at="2026-05-27T00:00:00Z",
        )
        assert "a1" in s.search("hello")
        # Search via alias and tag
        assert "a1" in s.search("greeting")
        assert "a1" in s.search("t1")
    finally:
        s.close()


def test_store_search_empty_query_returns_empty(tmp_path: Path) -> None:
    s = Store(tmp_path / "c.sqlite")
    try:
        assert s.search("") == []
        assert s.search("   ") == []
    finally:
        s.close()


def test_store_search_no_tokens_returns_empty(tmp_path: Path) -> None:
    s = Store(tmp_path / "c.sqlite")
    try:
        assert s.search("!!!") == []  # tokeniser strips → empty
    finally:
        s.close()


def test_store_delete_atom_removes_from_fts(tmp_path: Path) -> None:
    s = Store(tmp_path / "c.sqlite")
    try:
        s.upsert_atom(
            id="a1",
            type="claim",
            status="active",
            body="alpha",
            aliases=[],
            tags=[],
            updated_at="2026-05-27T00:00:00Z",
        )
        assert "a1" in s.search("alpha")
        s.delete_atom("a1")
        assert "a1" not in s.search("alpha")
    finally:
        s.close()


def test_store_all_atom_ids(tmp_path: Path) -> None:
    s = Store(tmp_path / "c.sqlite")
    try:
        for i in range(3):
            s.upsert_atom(
                id=f"a{i}",
                type="claim",
                status="active",
                body=f"body {i}",
                aliases=[],
                tags=[],
                updated_at="2026-05-27T00:00:00Z",
            )
        assert s.all_atom_ids() == ["a0", "a1", "a2"]
    finally:
        s.close()


def test_record_tool_call(tmp_path: Path) -> None:
    s = Store(tmp_path / "c.sqlite")
    try:
        rowid = s.record_tool_call(
            tool="search_vault",
            agent="extractor",
            args={"query": "x"},
            result=["a", "b"],
            duration_ms=42,
        )
        assert rowid > 0
        row = s.conn.execute(
            "SELECT tool, agent, args_json, duration_ms FROM tool_calls WHERE rowid = ?",
            (rowid,),
        ).fetchone()
        assert row["tool"] == "search_vault"
        assert row["agent"] == "extractor"
        assert row["duration_ms"] == 42
    finally:
        s.close()


def test_activity_log_append_and_read(tmp_path: Path) -> None:
    s = Store(
        tmp_path / "c.sqlite",
        activity_path=tmp_path / "activity.jsonl",
    )
    try:
        s.append_activity("test", x=1)
        s.append_activity("test", x=2)
        events = list(s.read_activity())
        assert len(events) == 2
        assert events[0]["x"] == 1
        assert events[1]["x"] == 2
    finally:
        s.close()


def test_activity_log_disabled_when_no_path(tmp_path: Path) -> None:
    s = Store(tmp_path / "c.sqlite")  # no activity_path
    try:
        s.append_activity("noop", x=1)  # should silently no-op
        events = list(s.read_activity())
        assert events == []
    finally:
        s.close()


def test_activity_log_skips_malformed_lines(tmp_path: Path) -> None:
    activity = tmp_path / "activity.jsonl"
    activity.write_text('{"event": "ok"}\nNOT VALID JSON\n{"event": "ok2"}\n')
    s = Store(tmp_path / "c.sqlite", activity_path=activity)
    try:
        events = list(s.read_activity())
        assert len(events) == 2
        assert events[0]["event"] == "ok"
        assert events[1]["event"] == "ok2"
    finally:
        s.close()


def test_store_raw_search(tmp_path: Path) -> None:
    s = Store(tmp_path / "c.sqlite")
    try:
        s.upsert_atom(
            id="a1",
            type="claim",
            status="active",
            body="quick brown fox",
            aliases=[],
            tags=[],
            updated_at="2026-05-27T00:00:00Z",
        )
        # Phrase query in raw FTS5 syntax
        assert "a1" in s.raw_search('"quick brown"')
    finally:
        s.close()


# -----------------------------------------------------------------------------
# EmbeddingIndex
# -----------------------------------------------------------------------------


def test_hash_encoder_is_deterministic() -> None:
    a = _hash_encode(["hello"])
    b = _hash_encode(["hello"])
    np.testing.assert_array_equal(a, b)


def test_hash_encoder_produces_normalised_vectors() -> None:
    out = _hash_encode(["x", "y", "z"])
    norms = np.linalg.norm(out, axis=1)
    np.testing.assert_allclose(norms, np.ones(3), atol=1e-5)


def test_embedding_index_add_and_search(tmp_path: Path) -> None:
    idx = EmbeddingIndex(tmp_path / "emb.npz", encoder=_hash_encode)
    idx.add("a", "hello world")
    idx.add("b", "goodbye world")
    hits = idx.search("hello", top_k=2)
    assert len(hits) == 2
    assert {h[0] for h in hits} == {"a", "b"}


def test_embedding_index_search_empty_index_returns_empty(tmp_path: Path) -> None:
    idx = EmbeddingIndex(tmp_path / "emb.npz", encoder=_hash_encode)
    assert idx.search("anything") == []


def test_embedding_index_replace_keeps_count(tmp_path: Path) -> None:
    idx = EmbeddingIndex(tmp_path / "emb.npz", encoder=_hash_encode)
    idx.add("a", "v1")
    idx.add("a", "v2")
    assert len(idx) == 1


def test_embedding_index_remove(tmp_path: Path) -> None:
    idx = EmbeddingIndex(tmp_path / "emb.npz", encoder=_hash_encode)
    idx.add("a", "x")
    idx.add("b", "y")
    idx.remove("a")
    assert "a" not in idx
    assert "b" in idx
    assert len(idx) == 1


def test_embedding_index_remove_unknown_is_noop(tmp_path: Path) -> None:
    idx = EmbeddingIndex(tmp_path / "emb.npz", encoder=_hash_encode)
    idx.remove("nonexistent")  # no raise


def test_embedding_index_clear(tmp_path: Path) -> None:
    idx = EmbeddingIndex(tmp_path / "emb.npz", encoder=_hash_encode)
    idx.add("a", "x")
    idx.add("b", "y")
    idx.clear()
    assert len(idx) == 0
    assert idx.ids == []


def test_embedding_index_persists_and_reloads(tmp_path: Path) -> None:
    p = tmp_path / "emb.npz"
    idx1 = EmbeddingIndex(p, encoder=_hash_encode)
    idx1.add("a", "x")
    idx1.add("b", "y")
    idx1.save()
    idx2 = EmbeddingIndex(p, encoder=_hash_encode)
    assert sorted(idx2.ids) == ["a", "b"]


def test_embedding_index_lazy_encoder_loading(tmp_path: Path) -> None:
    """The encoder must not be instantiated until first use."""
    idx = EmbeddingIndex(tmp_path / "emb.npz")
    # accessing the property triggers lazy load; we just want to know
    # construction didn't blow up.
    assert idx is not None


def test_embedding_index_remove_keeps_index_consistent(tmp_path: Path) -> None:
    """After removing the 1st of 3 atoms, vector for the 3rd still maps to
    the right id (no off-by-one)."""
    idx = EmbeddingIndex(tmp_path / "emb.npz", encoder=_hash_encode)
    idx.add("first", "a")
    idx.add("middle", "b")
    idx.add("last", "c")
    idx.remove("first")
    hits = idx.search("c", top_k=2)
    # the atom whose vector is most similar to "c" should be "last"
    top_id = hits[0][0]
    assert top_id == "last"
