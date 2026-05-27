"""FTS + embeddings index stay in sync with every Vault mutation.

Reads against a stale index would silently return wrong results, so
this is one of the load-bearing invariants of the Vault.
"""

from __future__ import annotations

from openacad.vault import AtomicNote, Vault


def test_write_adds_to_fts(fresh_vault: Vault) -> None:
    fresh_vault.write(AtomicNote(id="a1", type="claim", body="poverty in rural India"))
    assert "a1" in fresh_vault.store.search("poverty")


def test_write_adds_to_embeddings(fresh_vault: Vault) -> None:
    fresh_vault.write(AtomicNote(id="a1", type="claim", body="hello world"))
    assert "a1" in fresh_vault.embeddings


def test_delete_removes_from_both(fresh_vault: Vault) -> None:
    fresh_vault.write(AtomicNote(id="a1", type="claim", body="text"))
    assert "a1" in fresh_vault.embeddings
    assert "a1" in fresh_vault.store.search("text")
    fresh_vault.delete("a1")
    assert "a1" not in fresh_vault.embeddings
    assert "a1" not in fresh_vault.store.search("text")


def test_overwrite_replaces_old_body_in_fts(fresh_vault: Vault) -> None:
    fresh_vault.write(AtomicNote(id="a1", type="claim", body="alpha"))
    assert "a1" in fresh_vault.store.search("alpha")
    fresh_vault.write(AtomicNote(id="a1", type="claim", body="beta"))
    assert "a1" not in fresh_vault.store.search("alpha")
    assert "a1" in fresh_vault.store.search("beta")


def test_overwrite_does_not_duplicate_embedding(fresh_vault: Vault) -> None:
    fresh_vault.write(AtomicNote(id="a1", type="claim", body="x"))
    fresh_vault.write(AtomicNote(id="a1", type="claim", body="y"))
    assert len(fresh_vault.embeddings) == 1


def test_search_returns_atoms_not_just_ids(fresh_vault: Vault) -> None:
    fresh_vault.write(
        AtomicNote(id="a1", type="claim", body="quantum mechanics is weird")
    )
    results = fresh_vault.search("quantum")
    assert len(results) == 1
    assert results[0].id == "a1"
    assert results[0].body == "quantum mechanics is weird"


def test_search_returns_empty_on_no_match(fresh_vault: Vault) -> None:
    fresh_vault.write(AtomicNote(id="a1", type="claim", body="foo"))
    assert fresh_vault.search("nonexistent") == []


def test_search_tolerates_punctuation_in_query(fresh_vault: Vault) -> None:
    fresh_vault.write(AtomicNote(id="a1", type="claim", body="poverty matters"))
    # FTS5 raises on unbalanced quotes; the fallback should still work.
    assert "a1" in fresh_vault.store.search('"poverty')


def test_search_top_k_limits_results(fresh_vault: Vault) -> None:
    for i in range(5):
        fresh_vault.write(AtomicNote(id=f"a{i}", type="claim", body="match this text"))
    res = fresh_vault.search("match", top_k=2)
    assert len(res) <= 2


def test_search_via_tags(fresh_vault: Vault) -> None:
    fresh_vault.write(
        AtomicNote(id="a1", type="claim", tags=["sdg-7", "energy"], body="generic")
    )
    assert "a1" in fresh_vault.store.search("sdg-7")


def test_semantic_returns_results(fresh_vault: Vault) -> None:
    fresh_vault.write(AtomicNote(id="a1", type="claim", body="rural poverty"))
    fresh_vault.write(AtomicNote(id="a2", type="claim", body="urban infrastructure"))
    results = fresh_vault.semantic("poverty", top_k=5)
    assert len(results) > 0


def test_reindex_rebuilds_from_disk(fresh_vault: Vault) -> None:
    fresh_vault.write(AtomicNote(id="a1", type="claim", body="alpha"))
    fresh_vault.write(AtomicNote(id="a2", type="claim", body="beta"))

    # Sabotage the FTS table behind the Vault's back to simulate drift
    fresh_vault.store.conn.execute("DELETE FROM atoms_fts")
    assert fresh_vault.store.search("alpha") == []

    fresh_vault.reindex()
    assert "a1" in fresh_vault.store.search("alpha")
    assert "a2" in fresh_vault.store.search("beta")


def test_embeddings_persist_across_vault_instances(tmp_path) -> None:
    v1 = Vault(tmp_path / "v")
    try:
        v1.write(AtomicNote(id="a1", type="claim", body="hello"))
    finally:
        v1.close()

    v2 = Vault(tmp_path / "v")
    try:
        assert "a1" in v2.embeddings
    finally:
        v2.close()


def test_fts_persists_across_vault_instances(tmp_path) -> None:
    v1 = Vault(tmp_path / "v")
    try:
        v1.write(AtomicNote(id="a1", type="claim", body="searchable text"))
    finally:
        v1.close()

    v2 = Vault(tmp_path / "v")
    try:
        assert "a1" in v2.store.search("searchable")
    finally:
        v2.close()


def test_incoming_outgoing_traversal(fresh_vault: Vault) -> None:
    from openacad.vault import Relation

    fresh_vault.write(AtomicNote(id="a", type="claim", body="parent"))
    fresh_vault.write(
        AtomicNote(
            id="b",
            type="claim",
            body="extends [[a]]",
            relations=[Relation(type="extends", target="a")],
        )
    )
    fresh_vault.write(
        AtomicNote(
            id="c",
            type="claim",
            body="supports [[a]]",
            relations=[Relation(type="supports", target="a")],
        )
    )
    incoming = {atom.id for atom in fresh_vault.incoming("a")}
    assert incoming == {"b", "c"}
    out_b = {atom.id for atom in fresh_vault.outgoing("b")}
    assert out_b == {"a"}
    # Filter by type
    out_supports = {atom.id for atom in fresh_vault.outgoing("c", type="supports")}
    assert out_supports == {"a"}
    out_extends = {atom.id for atom in fresh_vault.outgoing("c", type="extends")}
    assert out_extends == set()


def test_outgoing_unknown_atom_returns_empty(fresh_vault: Vault) -> None:
    assert fresh_vault.outgoing("nope") == []


def test_atom_lookup_caches_results(fresh_vault: Vault) -> None:
    fresh_vault.write(AtomicNote(id="a1", type="claim", body="x"))
    a = fresh_vault.atom("a1")
    a_again = fresh_vault.atom("a1")
    assert a is a_again  # same object identity (cached)


def test_atom_returns_none_for_missing(fresh_vault: Vault) -> None:
    assert fresh_vault.atom("missing-atom-id") is None


def test_activity_log_records_write(fresh_vault: Vault) -> None:
    fresh_vault.write(AtomicNote(id="a1", type="claim", body="x"))
    events = list(fresh_vault.store.read_activity())
    assert any(e["event"] == "atom.write" and e["atom_id"] == "a1" for e in events)


def test_vault_context_manager(tmp_path) -> None:
    with Vault(tmp_path / "v") as v:
        v.write(AtomicNote(id="a1", type="claim", body="x"))
    # After exit, sidecar files exist
    assert (tmp_path / "v" / ".openacad" / "index" / "embeddings.npz").exists()


def test_vault_create_false_rejects_missing_dir(tmp_path) -> None:
    import pytest as _pytest

    from openacad.vault import Vault as VaultClass

    with _pytest.raises(FileNotFoundError):
        VaultClass(tmp_path / "no-such-vault", create=False)


def test_vault_paths_exposed(fresh_vault: Vault) -> None:
    """The path accessors used by M2 (agent loader) return real dirs."""
    assert fresh_vault.agents_dir.exists()
    assert fresh_vault.skills_dir.exists()
    assert fresh_vault.drafts_dir.exists()
    assert fresh_vault.documents_dir.exists()
    assert fresh_vault.chunks_dir.exists()


def test_merge_default_merged_id_works(fresh_vault: Vault) -> None:
    fresh_vault.write(AtomicNote(id="p1", type="claim", body="x"))
    fresh_vault.write(AtomicNote(id="p2", type="claim", body="y"))
    merged = fresh_vault.merge(["p1", "p2"], body="z")
    # default merged_id is "merged-p1-p2"
    assert merged.id.startswith("merged-")


def test_merge_with_extra_tags(fresh_vault: Vault) -> None:
    fresh_vault.write(AtomicNote(id="p", type="claim", tags=["x"], body="x"))
    merged = fresh_vault.merge(["p"], body="z", merged_id="m", tags=["y"])
    assert sorted(merged.tags) == ["x", "y"]


def test_delete_unknown_atom_no_raise(fresh_vault: Vault) -> None:
    fresh_vault.delete("never-existed")  # should be a quiet no-op
