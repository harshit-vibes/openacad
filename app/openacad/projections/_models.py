"""DTOs for the read-only Ops Console projections.

Every BaseModel here is a *projection* contract: pure data shapes consumed by
Streamlit widgets and external HTTP surfaces. Domain models (PromptVersion,
PaperSource, AtomicNote) are deliberately not re-exported here — projections
convert from those into the flat, JSON-safe shapes below.

Names that collide with `openacad.notes.registry.schema` (AttributeDef,
RelationDef) refer to *this* DTO from the projections layer; registry callers
must import the registry models under an alias to disambiguate.
"""

from datetime import datetime

from pydantic import BaseModel, Field

from openacad.feedback.schema import PromptVersion


# ── Ingest ──────────────────────────────────────────────────────────────


class PaperRow(BaseModel):
    source_id: str
    title: str
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    pages: int | None = None
    chunks: int = 0
    atoms: int = 0
    ingested_at: datetime


class PaperLibraryView(BaseModel):
    papers: list[PaperRow] = Field(default_factory=list)
    total_papers: int = 0
    total_chunks: int = 0
    total_atoms: int = 0
    last_ingested_at: datetime | None = None


# ── Registry / Notes ────────────────────────────────────────────────────


class AtomRow(BaseModel):
    atom_id: str
    kind: str
    content_preview: str = ""  # first 200 chars
    n_attrs: int = 0
    n_rels: int = 0
    source_id: str | None = None


class AttributeDef(BaseModel):
    key: str
    value_type: str
    allowed_values: list[str] | None = None
    usage_count: int = 0
    first_seen: datetime | None = None


class RelationDef(BaseModel):
    key: str
    source_types: list[str] = Field(default_factory=list)
    target_types: list[str] = Field(default_factory=list)
    inverse: str | None = None
    usage_count: int = 0


class RegistryView(BaseModel):
    atoms: list[AtomRow] = Field(default_factory=list)
    attributes: list[AttributeDef] = Field(default_factory=list)
    relations: list[RelationDef] = Field(default_factory=list)
    total_atoms: int = 0
    total_attrs: int = 0
    total_rels: int = 0
    orphan_attrs: list[str] = Field(default_factory=list)
    orphan_rels: list[str] = Field(default_factory=list)


# ── Curation ────────────────────────────────────────────────────────────


class DraftRow(BaseModel):
    draft_id: str
    source_id: str | None = None
    drafted_at: datetime
    prompt_version: str
    payload_preview: str = ""


class VerdictRow(BaseModel):
    event_id: str
    timestamp: datetime
    kind: str  # accept/edit/reject/deprecate
    draft_id: str | None = None
    actor: str
    delta: dict = Field(default_factory=dict)


class CurationView(BaseModel):
    pending_drafts: list[DraftRow] = Field(default_factory=list)
    verdict_history: list[VerdictRow] = Field(default_factory=list)
    counts: dict[str, int] = Field(default_factory=dict)
    # {accept: N, edit: N, reject: N, deprecate: N, pending: N}


# ── Evals & Prompt Hardening ────────────────────────────────────────────


class ComparisonRow(BaseModel):
    id: str
    question: str
    tokens_in: int = 0
    tokens_out: int = 0
    latency_ms: int = 0
    citations: int = 0
    answer_preview: str = ""
    run_at: datetime


class RubricRow(BaseModel):
    id: str
    role: str  # answerer, extractor, ...
    criteria: dict[str, float] = Field(default_factory=dict)
    timestamp: datetime
    notes: str | None = None


class PromptTimeline(BaseModel):
    role: str  # answerer, extractor, scorer, meta_evaluator
    versions: list[PromptVersion] = Field(default_factory=list)


class MetaProposalRow(BaseModel):
    event_id: str
    timestamp: datetime
    target_role: str
    insight_kind: str
    proposed_change_preview: str = ""
    based_on_events: list[str] = Field(default_factory=list)
    state: str  # proposed/active/archived (or pending/promoted/rejected for Proposal)


class EvalsView(BaseModel):
    comparison_runs: list[ComparisonRow] = Field(default_factory=list)
    rubric_scores: list[RubricRow] = Field(default_factory=list)
    rubric_avg_by_criterion: dict[str, float] = Field(default_factory=dict)
    prompt_timelines: list[PromptTimeline] = Field(default_factory=list)
    meta_proposals: list[MetaProposalRow] = Field(default_factory=list)


# ── Observability ───────────────────────────────────────────────────────


class ToolCallRow(BaseModel):
    id: str
    session_id: str
    agent: str
    tool_name: str
    arguments: dict = Field(default_factory=dict)
    n_results: int = 0
    latency_ms: int = 0
    timestamp: datetime
    error_message: str | None = None  # new field (added by schema migration)


class LatencyBucket(BaseModel):
    upper_ms: int  # bucket upper bound; sentinel value (e.g. 10_000_000) for the "10000+" bucket
    count: int = 0


class CostRollupItem(BaseModel):
    bucket_label: str  # e.g. "answerer" / "synthesis" / "A" / "2026-05-23"
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0  # gpt-4o-mini: 0.15/M in, 0.60/M out


class ActivityFeedItem(BaseModel):
    timestamp: datetime
    kind: str  # tool_call, verdict, prompt_promote, rubric, ...
    actor: str
    summary: str  # human-readable one-liner
    detail: dict = Field(default_factory=dict)


class ObservabilityView(BaseModel):
    tool_calls: list[ToolCallRow] = Field(default_factory=list)
    latency_histogram: list[LatencyBucket] = Field(default_factory=list)
    cost_by_role: list[CostRollupItem] = Field(default_factory=list)
    cost_by_day: list[CostRollupItem] = Field(default_factory=list)
    activity_feed: list[ActivityFeedItem] = Field(default_factory=list)
    errors: list[ToolCallRow] = Field(default_factory=list)
    n_tool_calls: int = 0
    avg_latency_ms: float = 0.0
    total_cost_usd: float = 0.0
    n_errors: int = 0
