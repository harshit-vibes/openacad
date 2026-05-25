"""Typed artifact entities — papers, chapters, reviews, briefings, assessments.

An artifact is the OUTPUT side of openacad: notes go in, artifacts come out
(composition) or external artifacts come in and produce assessments
(assessment).
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


ArtifactKind = Literal["paper", "chapter", "review", "briefing", "slides", "assessment"]


class ArtifactSection(BaseModel):
    title: str
    body: str
    note_citations: list[str] = Field(default_factory=list)


class Artifact(BaseModel):
    id: str
    kind: ArtifactKind
    title: str
    created_at: datetime
    scenario_key: str
    brief: str = ""
    sections: list[ArtifactSection] = Field(default_factory=list)
    note_citations: list[str] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)


class Assessment(BaseModel):
    """Output of artifacts/assessment/* run against a notes vault."""
    id: str
    target_artifact_id: str
    created_at: datetime
    scenario_key: str
    kind: Literal["consistency", "coverage", "support", "critique", "gap"]
    summary: str
    findings: list[dict] = Field(default_factory=list)
    supporting_notes: list[str] = Field(default_factory=list)
    contradicting_notes: list[str] = Field(default_factory=list)
    missing_topics: list[str] = Field(default_factory=list)


__all__ = ["Artifact", "ArtifactKind", "ArtifactSection", "Assessment"]
