"""Tests for the wiki-link reconciliation invariant.

Strict rule, enforced on every ``Vault.write()``:

    set([[wiki-links]] in body) == set(relations[].target)

The invariant exists so the graph is self-consistent — you can trust
either the frontmatter relations OR the body wiki-links and they agree.
"""

from __future__ import annotations

import pytest

from openacad.vault import AtomicNote, Relation, Vault, WikiLinkMismatch
from openacad.vault.markdown import (
    append_missing_wiki_links,
    extract_wiki_link_targets,
)


def test_extract_wiki_link_targets_basic() -> None:
    body = "See [[a]] and [[b|alias]] and [[c]]"
    assert extract_wiki_link_targets(body) == ["a", "b", "c"]


def test_extract_wiki_link_targets_deduplicates() -> None:
    body = "[[a]] [[a]] [[b]] [[a]]"
    assert extract_wiki_link_targets(body) == ["a", "b"]


def test_extract_wiki_link_targets_ignores_singles() -> None:
    body = "Not a link [single brackets] or [[ unbalanced"
    assert extract_wiki_link_targets(body) == []


def test_check_invariant_passes_when_sets_match() -> None:
    from openacad.vault.markdown import check_wiki_link_invariant

    body = "See [[a]] and [[b]]"
    targets = ["a", "b"]
    check_wiki_link_invariant(body, targets)  # no raise


def test_check_invariant_raises_when_body_has_extra_link() -> None:
    from openacad.vault.markdown import check_wiki_link_invariant

    with pytest.raises(WikiLinkMismatch) as exc_info:
        check_wiki_link_invariant("See [[a]] and [[b]]", ["a"])
    assert exc_info.value.only_in_body == ["b"]
    assert exc_info.value.only_in_relations == []


def test_check_invariant_raises_when_relations_have_extra() -> None:
    from openacad.vault.markdown import check_wiki_link_invariant

    with pytest.raises(WikiLinkMismatch) as exc_info:
        check_wiki_link_invariant("See [[a]]", ["a", "b"])
    assert exc_info.value.only_in_relations == ["b"]


def test_check_invariant_handles_wrapped_targets() -> None:
    """``relations[].target`` may be either ``"x"`` or ``"[[x]]"`` — we normalise."""
    from openacad.vault.markdown import check_wiki_link_invariant

    check_wiki_link_invariant("See [[a]]", ["[[a]]"])  # no raise


def test_append_missing_links_appends_footer() -> None:
    body = "Existing text"
    out = append_missing_wiki_links(body, ["a", "b"])
    assert "[[a]]" in out and "[[b]]" in out
    assert out.startswith("Existing text")


def test_append_missing_links_no_change_when_satisfied() -> None:
    body = "See [[a]] and [[b]]"
    assert append_missing_wiki_links(body, ["a", "b"]) == body


def test_write_rejects_atom_with_dangling_body_link(fresh_vault: Vault) -> None:
    atom = AtomicNote(
        id="atom-bad",
        type="claim",
        body="Refers to [[undeclared]]",
        # ↑ but no Relation
    )
    with pytest.raises(WikiLinkMismatch) as exc_info:
        fresh_vault.write(atom)
    assert "undeclared" in str(exc_info.value)


def test_write_rejects_atom_with_dangling_relation(fresh_vault: Vault) -> None:
    atom = AtomicNote(
        id="atom-bad",
        type="claim",
        body="Plain body with no links",
        relations=[Relation(type="supports", target="dangling-atom")],
    )
    with pytest.raises(WikiLinkMismatch):
        fresh_vault.write(atom)


def test_write_with_reconcile_appends_missing_link(fresh_vault: Vault) -> None:
    atom = AtomicNote(
        id="atom-ok",
        type="claim",
        body="Plain body with no links",
        relations=[Relation(type="supports", target="other-atom")],
    )
    written = fresh_vault.write(atom, reconcile=True)
    assert "[[other-atom]]" in written.body
    # And it's persisted on disk
    on_disk = (fresh_vault.path / "atom-ok.md").read_text()
    assert "[[other-atom]]" in on_disk


def test_write_then_read_preserves_invariant(fresh_vault: Vault) -> None:
    """Every atom on disk satisfies the invariant — sanity test."""
    atom = AtomicNote(
        id="atom-a",
        type="claim",
        body="body",
    )
    fresh_vault.write(atom)
    other = AtomicNote(
        id="atom-b",
        type="claim",
        body="See [[atom-a]]",
        relations=[Relation(type="extends", target="atom-a")],
    )
    fresh_vault.write(other)

    for a in fresh_vault.atoms:
        body_targets = set(extract_wiki_link_targets(a.body))
        rel_targets = {r.target for r in a.relations}
        assert body_targets == rel_targets, a.id


def test_reconcile_idempotent(fresh_vault: Vault) -> None:
    atom = AtomicNote(
        id="atom-x",
        type="claim",
        body="text",
        relations=[Relation(type="r", target="atom-y")],
    )
    written_once = fresh_vault.write(atom, reconcile=True)
    written_twice = fresh_vault.write(written_once)  # no reconcile needed now
    assert written_once.body == written_twice.body
