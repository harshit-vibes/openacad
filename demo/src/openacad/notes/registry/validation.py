"""In-memory Schema cache — the single source of registry truth.

Loaded at boot from vault/registry/. Consulted by:
- extraction_agent: for prompt context (what attributes/relations to suggest)
- curate flow: for write-time strict validation
- retrieval: for query planning (cardinality from usage_count)
- registry_service: for promotion threshold checks

`reload()` is called after any registry mutation. Hot reload, no service restart.
"""

from threading import Lock
from typing import Callable

from openacad.notes.schema import AtomicNote, AtomKind, AttrValue

from openacad.notes.registry.schema import AttributeDef, RelationDef, TypeDef
from openacad.notes.persistence import vault as vault_io
class Schema:
    def __init__(self) -> None:
        self.attributes: dict[str, AttributeDef] = {}
        self.relations: dict[str, RelationDef] = {}
        self.types: dict[str, TypeDef] = {}
        self._lock = Lock()
        self.reload()

    def reload(self) -> None:
        with self._lock:
            self.attributes = {d.key: d for d in vault_io.list_attribute_defs()}
            self.relations = {d.key: d for d in vault_io.list_relation_defs()}
            self.types = {d.key: d for d in vault_io.list_type_defs()}

    # ── lookup ──────────────────────────────────────────────────────────

    def get_attribute(self, key: str) -> AttributeDef | None:
        return self.attributes.get(key)

    def get_relation(self, key: str) -> RelationDef | None:
        return self.relations.get(key)

    def get_type(self, key: str) -> TypeDef | None:
        return self.types.get(key)

    def attributes_for_type(self, atom_type: AtomKind) -> list[AttributeDef]:
        return [
            d for d in self.attributes.values()
            if not d.applicable_types or atom_type in d.applicable_types
        ]

    def relations_for_source(self, atom_type: AtomKind) -> list[RelationDef]:
        return [
            d for d in self.relations.values()
            if not d.source_types or atom_type in d.source_types
        ]

    # ── validation ──────────────────────────────────────────────────────

    def validate(
        self,
        atom: AtomicNote,
        target_kind: Callable[[str], AtomKind | None],
    ) -> list[str]:
        """Strict-validate an atom. Returns list of error messages (empty = OK).

        `target_kind(atom_id)` returns the AtomKind of an existing atom or None.
        Caller provides this so Schema stays decoupled from storage.
        """
        errors: list[str] = []
        atom_type = atom.metas.type

        # ── attributes ──────────────────────────────────────────────
        for k, v in atom.attributes.items():
            ad = self.attributes.get(k)
            if ad is None:
                continue  # unknown keys pass through — eligible for auto-promotion
            if ad.applicable_types and atom_type not in ad.applicable_types:
                errors.append(
                    f"attribute '{k}' not applicable to type '{atom_type}' "
                    f"(allowed: {ad.applicable_types})"
                )
            if not self._value_matches(v, ad):
                tail = f" allowed={ad.allowed_values}" if ad.allowed_values else ""
                errors.append(
                    f"attribute '{k}' value {v!r} doesn't match "
                    f"value_type={ad.value_type}{tail}"
                )

        # ── relations ───────────────────────────────────────────────
        for rel in atom.relations:
            rd = self.relations.get(rel.type)
            if rd is None:
                continue  # unknown relation type passes through
            if rd.source_types and atom_type not in rd.source_types:
                errors.append(
                    f"relation '{rel.type}' invalid source type '{atom_type}' "
                    f"(allowed: {rd.source_types})"
                )
            tk = target_kind(rel.target)
            if tk is None:
                errors.append(f"relation '{rel.type}' target '{rel.target}' does not exist")
                continue
            if rd.target_types and tk not in rd.target_types:
                errors.append(
                    f"relation '{rel.type}' invalid target type '{tk}' for "
                    f"target '{rel.target}' (allowed: {rd.target_types})"
                )

        return errors

    @staticmethod
    def _value_matches(v: AttrValue, ad: AttributeDef) -> bool:
        if v is None:
            return True  # explicit null is "asked but absent" — always allowed
        if ad.value_type == "string":
            return isinstance(v, str)
        if ad.value_type == "number":
            return isinstance(v, (int, float)) and not isinstance(v, bool)
        if ad.value_type == "bool":
            return isinstance(v, bool)
        if ad.value_type == "date":
            return isinstance(v, str)  # ISO-8601 string
        if ad.value_type == "enum":
            return v in (ad.allowed_values or [])
        return True


_schema: Schema | None = None
_schema_lock = Lock()


def get_schema() -> Schema:
    global _schema
    if _schema is None:
        with _schema_lock:
            if _schema is None:
                _schema = Schema()
    return _schema


def reload_schema() -> None:
    get_schema().reload()
