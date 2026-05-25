"""The canonical AtomicNote schema. See docs/note-anatomy.md for the spec."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

AtomKind = Literal["claim", "method", "finding"]
AtomStatus = Literal["draft", "active", "archived", "deprecated"]
ScholarAct = Literal["accepted", "edited", "seeded", "originated", "deprecated"]

# Scalar-only at v1. Upgrade path: widen to `str | int | float | bool | None | list | dict`.
AttrValue = str | int | float | bool | None


class Metas(BaseModel):
    id: str
    type: AtomKind
    status: AtomStatus = "active"
    created_at: datetime
    updated_at: datetime
    tags: list[str] = Field(default_factory=list)


class Origin(BaseModel):
    source_id: str | None = None
    chunk_ids: list[str] = Field(default_factory=list)
    page_range: tuple[int, int] | None = None
    prompt_version: str | None = None
    scholar_action: ScholarAct = "seeded"


class Relation(BaseModel):
    type: str
    target: str


class AtomicNote(BaseModel):
    metas: Metas
    origin: Origin
    attributes: dict[str, AttrValue] = Field(default_factory=dict)
    relations: list[Relation] = Field(default_factory=list)
    content: str = ""


class ProposedAtom(BaseModel):
    """What the extraction agent emits. The pipeline wraps these into DraftAtom
    by adding runtime fields (draft_id, drafted_at, prompt_version, source_id, chunk_ids)."""

    type: AtomKind
    suggested_id: str = Field(description="Stable kebab-case id, e.g. '2026-05-24-claim-foo'")
    tags: list[str] = Field(default_factory=list)
    attributes: dict[str, AttrValue] = Field(default_factory=dict)
    relations: list[Relation] = Field(default_factory=list)
    content: str = Field(description="The atomic idea, in markdown. One idea, stands alone.")


class DraftAtom(BaseModel):
    """An AI-extracted draft sitting in the HITL queue. Becomes an AtomicNote on accept."""

    draft_id: str
    drafted_at: datetime
    prompt_version: str
    source_id: str
    chunk_ids: list[str]
    page_range: tuple[int, int] | None = None

    # the proposed atom shape (metas.id assigned at accept-time)
    type: AtomKind
    suggested_id: str
    tags: list[str] = Field(default_factory=list)
    attributes: dict[str, AttrValue] = Field(default_factory=dict)
    relations: list[Relation] = Field(default_factory=list)
    content: str = ""

    # extraction-time signals (populated by /extract/score)
    confidence_score: float | None = None
    validation_errors: list[str] = Field(default_factory=list)
