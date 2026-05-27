from typing import Any

from pydantic import BaseModel, Field

from openacad.notes.schema.note import AtomicNote


class QueryResult(BaseModel):
    atoms: list[AtomicNote] = Field(default_factory=list)
    explain: dict[str, Any] = Field(default_factory=dict)


class SynthesisResult(BaseModel):
    answer: str
    cited_atoms: list[str] = Field(default_factory=list)
    tool_call_ids: list[str] = Field(default_factory=list)
    tokens_in: int = 0
    tokens_out: int = 0
    latency_ms: int = 0
