"""Evals projection — comparison runs, rubric scores, prompt timelines, and
meta-eval proposals.

Two kinds of "proposals" coexist in the codebase:

- `Proposal` rows in the `proposals` table — registry-evolution proposals.
- `prompt_propose` events in the `events` table — meta-evaluator proposals
  for prompt hardening.

The Evals page is about agent-prompt hardening, so meta_proposals is sourced
from the events table first; if there are none, we fall back to the
`proposals` table so the surface still renders something useful.
"""

from __future__ import annotations

from openacad.feedback.schema import PromptVersion
from openacad.runtime import db
from openacad.runtime.scenario import use_scenario

from openacad.projections._models import (
    ComparisonRow,
    EvalsView,
    MetaProposalRow,
    PromptTimeline,
    RubricRow,
)


_ANSWER_PREVIEW_CHARS = 200
_PROPOSAL_PREVIEW_CHARS = 200
_PROMPT_ROLES: tuple[str, ...] = ("answerer", "extractor", "scorer", "meta_evaluator")


def _avg_by_criterion(rubrics: list[RubricRow]) -> dict[str, float]:
    """Per-criterion mean across every rubric submission."""
    sums: dict[str, float] = {}
    counts: dict[str, int] = {}
    for r in rubrics:
        for k, v in (r.criteria or {}).items():
            try:
                f = float(v)
            except (TypeError, ValueError):
                continue
            sums[k] = sums.get(k, 0.0) + f
            counts[k] = counts.get(k, 0) + 1
    return {k: sums[k] / counts[k] for k in sums if counts.get(k, 0)}


def _rubric_to_row(raw: dict) -> RubricRow:
    # Coerce criteria values to float so the DTO contract holds.
    criteria_raw = raw.get("criteria") or {}
    criteria: dict[str, float] = {}
    for k, v in criteria_raw.items():
        try:
            criteria[k] = float(v)
        except (TypeError, ValueError):
            continue
    ts = raw.get("timestamp")
    from datetime import datetime
    if isinstance(ts, str):
        ts = datetime.fromisoformat(ts)
    return RubricRow(
        id=raw["id"],
        role=raw["role"],
        criteria=criteria,
        timestamp=ts,
        notes=raw.get("free_text") or None,
    )


def _comparison_to_row(c) -> ComparisonRow:
    return ComparisonRow(
        id=c.id,
        question=c.question,
        tokens_in=c.tokens_in,
        tokens_out=c.tokens_out,
        latency_ms=c.latency_ms,
        citations=len(c.citations or []),
        answer_preview=(c.answer or "")[:_ANSWER_PREVIEW_CHARS],
        run_at=c.run_at,
    )


def _prompt_timelines(prompts: list[PromptVersion]) -> list[PromptTimeline]:
    by_role: dict[str, list[PromptVersion]] = {role: [] for role in _PROMPT_ROLES}
    for p in prompts:
        if p.name in by_role:
            by_role[p.name].append(p)
    # Sort each role's versions by created_at ascending so the UI shows
    # the historical chain in order.
    for role in by_role:
        by_role[role].sort(key=lambda pv: pv.created_at)
    return [PromptTimeline(role=role, versions=by_role[role]) for role in _PROMPT_ROLES]


def _meta_proposal_rows_from_events() -> list[MetaProposalRow]:
    """Meta-evaluator proposals emitted as `prompt_propose` events."""
    out: list[MetaProposalRow] = []
    for ev in db.list_events(kind="prompt_propose", limit=500):
        payload = ev.payload or {}
        target_role = (
            payload.get("target_role")
            or payload.get("role")
            or payload.get("name")
            or "unknown"
        )
        insight_kind = (
            payload.get("insight_kind")
            or payload.get("kind")
            or "prompt_propose"
        )
        change_preview = (
            payload.get("proposed_change")
            or payload.get("body")
            or payload.get("rationale")
            or ""
        )
        if isinstance(change_preview, (dict, list)):
            change_preview = str(change_preview)
        out.append(
            MetaProposalRow(
                event_id=ev.id,
                timestamp=ev.timestamp,
                target_role=target_role,
                insight_kind=insight_kind,
                proposed_change_preview=str(change_preview)[:_PROPOSAL_PREVIEW_CHARS],
                based_on_events=list(payload.get("based_on_events") or []),
                state=payload.get("state", "proposed"),
            )
        )
    return out


def _meta_proposal_rows_from_proposals() -> list[MetaProposalRow]:
    """Fallback: pull from the `proposals` table when no events exist."""
    out: list[MetaProposalRow] = []
    for p in db.list_proposals():
        change_preview = p.rationale or str(p.payload or "")
        out.append(
            MetaProposalRow(
                event_id=p.id,
                timestamp=p.proposed_at,
                target_role=p.key,
                insight_kind=p.kind,
                proposed_change_preview=change_preview[:_PROPOSAL_PREVIEW_CHARS],
                based_on_events=[p.triggered_by] if p.triggered_by else [],
                state=p.state,
            )
        )
    return out


def evals_summary(scenario_key: str = "evolving-notes") -> EvalsView:
    with use_scenario(scenario_key):
        comparisons = [_comparison_to_row(c) for c in db.list_comparisons()]
        rubric_rows = [_rubric_to_row(r) for r in db.list_rubric_rows(limit=500)]
        avg = _avg_by_criterion(rubric_rows)
        prompts = db.list_prompts()
        timelines = _prompt_timelines(prompts)

        meta = _meta_proposal_rows_from_events()
        if not meta:
            meta = _meta_proposal_rows_from_proposals()
        # Newest first.
        meta.sort(key=lambda m: m.timestamp, reverse=True)

        return EvalsView(
            comparison_runs=comparisons,
            rubric_scores=rubric_rows,
            rubric_avg_by_criterion=avg,
            prompt_timelines=timelines,
            meta_proposals=meta,
        )
