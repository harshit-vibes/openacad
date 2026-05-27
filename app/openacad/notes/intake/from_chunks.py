"""Three-stage extraction orchestrator.

draft    — run extraction agent over a source's chunks → persist DraftAtoms
validate — registry strict-validate each draft → list of errors per draft
score    — confidence + duplicate detection → confidence_score per draft

Designed so each stage is a separate endpoint (Phase 2 design decision) but the
pipeline can also be run end-to-end via `draft → validate → score`.
"""

import uuid
from datetime import datetime, timezone

from pydantic_ai.usage import UsageLimits

from openacad.notes.schema import AtomicNote, DraftAtom, Metas, Origin, ProposedAtom

# The extractor declares 4 openacad (list_attribute_keys, check_registry,
# find_similar_atoms, get_chunk_context) and routinely chains 30-80 tool calls
# on dense chunks before emitting the final ProposedAtom list. PydanticAI's
# default request_limit=50 fires partway through. 250 is a comfortable ceiling
# that still prevents runaway loops.
EXTRACTION_USAGE_LIMITS = UsageLimits(request_limit=250)
from openacad.notes.query import semantic as semantic_service
from openacad.runtime import db
from openacad.notes.persistence import vault as vault_io
from openacad.agents.extractor.agent import ExtractionDeps, build_context_block, get_agent

CURRENT_EXTRACTION_PROMPT = "extraction.v1"


def now() -> datetime:
    return datetime.now(timezone.utc)


# ── stage 1: draft ──────────────────────────────────────────────────────


def draft(source_id: str, chunk_ids: list[str] | None = None, window_size: int = 5) -> list[DraftAtom]:
    """Run the extraction agent over the source's chunks; persist drafts; return them.

    Chunks are batched into windows of `window_size` to keep context manageable.
    """
    source = db.get_source(source_id)
    if not source:
        raise ValueError(f"source {source_id} not found")

    all_chunks = db.chunks_for_source(source_id)
    if chunk_ids:
        wanted = set(chunk_ids)
        all_chunks = [c for c in all_chunks if c.id in wanted]
    if not all_chunks:
        return []

    agent = get_agent()
    deps = ExtractionDeps(source_id=source_id)
    out: list[DraftAtom] = []

    for i in range(0, len(all_chunks), window_size):
        window = all_chunks[i : i + window_size]
        context = build_context_block(source_id, window)
        result = agent.run_sync(context, deps=deps, usage_limits=EXTRACTION_USAGE_LIMITS)
        proposed: list[ProposedAtom] = result.output

        page_lo = min(c.page_range[0] for c in window)
        page_hi = max(c.page_range[1] for c in window)
        chunk_ids_in_window = [c.id for c in window]
        drafted_at = now()

        # Capability scrub — the active scenario's flags decide whether the
        # extractor's attribute/relation output is honored or zeroed out. The
        # prompt itself instructs the agent, but LLMs are noisy — enforce here
        # so a drafted atom in atoms-only NEVER carries attributes/relations.
        from openacad.runtime.scenario import active_scenario
        scn = active_scenario()
        keep_attrs = scn.has_attributes
        keep_rels = scn.has_relations

        for p in proposed:
            d = DraftAtom(
                draft_id=f"dr-{uuid.uuid4().hex[:8]}",
                drafted_at=drafted_at,
                prompt_version=CURRENT_EXTRACTION_PROMPT,
                source_id=source_id,
                chunk_ids=chunk_ids_in_window,
                page_range=(page_lo, page_hi),
                type=p.type,
                suggested_id=p.suggested_id,
                tags=p.tags,
                attributes=p.attributes if keep_attrs else {},
                relations=p.relations if keep_rels else [],
                content=p.content,
            )
            db.upsert_draft(d)
            out.append(d)

    return out


# ── stage 2: validate ───────────────────────────────────────────────────


def validate(draft_ids: list[str]) -> dict[str, list[str]]:
    """Registry strict-validate each draft. Returns {draft_id: [errors]}."""
    from openacad.notes.registry._legacy import validate_atom

    out: dict[str, list[str]] = {}
    drafts = [db.get_draft(did) for did in draft_ids]
    drafts = [d for d in drafts if d is not None]

    # Build extra_atoms list so a draft can reference another draft's suggested_id.
    extras = [_draft_as_atom(d) for d in drafts]

    for d in drafts:
        atom = _draft_as_atom(d)
        errors = validate_atom(atom, extra_atoms=extras)
        out[d.draft_id] = errors
        d.validation_errors = errors
        db.upsert_draft(d)

    return out


# ── stage 3: score ──────────────────────────────────────────────────────


def score(draft_ids: list[str]) -> dict[str, float]:
    """Confidence + duplicate score for each draft. Returns {draft_id: score in [0,1]}."""
    out: dict[str, float] = {}
    drafts = [db.get_draft(did) for did in draft_ids]
    drafts = [d for d in drafts if d is not None]
    store = semantic_service.atoms_store()

    for d in drafts:
        n_errs = len(d.validation_errors)
        validity_score = max(0.0, 1.0 - 0.2 * n_errs)

        dup_score = 1.0
        if d.content and len(store) > 0:
            hits = store.search(d.content, limit=1)
            if hits:
                _, sim = hits[0]
                if sim > 0.85:
                    dup_score = max(0.0, 1.0 - (sim - 0.85) * 6)  # decays past threshold

        score_val = min(validity_score, dup_score)
        d.confidence_score = round(score_val, 3)
        db.upsert_draft(d)
        out[d.draft_id] = d.confidence_score

    return out


# ── helpers ─────────────────────────────────────────────────────────────


def _draft_as_atom(d: DraftAtom) -> AtomicNote:
    """Wrap a draft as an AtomicNote for validation purposes (no commit)."""
    return AtomicNote(
        metas=Metas(
            id=d.suggested_id,
            type=d.type,
            status="draft",
            created_at=d.drafted_at,
            updated_at=d.drafted_at,
            tags=d.tags,
        ),
        origin=Origin(
            source_id=d.source_id,
            chunk_ids=d.chunk_ids,
            page_range=d.page_range,
            prompt_version=d.prompt_version,
            scholar_action="seeded",  # pre-commit; real action set on accept
        ),
        attributes=d.attributes,
        relations=d.relations,
        content=d.content,
    )
