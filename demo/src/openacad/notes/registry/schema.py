from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from openacad.notes.schema.note import AtomKind

ValueType = Literal["string", "number", "bool", "enum", "date"]


class AttributeDef(BaseModel):
    key: str
    namespace: str = ""
    description: str = ""
    value_type: ValueType = "string"
    allowed_values: list[Any] | None = None
    applicable_types: list[AtomKind] = Field(default_factory=list)
    usage_count: int = 0
    first_seen: datetime
    auto_registered: bool = True


class RelationDef(BaseModel):
    key: str
    namespace: str = ""
    description: str = ""
    inverse: str | None = None
    source_types: list[AtomKind] = Field(default_factory=list)
    target_types: list[AtomKind] = Field(default_factory=list)
    usage_count: int = 0
    first_seen: datetime
    auto_registered: bool = True


class TypeDef(BaseModel):
    key: AtomKind
    description: str = ""
    suggested_attributes: list[str] = Field(default_factory=list)
    suggested_relations: list[str] = Field(default_factory=list)
    example_atom: str | None = None
    first_seen: datetime
    auto_registered: bool = False


ProposalKind = Literal[
    "new_type", "constraint_tightening", "new_attribute", "new_relation", "promote_value_to_enum"
]


class Proposal(BaseModel):
    id: str
    kind: ProposalKind
    key: str
    proposed_at: datetime
    triggered_by: str
    payload: dict = Field(default_factory=dict)
    state: Literal["pending", "promoted", "rejected"] = "pending"
    rationale: str = ""
