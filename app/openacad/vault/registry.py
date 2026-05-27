"""Observed attribute + relation schema for a vault.

Each vault tracks a YAML registry at ``.openacad/index/registry.yaml``::

    attributes:
      domain:
        first_seen: 2026-05-27T10:00:00Z
        uses: 14
        types: [str]
      evidence:
        first_seen: 2026-05-27T10:00:00Z
        uses: 9
        types: [str]
    relations:
      supports:
        first_seen: 2026-05-27T10:00:00Z
        uses: 7
        inverse: null
      contradicts:
        first_seen: 2026-05-27T10:00:00Z
        uses: 3
        inverse: contradicts        # self-inverse

The registry is *observational* — it records what's been used. Validation
returns warnings, never raises. After an attribute has been used N+
times it's auto-promoted (its ``types`` list is frozen, future writes
emit a warning if a new type appears).
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

if TYPE_CHECKING:
    from .atoms import AtomicNote

PROMOTION_THRESHOLD = 3
"""Number of distinct atoms an attribute or relation must appear in
before the registry considers it 'promoted' (stable / typed)."""


@dataclass
class AttributeDef:
    """A registered attribute key."""

    name: str
    first_seen: str
    uses: int = 0
    atoms: set[str] = field(default_factory=set)
    types: list[str] = field(default_factory=list)

    @property
    def is_promoted(self) -> bool:
        return len(self.atoms) >= PROMOTION_THRESHOLD

    def to_dict(self) -> dict:
        return {
            "first_seen": self.first_seen,
            "uses": self.uses,
            "atoms": sorted(self.atoms),
            "types": list(self.types),
        }

    @classmethod
    def from_dict(cls, name: str, data: dict) -> AttributeDef:
        return cls(
            name=name,
            first_seen=str(data.get("first_seen", _utcnow())),
            uses=int(data.get("uses", 0)),
            atoms=set(data.get("atoms") or []),
            types=list(data.get("types") or []),
        )


@dataclass
class RelationDef:
    """A registered relation type."""

    name: str
    first_seen: str
    uses: int = 0
    atoms: set[str] = field(default_factory=set)
    inverse: str | None = None

    @property
    def is_promoted(self) -> bool:
        return len(self.atoms) >= PROMOTION_THRESHOLD

    def to_dict(self) -> dict:
        d: dict = {
            "first_seen": self.first_seen,
            "uses": self.uses,
            "atoms": sorted(self.atoms),
        }
        if self.inverse is not None:
            d["inverse"] = self.inverse
        return d

    @classmethod
    def from_dict(cls, name: str, data: dict) -> RelationDef:
        return cls(
            name=name,
            first_seen=str(data.get("first_seen", _utcnow())),
            uses=int(data.get("uses", 0)),
            atoms=set(data.get("atoms") or []),
            inverse=data.get("inverse"),
        )


def _utcnow() -> str:
    return datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _type_name(value: object) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "str"
    if isinstance(value, list):
        return "list"
    if isinstance(value, dict):
        return "dict"
    return type(value).__name__


class Registry:
    """Vault attribute + relation registry. Mutated by ``Vault.write()``."""

    def __init__(
        self,
        path: str | Path | None = None,
        *,
        attributes: dict[str, AttributeDef] | None = None,
        relations: dict[str, RelationDef] | None = None,
    ) -> None:
        self.path: Path | None = Path(path) if path is not None else None
        self.attributes: dict[str, AttributeDef] = dict(attributes or {})
        self.relations: dict[str, RelationDef] = dict(relations or {})

    # ------------------------------------------------------------------
    # disk I/O
    # ------------------------------------------------------------------

    @classmethod
    def load(cls, path: str | Path) -> Registry:
        p = Path(path)
        if not p.exists():
            return cls(path=p)
        data = yaml.safe_load(p.read_text("utf-8")) or {}
        attrs = {
            name: AttributeDef.from_dict(name, body or {})
            for name, body in (data.get("attributes") or {}).items()
        }
        rels = {
            name: RelationDef.from_dict(name, body or {})
            for name, body in (data.get("relations") or {}).items()
        }
        return cls(path=p, attributes=attrs, relations=rels)

    def save(self, path: str | Path | None = None) -> None:
        target = Path(path) if path is not None else self.path
        if target is None:
            raise ValueError("Registry has no path; pass one to save()")
        target.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "attributes": {
                name: defn.to_dict() for name, defn in sorted(self.attributes.items())
            },
            "relations": {
                name: defn.to_dict() for name, defn in sorted(self.relations.items())
            },
        }
        target.write_text(
            yaml.safe_dump(data, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )

    # ------------------------------------------------------------------
    # mutation — called by Vault.write()
    # ------------------------------------------------------------------

    def observe(self, atom: AtomicNote) -> list[str]:
        """Record the atom's attribute/relation usage; return warnings.

        Warnings are emitted (but not raised) for:
          - a new type appearing on a promoted attribute
          - a relation type whose ``inverse`` is registered but the
            inverse-relation doesn't exist on the target atom (we can't
            verify this here without graph context — the caller does it)
        """
        warnings: list[str] = []
        now = _utcnow()

        # attributes
        for key, value in atom.attributes.items():
            tname = _type_name(value)
            defn = self.attributes.get(key)
            if defn is None:
                self.attributes[key] = AttributeDef(
                    name=key,
                    first_seen=now,
                    uses=1,
                    atoms={atom.id},
                    types=[tname],
                )
            else:
                defn.uses += 1
                defn.atoms.add(atom.id)
                if tname not in defn.types:
                    if defn.is_promoted:
                        warnings.append(
                            f"attribute {key!r} is promoted (types={defn.types}) "
                            f"but atom {atom.id!r} introduces new type {tname!r}"
                        )
                    defn.types.append(tname)

        # relations
        for rel in atom.relations:
            defn = self.relations.get(rel.type)
            if defn is None:
                self.relations[rel.type] = RelationDef(
                    name=rel.type,
                    first_seen=now,
                    uses=1,
                    atoms={atom.id},
                )
            else:
                defn.uses += 1
                defn.atoms.add(atom.id)

        return warnings

    def forget(self, atom: AtomicNote) -> None:
        """Remove an atom's contributions from the registry."""
        for key in atom.attributes.keys():
            defn = self.attributes.get(key)
            if defn is None:
                continue
            if atom.id in defn.atoms:
                defn.atoms.discard(atom.id)
                defn.uses = max(0, defn.uses - 1)
            if not defn.atoms:
                del self.attributes[key]
        for rel in atom.relations:
            defn = self.relations.get(rel.type)
            if defn is None:
                continue
            if atom.id in defn.atoms:
                defn.atoms.discard(atom.id)
                defn.uses = max(0, defn.uses - 1)
            if not defn.atoms:
                del self.relations[rel.type]

    # ------------------------------------------------------------------
    # validation (used by Vault.write() and standalone tests)
    # ------------------------------------------------------------------

    def validate(
        self,
        atom: AtomicNote,
        *,
        known_atom_ids: Iterable[str] = (),
    ) -> list[str]:
        """Return warnings for the atom against the current schema.

        - **Orphan keys**: attribute appears in the registry < threshold
          times AND this is the first time we're seeing it on the atom.
          (Diagnostic: lets the scholar spot one-off attributes that
          might be typos or premature additions.)
        - **Missing-inverse**: a registered relation type has an
          ``inverse`` defined, but the target atom (if present in
          ``known_atom_ids``) doesn't carry the inverse edge back.
          We only flag the structural concern here; the Vault does the
          actual neighbour lookup.
        - **Unknown relation type**: not currently registered (will be
          on observe; we surface this as a heads-up).
        """
        warnings: list[str] = []
        known = set(known_atom_ids)

        for key, value in atom.attributes.items():
            defn = self.attributes.get(key)
            if defn is None:
                warnings.append(
                    f"attribute {key!r} is new — will be auto-registered on write"
                )
            else:
                tname = _type_name(value)
                if defn.is_promoted and tname not in defn.types:
                    warnings.append(
                        f"attribute {key!r} is promoted with types {defn.types}; "
                        f"this atom's value is {tname!r}"
                    )

        for rel in atom.relations:
            defn = self.relations.get(rel.type)
            if defn is None:
                warnings.append(
                    f"relation type {rel.type!r} is new — will be auto-registered on write"
                )
            elif defn.inverse is not None and known and rel.target in known:
                # The Vault will do the actual back-edge check; we just
                # note that an inverse is expected.
                warnings.append(
                    f"relation {rel.type!r} → {rel.target!r}: inverse "
                    f"{defn.inverse!r} expected on target"
                )
        return warnings

    # ------------------------------------------------------------------
    # promotion API
    # ------------------------------------------------------------------

    def declare_inverse(self, relation: str, inverse: str) -> None:
        """Register a typed inverse pair (used by ``openacad init`` / config)."""
        if relation not in self.relations:
            self.relations[relation] = RelationDef(name=relation, first_seen=_utcnow())
        self.relations[relation].inverse = inverse
        if inverse not in self.relations:
            self.relations[inverse] = RelationDef(name=inverse, first_seen=_utcnow())
        self.relations[inverse].inverse = relation

    def promoted_attributes(self) -> list[str]:
        return sorted(name for name, defn in self.attributes.items() if defn.is_promoted)

    def promoted_relations(self) -> list[str]:
        return sorted(name for name, defn in self.relations.items() if defn.is_promoted)


__all__ = [
    "Registry",
    "AttributeDef",
    "RelationDef",
    "PROMOTION_THRESHOLD",
]
