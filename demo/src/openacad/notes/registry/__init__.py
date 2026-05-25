"""The typed registry — attribute/relation/kind definitions that grow as
notes accumulate."""

from openacad.notes.registry.schema import (
    AttributeDef,
    Proposal,
    ProposalKind,
    RelationDef,
    TypeDef,
    ValueType,
)
from openacad.notes.registry.validation import Schema, get_schema, reload_schema
from openacad.notes.registry._legacy import (
    validate_atom,
    recount_usage_and_promote,
    propose_new_type,
    promote_proposal,
    reject_proposal,
)

__all__ = [
    "AttributeDef", "Proposal", "ProposalKind", "RelationDef",
    "TypeDef", "ValueType",
    "Schema", "get_schema", "reload_schema",
    "validate_atom", "recount_usage_and_promote",
    "propose_new_type", "promote_proposal", "reject_proposal",
]
