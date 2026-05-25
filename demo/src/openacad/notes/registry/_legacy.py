"""Registry mutations: auto-promotion at threshold, manual promotion of proposals,
strict validation entry point, schema-evolution audit log.

Strict validation lives in schema.Schema.validate(); this module wraps it with
the target_kind lookup against the live vault.
"""

import uuid
from collections import defaultdict
from datetime import datetime, timezone



from openacad.runtime.settings import settings
from openacad.notes.schema import AtomicNote, AtomKind, AttrValue
from openacad.notes.registry.schema import AttributeDef, Proposal, RelationDef, TypeDef, ValueType
from openacad.runtime import db
from openacad.notes.persistence import vault as vault_io
from openacad.notes.registry.validation import get_schema, reload_schema


def now() -> datetime:
    return datetime.now(timezone.utc)


# ── target_kind lookup against the vault ────────────────────────────────


def _build_target_lookup(extra_atoms: list[AtomicNote] | None = None):
    """Return a target_kind(atom_id) function backed by current vault + extras.

    `extra_atoms` lets a batch-commit include not-yet-written atoms (e.g. a draft
    referencing another draft in the same batch).
    """
    on_disk = {a.metas.id: a.metas.type for a in vault_io.list_atoms()}
    for a in extra_atoms or []:
        on_disk[a.metas.id] = a.metas.type

    def lookup(atom_id: str) -> AtomKind | None:
        return on_disk.get(atom_id)

    return lookup


def validate_atom(atom: AtomicNote, extra_atoms: list[AtomicNote] | None = None) -> list[str]:
    """Strict-validate an atom against current registry + vault."""
    return get_schema().validate(atom, _build_target_lookup(extra_atoms))


# ── value_type inference (for auto-promotion) ───────────────────────────


def _infer_value_type(values: list[AttrValue]) -> tuple[ValueType, list[AttrValue] | None]:
    """Heuristic: if all observed values are same simple type, use it. If a small
    set of distinct strings, propose enum."""
    non_null = [v for v in values if v is not None]
    if not non_null:
        return "string", None
    types: set[str] = set()
    for v in non_null:
        if isinstance(v, bool):
            types.add("bool")
        elif isinstance(v, (int, float)):
            types.add("number")
        elif isinstance(v, str):
            types.add("string")
        else:
            types.add("string")
    if len(types) == 1:
        t = types.pop()
        if t == "string":
            distinct = sorted({v for v in non_null if isinstance(v, str)})
            if 2 <= len(distinct) <= 6:
                return "enum", distinct
            return "string", None
        return t, None  # type: ignore[return-value]
    return "string", None


# ── usage recount + auto-promotion ──────────────────────────────────────


def recount_usage_and_promote() -> dict:
    """Walk the vault, recount per-key usage for attributes and relations,
    auto-register any unknown keys that cross the promotion threshold.

    Returns a summary dict for the caller (CLI/UI feedback).
    """
    schema = get_schema()
    threshold = settings.registry_promote_threshold

    all_atoms = vault_io.list_atoms()
    promoted: dict[str, list[str]] = {"attributes": [], "relations": []}

    # ── attributes ──────────────────────────────────────────────
    usage_attr: dict[str, list[AttrValue]] = defaultdict(list)
    applicable_attr: dict[str, set[AtomKind]] = defaultdict(set)
    for atom in all_atoms:
        for k, v in atom.attributes.items():
            usage_attr[k].append(v)
            applicable_attr[k].add(atom.metas.type)

    for key, values in usage_attr.items():
        existing = schema.attributes.get(key)
        if existing:
            if existing.usage_count != len(values):
                existing.usage_count = len(values)
                vault_io.write_attribute_def(existing)
            continue
        if len(values) >= threshold:
            namespace = key.split(".")[0] if "." in key else ""
            vt, allowed = _infer_value_type(values)
            ad = AttributeDef(
                key=key,
                namespace=namespace,
                description=f"Auto-registered after {len(values)} uses",
                value_type=vt,
                allowed_values=allowed,
                applicable_types=sorted(applicable_attr[key]),
                usage_count=len(values),
                first_seen=now(),
                auto_registered=True,
            )
            vault_io.write_attribute_def(ad)
            vault_io.append_schema_evolution(
                {
                    "timestamp": now().isoformat(),
                    "action": "auto-register",
                    "kind": "attribute",
                    "key": key,
                    "trigger": f"{len(values)}th use",
                    "value_type": vt,
                }
            )
            promoted["attributes"].append(key)

    # ── relations ───────────────────────────────────────────────
    usage_rel_source: dict[str, set[str]] = defaultdict(set)  # rel_type -> {source_atom_id}
    source_types_rel: dict[str, set[AtomKind]] = defaultdict(set)
    target_types_rel: dict[str, set[AtomKind]] = defaultdict(set)
    atom_kinds = {a.metas.id: a.metas.type for a in all_atoms}
    for atom in all_atoms:
        for r in atom.relations:
            usage_rel_source[r.type].add(atom.metas.id)
            source_types_rel[r.type].add(atom.metas.type)
            if r.target in atom_kinds:
                target_types_rel[r.type].add(atom_kinds[r.target])

    for key, sources in usage_rel_source.items():
        existing = schema.relations.get(key)
        if existing:
            if existing.usage_count != len(sources):
                existing.usage_count = len(sources)
                vault_io.write_relation_def(existing)
            continue
        if len(sources) >= threshold:
            rd = RelationDef(
                key=key,
                namespace="",
                description=f"Auto-registered after {len(sources)} uses",
                source_types=sorted(source_types_rel[key]),
                target_types=sorted(target_types_rel[key]),
                usage_count=len(sources),
                first_seen=now(),
                auto_registered=True,
            )
            vault_io.write_relation_def(rd)
            vault_io.append_schema_evolution(
                {
                    "timestamp": now().isoformat(),
                    "action": "auto-register",
                    "kind": "relation",
                    "key": key,
                    "trigger": f"{len(sources)}th source",
                }
            )
            promoted["relations"].append(key)

    if promoted["attributes"] or promoted["relations"]:
        reload_schema()

    return promoted


# ── proposals (types are always proposed, never auto-promoted) ──────────


def propose_new_type(key: str, triggered_by: str, rationale: str = "") -> Proposal:
    """Called by extraction_pipeline when a draft asks for an unknown atom type."""
    existing = [p for p in db.list_proposals("pending") if p.key == key and p.kind == "new_type"]
    if existing:
        return existing[0]

    p = Proposal(
        id=f"prop-{uuid.uuid4().hex[:8]}",
        kind="new_type",
        key=key,
        proposed_at=now(),
        triggered_by=triggered_by,
        rationale=rationale,
    )
    db.insert_proposal(p)
    vault_io.append_schema_evolution(
        {
            "timestamp": now().isoformat(),
            "action": "proposal",
            "kind": "type",
            "key": key,
            "triggered_by": triggered_by,
        }
    )
    return p


def promote_proposal(proposal_id: str, payload: dict | None = None) -> dict:
    """Scholar-approve a proposal. Writes the registry entry."""
    proposal = db.get_proposal(proposal_id)
    if proposal is None:
        raise ValueError(f"proposal {proposal_id} not found")
    if proposal.state != "pending":
        raise ValueError(f"proposal {proposal_id} is {proposal.state}, not pending")

    payload = payload or {}

    if proposal.kind == "new_type":
        td = TypeDef(
            key=proposal.key,
            description=payload.get("description") or proposal.rationale or "",
            suggested_attributes=payload.get("suggested_attributes") or [],
            suggested_relations=payload.get("suggested_relations") or [],
            first_seen=now(),
            auto_registered=False,
        )
        vault_io.write_type_def(td)
        vault_io.append_schema_evolution(
            {
                "timestamp": now().isoformat(),
                "action": "promote",
                "kind": "type",
                "key": proposal.key,
            }
        )
    else:
        raise NotImplementedError(f"promote_proposal: kind={proposal.kind}")

    db.update_proposal_state(proposal_id, "promoted")
    reload_schema()
    return {"ok": True, "key": proposal.key, "kind": proposal.kind}


def reject_proposal(proposal_id: str) -> dict:
    proposal = db.get_proposal(proposal_id)
    if proposal is None:
        raise ValueError(f"proposal {proposal_id} not found")
    db.update_proposal_state(proposal_id, "rejected")
    vault_io.append_schema_evolution(
        {
            "timestamp": now().isoformat(),
            "action": "reject",
            "kind": proposal.kind,
            "key": proposal.key,
        }
    )
    return {"ok": True}
