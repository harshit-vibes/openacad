"""Compose an artifact from a notes vault.

MVP orchestrator: takes a brief (the artifact's topic + section outline) and
runs the active scenario's answerer against each section. The answerer's
output becomes the section body; the cited atoms become the section's
note_citations.

Real composition would have a separate Planner agent + per-section Drafter
agents + an Assembler. V1 is "ask the synthesizer 5 questions, glue results."
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from openacad.artifacts.schema import Artifact, ArtifactKind, ArtifactSection
from openacad.runtime.scenario import active_scenario
from openacad.runtime import dispatcher
from openacad.feedback.timeline import log_event


def compose(
    kind: ArtifactKind,
    title: str,
    sections: list[str],
    paper_ids: list[str] | None = None,
    brief: str = "",
) -> Artifact:
    """Compose a fresh artifact by asking the answerer one question per section.

    `sections` is a list of section titles. Each title is sent verbatim as the
    question (prefixed with "Write the section: ...") to the active scenario's
    answerer; the answer becomes the body, the cited atoms become the section's
    note_citations.
    """
    s = active_scenario()
    artifact_id = f"art-{uuid.uuid4().hex[:8]}"
    composed_sections: list[ArtifactSection] = []
    all_citations: list[str] = []

    for section_title in sections:
        question = f"Write the {kind} section titled '{section_title}'. {brief}".strip()
        try:
            out = dispatcher.ask(question, paper_ids or [])
            body = out.answer
            citations = out.cited_units
        except Exception as e:
            body = f"_(section drafting failed: {e})_"
            citations = []

        composed_sections.append(ArtifactSection(
            title=section_title,
            body=body,
            note_citations=citations,
        ))
        all_citations.extend(citations)

    artifact = Artifact(
        id=artifact_id,
        kind=kind,
        title=title,
        created_at=datetime.now(timezone.utc),
        scenario_key=s.key,
        brief=brief,
        sections=composed_sections,
        note_citations=list(dict.fromkeys(all_citations)),  # dedupe, preserve order
        metadata={"composer_version": "mvp-v1", "section_count": len(sections)},
    )

    log_event("artifact_composed", {
        "artifact_id": artifact_id,
        "kind": kind,
        "title": title,
        "section_count": len(sections),
        "citation_count": len(artifact.note_citations),
    })
    return artifact


__all__ = ["compose"]
