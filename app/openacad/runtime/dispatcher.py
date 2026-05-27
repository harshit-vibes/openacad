"""Per-scenario orchestration: pick the right pipeline (B0 / B1 / B2 / Atoms),
run it, return a typed AnswerOutput.

This module is the bridge between the scoring openacad.runtime (which knows only Cases)
and the actual baseline/atom services.
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from typing import Any

from openacad.runtime.scenario import Tier, active_scenario, use_scenario
from openacad.feedback.scoring import AnswerOutput


def ask(question: str, paper_ids: list[str] | None = None) -> AnswerOutput:
    """Synchronous entrypoint — picks the pipeline based on the active scenario."""
    s = active_scenario()
    paper_ids = paper_ids or []

    if s.key == "cold-read":
        from openacad.runtime.answerers import cold as baseline_b0
        out = baseline_b0.run(question, paper_ids)
        return AnswerOutput(
            answer=out["answer"],
            cited_units=paper_ids,                 # B0 cites the whole paper
            tokens_in=out["tokens_in"], tokens_out=out["tokens_out"],
            latency_ms=out["latency_ms"],
        )

    if s.key == "semantic-snippets":
        from openacad.runtime.answerers import semantic as baseline_b1
        out = baseline_b1.run(question, paper_ids)
        return AnswerOutput(
            answer=out["answer"],
            cited_units=out["citations"],
            tokens_in=out["tokens_in"], tokens_out=out["tokens_out"],
            latency_ms=out["latency_ms"],
        )

    if s.key == "keyword-snippets":
        from openacad.runtime.answerers import lexical as baseline_b2
        out = baseline_b2.run(question, paper_ids)
        return AnswerOutput(
            answer=out["answer"],
            cited_units=out["citations"],
            tokens_in=out["tokens_in"], tokens_out=out["tokens_out"],
            latency_ms=out["latency_ms"],
        )

    # Atom tier: drafted-notes, curated-notes, evolving-notes
    from openacad.agents.synthesizer import agent as synthesis_agent
    syn = synthesis_agent.ask(question, paper_ids=paper_ids or None)
    return AnswerOutput(
        answer=syn.answer,
        cited_units=syn.cited_atoms,
        tokens_in=syn.tokens_in, tokens_out=syn.tokens_out,
        latency_ms=syn.latency_ms,
    )


async def ask_async(question: str, paper_ids: list[str] | None = None) -> AnswerOutput:
    """Async wrapper so pydantic-evals' async task signature is satisfied."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, lambda: ask(question, paper_ids))


# ── prepare scenario state for atom-tier scenarios ──────────────────────


def prepare_atoms(scenario_key: str, source_ids: list[str] | None = None,
                  auto_accept: bool = False) -> dict[str, Any]:
    """For Drafted/Curated/Evolving: ensure each source has had extraction run and
    drafts curated (auto-accepted if auto_accept=True; left in queue otherwise).

    Idempotent: skips sources that already have drafts or have produced atoms.
    """
    from openacad.runtime import db
    from openacad.notes.intake import from_chunks as extraction_pipeline
    with use_scenario(scenario_key):
        s = active_scenario()
        if s.tier != Tier.ATOMS:
            return {"skipped": "scenario tier is not ATOMS"}
        sources = source_ids or [src.id for src in db.list_sources()]
        results = {}
        for sid in sources:
            existing_drafts = db.drafts_for_source(sid)
            # Skip if drafts already pending or some atoms exist for this source
            atoms_from_source = [a for a in db.list_atom_projections() if a.get("source_id") == sid]
            if existing_drafts or atoms_from_source:
                results[sid] = {
                    "skipped": True,
                    "drafts": len(existing_drafts),
                    "atoms": len(atoms_from_source),
                }
                continue
            drafts = extraction_pipeline.draft(sid)
            extraction_pipeline.validate([d.draft_id for d in drafts])
            extraction_pipeline.score([d.draft_id for d in drafts])
            if auto_accept:
                from openacad.notes.curation import _legacy as curate_service
                accepted = errored = 0
                for d in drafts:
                    fresh = db.get_draft(d.draft_id)
                    if fresh is None or fresh.validation_errors:
                        errored += 1
                        continue
                    # Avoid id collision with any existing atom
                    base = fresh.suggested_id
                    suffix = 1
                    from openacad.notes.persistence import vault as vault_io
                    while vault_io.atom_exists(fresh.suggested_id):
                        fresh.suggested_id = f"{base}-{suffix}"
                        suffix += 1
                    if suffix > 1:
                        db.upsert_draft(fresh)
                    try:
                        curate_service.accept(fresh.draft_id)
                        accepted += 1
                    except ValueError:
                        errored += 1
                results[sid] = {"drafted": len(drafts), "accepted": accepted, "errored": errored}
            else:
                results[sid] = {"drafted": len(drafts), "pending_curate": True}
        return results
