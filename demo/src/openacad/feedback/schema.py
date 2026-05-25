from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

EvalEventKind = Literal[
    "accept",
    "edit",
    "reject",
    "compare_run",
    "tool_call",
    "registry_change",
    "prompt_regen",
    "prompt_promote",
    "prompt_propose",
    "query_marked_poor",
    "rubric",
]

Pipeline = Literal["B0", "B1", "B2", "A"]


class EvalEvent(BaseModel):
    id: str
    timestamp: datetime
    kind: EvalEventKind
    actor: str = "scholar"
    payload: dict = Field(default_factory=dict)


class PromptVersion(BaseModel):
    name: Literal[
        # Legacy role names (pre-scenario refactor)
        "extraction", "synthesis",
        # Scenario agent roles (Step 1+ onward)
        "answerer", "extractor", "scorer", "meta_evaluator",
    ]
    version: str  # e.g. "extraction.v3" or "answerer.v1"
    created_at: datetime
    body: str
    parent_version: str | None = None
    state: Literal["proposed", "active", "archived"] = "proposed"
    accept_rate: float | None = None
    avg_edit_distance: float | None = None
    based_on_events: list[str] = Field(default_factory=list)


class ToolCall(BaseModel):
    id: str
    session_id: str
    agent: Literal["extraction", "synthesis"]
    tool_name: str
    arguments: dict = Field(default_factory=dict)
    n_results: int = 0
    latency_ms: int = 0
    timestamp: datetime
    error_message: str | None = None


class ComparisonResult(BaseModel):
    id: str
    question: str
    paper_ids: list[str]
    pipeline: Pipeline
    answer: str
    citations: list[str] = Field(default_factory=list)
    tokens_in: int = 0
    tokens_out: int = 0
    latency_ms: int = 0
    accuracy_vs_gold: float | None = None
    citation_precision: float | None = None
    n_units_retrieved: int = 0
    tool_call_ids: list[str] = Field(default_factory=list)
    run_at: datetime
