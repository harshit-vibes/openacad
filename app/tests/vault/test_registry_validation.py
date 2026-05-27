"""Registry observation, validation, and auto-promotion tests."""

from __future__ import annotations

from openacad.vault import AtomicNote, Relation, Vault
from openacad.vault.registry import PROMOTION_THRESHOLD, Registry


def test_observe_records_new_attribute() -> None:
    reg = Registry()
    atom = AtomicNote(id="a1", type="claim", attributes={"domain": "poverty"}, body="x")
    reg.observe(atom)
    assert "domain" in reg.attributes
    assert reg.attributes["domain"].uses == 1
    assert "str" in reg.attributes["domain"].types


def test_observe_increments_existing_attribute() -> None:
    reg = Registry()
    for i in range(3):
        reg.observe(
            AtomicNote(id=f"a{i}", type="claim", attributes={"domain": "x"}, body="x")
        )
    assert reg.attributes["domain"].uses == 3


def test_attribute_promoted_after_threshold_distinct_atoms() -> None:
    reg = Registry()
    for i in range(PROMOTION_THRESHOLD):
        reg.observe(
            AtomicNote(id=f"a{i}", type="claim", attributes={"era": "modern"}, body="x")
        )
    assert reg.attributes["era"].is_promoted is True
    assert "era" in reg.promoted_attributes()


def test_attribute_not_promoted_below_threshold() -> None:
    reg = Registry()
    reg.observe(AtomicNote(id="a1", type="claim", attributes={"x": 1}, body="x"))
    assert reg.attributes["x"].is_promoted is False
    assert "x" not in reg.promoted_attributes()


def test_promoted_attribute_warns_on_type_change() -> None:
    reg = Registry()
    for i in range(PROMOTION_THRESHOLD):
        reg.observe(
            AtomicNote(id=f"a{i}", type="claim", attributes={"k": "v"}, body="x")
        )
    # Now introduce an int value for the same key
    warns = reg.observe(
        AtomicNote(id="a-int", type="claim", attributes={"k": 42}, body="x")
    )
    assert any("k" in w and "int" in w for w in warns)


def test_relation_observed_and_promoted() -> None:
    reg = Registry()
    for i in range(PROMOTION_THRESHOLD):
        reg.observe(
            AtomicNote(
                id=f"a{i}",
                type="claim",
                body="See [[t]]",
                relations=[Relation(type="supports", target="t")],
            )
        )
    assert "supports" in reg.relations
    assert reg.relations["supports"].is_promoted


def test_forget_removes_atom_contribution() -> None:
    reg = Registry()
    a = AtomicNote(id="a", type="claim", attributes={"k": 1}, body="x")
    reg.observe(a)
    assert "k" in reg.attributes
    reg.forget(a)
    assert "k" not in reg.attributes


def test_forget_keeps_attribute_when_others_use_it() -> None:
    reg = Registry()
    a1 = AtomicNote(id="a1", type="claim", attributes={"k": 1}, body="x")
    a2 = AtomicNote(id="a2", type="claim", attributes={"k": 2}, body="x")
    reg.observe(a1)
    reg.observe(a2)
    reg.forget(a1)
    assert "k" in reg.attributes
    assert reg.attributes["k"].uses == 1


def test_validate_warns_for_unknown_attribute() -> None:
    reg = Registry()
    a = AtomicNote(id="a", type="claim", attributes={"novel_key": "v"}, body="x")
    warns = reg.validate(a)
    assert any("novel_key" in w for w in warns)


def test_validate_warns_for_unknown_relation_type() -> None:
    reg = Registry()
    a = AtomicNote(
        id="a",
        type="claim",
        body="See [[t]]",
        relations=[Relation(type="exotic-edge", target="t")],
    )
    warns = reg.validate(a)
    assert any("exotic-edge" in w for w in warns)


def test_validate_silent_for_known_attribute() -> None:
    reg = Registry()
    reg.observe(AtomicNote(id="x", type="claim", attributes={"k": "v"}, body="x"))
    a = AtomicNote(id="a", type="claim", attributes={"k": "v2"}, body="x")
    warns = reg.validate(a)
    assert not any("'k'" in w and "new" in w for w in warns)


def test_validate_warns_on_promoted_type_drift() -> None:
    reg = Registry()
    for i in range(PROMOTION_THRESHOLD):
        reg.observe(AtomicNote(id=f"a{i}", type="claim", attributes={"k": "v"}, body="x"))
    a = AtomicNote(id="new", type="claim", attributes={"k": 99}, body="x")
    warns = reg.validate(a)
    assert any("promoted" in w and "int" in w for w in warns)


def test_validate_notes_expected_inverse_when_declared(fresh_vault: Vault) -> None:
    fresh_vault.registry.declare_inverse("supports", "supported-by")
    fresh_vault.write(AtomicNote(id="atom-target", type="claim", body="target"))
    candidate = AtomicNote(
        id="atom-source",
        type="claim",
        body="See [[atom-target]]",
        relations=[Relation(type="supports", target="atom-target")],
    )
    warns = fresh_vault.registry.validate(
        candidate, known_atom_ids=["atom-target", "atom-source"]
    )
    assert any("inverse" in w and "supported-by" in w for w in warns)


def test_registry_save_and_load_roundtrip(tmp_path) -> None:
    reg = Registry(path=tmp_path / "registry.yaml")
    reg.observe(
        AtomicNote(
            id="a1",
            type="claim",
            attributes={"domain": "x"},
            body="See [[t]]",
            relations=[Relation(type="supports", target="t")],
        )
    )
    reg.save()
    reloaded = Registry.load(tmp_path / "registry.yaml")
    assert "domain" in reloaded.attributes
    assert "supports" in reloaded.relations
    assert reloaded.attributes["domain"].uses == 1


def test_declare_inverse_idempotent() -> None:
    reg = Registry()
    reg.declare_inverse("a", "b")
    reg.declare_inverse("a", "b")
    assert reg.relations["a"].inverse == "b"
    assert reg.relations["b"].inverse == "a"


def test_load_missing_registry_returns_empty(tmp_path) -> None:
    reg = Registry.load(tmp_path / "nope.yaml")
    assert reg.attributes == {}
    assert reg.relations == {}


def test_vault_write_records_observations(fresh_vault: Vault) -> None:
    fresh_vault.write(
        AtomicNote(id="a1", type="claim", attributes={"x": 1}, body="body")
    )
    assert "x" in fresh_vault.registry.attributes
    # And persisted to disk
    from openacad.vault.registry import Registry as RegCls

    reg = RegCls.load(fresh_vault.sidecar / "index" / "registry.yaml")
    assert "x" in reg.attributes


def test_vault_delete_removes_observation(fresh_vault: Vault) -> None:
    fresh_vault.write(
        AtomicNote(id="a1", type="claim", attributes={"only-on-a1": 1}, body="body")
    )
    assert "only-on-a1" in fresh_vault.registry.attributes
    fresh_vault.delete("a1")
    assert "only-on-a1" not in fresh_vault.registry.attributes
