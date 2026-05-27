"""Smoke tests for the read-only Ops Console projections.

These run against the already-seeded `evolving-notes` vault (rung 9). They
check that each projection returns the correct DTO type and that the basic
invariants the spec promises hold (counts ≥ 0, totals match list lengths,
prompt timelines cover every role even when empty, etc.).
"""

from __future__ import annotations

from openacad.projections import (
    curation_summary,
    evals_summary,
    observability_rollup,
    paper_library,
    registry_view,
)
from openacad.projections._models import (
    ActivityFeedItem,
    AtomRow,
    AttributeDef,
    ComparisonRow,
    CostRollupItem,
    CurationView,
    DraftRow,
    EvalsView,
    LatencyBucket,
    MetaProposalRow,
    ObservabilityView,
    PaperLibraryView,
    PaperRow,
    PromptTimeline,
    RegistryView,
    RelationDef,
    RubricRow,
    ToolCallRow,
    VerdictRow,
)


# ── ingest ────────────────────────────────────────────────────────────


def test_paper_library_returns_dto_and_invariants() -> None:
    view = paper_library()

    assert isinstance(view, PaperLibraryView)
    assert view.total_papers == len(view.papers)
    assert view.total_papers >= 0
    assert view.total_chunks >= 0
    assert view.total_atoms >= 0

    # Every row is the right type and has non-negative counts.
    for row in view.papers:
        assert isinstance(row, PaperRow)
        assert row.chunks >= 0
        assert row.atoms >= 0
        assert row.source_id  # non-empty

    # Totals match the sum of row counts.
    assert sum(r.chunks for r in view.papers) == view.total_chunks
    assert sum(r.atoms for r in view.papers) == view.total_atoms

    if view.papers:
        # last_ingested_at must be at least as recent as every row's timestamp.
        assert view.last_ingested_at is not None
        for row in view.papers:
            assert row.ingested_at <= view.last_ingested_at
    else:
        assert view.last_ingested_at is None


# ── registry ──────────────────────────────────────────────────────────


def test_registry_view_returns_dto_and_invariants() -> None:
    view = registry_view()

    assert isinstance(view, RegistryView)
    assert view.total_atoms == len(view.atoms)
    assert view.total_attrs == len(view.attributes)
    assert view.total_rels == len(view.relations)

    for atom in view.atoms:
        assert isinstance(atom, AtomRow)
        assert atom.n_attrs >= 0
        assert atom.n_rels >= 0
        assert atom.atom_id  # non-empty
        # Preview is bounded by the documented 200-char cap.
        assert len(atom.content_preview) <= 200

    for a in view.attributes:
        assert isinstance(a, AttributeDef)
        assert a.usage_count >= 0
        assert a.key

    for r in view.relations:
        assert isinstance(r, RelationDef)
        assert r.usage_count >= 0
        assert r.key

    # Orphan lists must be subsets of the registered keys.
    attr_keys = {a.key for a in view.attributes}
    rel_keys = {r.key for r in view.relations}
    assert set(view.orphan_attrs).issubset(attr_keys)
    assert set(view.orphan_rels).issubset(rel_keys)


# ── curation ──────────────────────────────────────────────────────────


def test_curation_summary_returns_dto_and_invariants() -> None:
    view = curation_summary()

    assert isinstance(view, CurationView)

    # All four verdict kinds (plus pending) must appear in counts.
    for kind in ("accept", "edit", "reject", "deprecate", "pending"):
        assert kind in view.counts
        assert view.counts[kind] >= 0

    assert view.counts["pending"] == len(view.pending_drafts)

    # Verdict count totals match per-kind sum over the history list.
    verdict_kinds = ("accept", "edit", "reject", "deprecate")
    history_counts = {k: 0 for k in verdict_kinds}
    for vr in view.verdict_history:
        assert isinstance(vr, VerdictRow)
        if vr.kind in history_counts:
            history_counts[vr.kind] += 1
    for kind in verdict_kinds:
        assert view.counts[kind] == history_counts[kind]

    for d in view.pending_drafts:
        assert isinstance(d, DraftRow)
        assert d.draft_id

    # History is newest-first.
    if len(view.verdict_history) > 1:
        for prev, nxt in zip(view.verdict_history, view.verdict_history[1:]):
            assert prev.timestamp >= nxt.timestamp


# ── evals ─────────────────────────────────────────────────────────────


def test_evals_summary_returns_dto_and_invariants() -> None:
    view = evals_summary()

    assert isinstance(view, EvalsView)

    for c in view.comparison_runs:
        assert isinstance(c, ComparisonRow)
        assert c.tokens_in >= 0
        assert c.tokens_out >= 0
        assert c.latency_ms >= 0
        assert c.citations >= 0
        assert len(c.answer_preview) <= 200

    for r in view.rubric_scores:
        assert isinstance(r, RubricRow)
        for k, v in r.criteria.items():
            assert isinstance(v, float)

    # rubric_avg_by_criterion only contains keys that appear in at least one
    # rubric submission.
    seen_criteria: set[str] = set()
    for r in view.rubric_scores:
        seen_criteria.update(r.criteria.keys())
    assert set(view.rubric_avg_by_criterion.keys()).issubset(seen_criteria)

    # Prompt timelines: one per role, in deterministic order.
    assert len(view.prompt_timelines) == 4
    role_names = [t.role for t in view.prompt_timelines]
    assert role_names == ["answerer", "extractor", "scorer", "meta_evaluator"]
    for t in view.prompt_timelines:
        assert isinstance(t, PromptTimeline)
        # Versions sorted ascending by created_at.
        for prev, nxt in zip(t.versions, t.versions[1:]):
            assert prev.created_at <= nxt.created_at

    for m in view.meta_proposals:
        assert isinstance(m, MetaProposalRow)
        assert m.event_id
        assert m.target_role
        assert m.insight_kind

    # Meta proposals are newest-first.
    if len(view.meta_proposals) > 1:
        for prev, nxt in zip(view.meta_proposals, view.meta_proposals[1:]):
            assert prev.timestamp >= nxt.timestamp


# ── observability ─────────────────────────────────────────────────────


def test_observability_rollup_returns_dto_and_invariants() -> None:
    view = observability_rollup()

    assert isinstance(view, ObservabilityView)

    # Scalar invariants.
    assert view.n_tool_calls == len(view.tool_calls)
    assert view.n_errors == len(view.errors)
    assert view.avg_latency_ms >= 0
    assert view.total_cost_usd >= 0

    # Histogram covers all 8 documented buckets.
    assert len(view.latency_histogram) == 8
    upper_bounds = [b.upper_ms for b in view.latency_histogram]
    assert upper_bounds == [100, 250, 500, 1000, 2500, 5000, 10000, 10_000_000]
    # Bucket counts sum to total tool calls.
    assert sum(b.count for b in view.latency_histogram) == view.n_tool_calls
    for b in view.latency_histogram:
        assert isinstance(b, LatencyBucket)
        assert b.count >= 0

    # Cost rollups.
    for c in view.cost_by_role:
        assert isinstance(c, CostRollupItem)
        assert c.tokens_in >= 0
        assert c.tokens_out >= 0
        assert c.cost_usd >= 0
    for c in view.cost_by_day:
        assert isinstance(c, CostRollupItem)
        assert c.tokens_in >= 0
        assert c.tokens_out >= 0
        assert c.cost_usd >= 0
    # By-day labels are ISO dates.
    for c in view.cost_by_day:
        assert len(c.bucket_label) == 10  # "YYYY-MM-DD"

    # Errors are a subset of all tool calls.
    error_ids = {t.id for t in view.errors}
    all_ids = {t.id for t in view.tool_calls}
    assert error_ids.issubset(all_ids)
    for t in view.errors:
        assert t.error_message is not None

    # Tool call rows themselves.
    for t in view.tool_calls:
        assert isinstance(t, ToolCallRow)
        assert t.latency_ms >= 0
        assert t.n_results >= 0

    # Activity feed is newest-first and JSON-safe.
    for item in view.activity_feed:
        assert isinstance(item, ActivityFeedItem)
        assert isinstance(item.detail, dict)
        assert item.summary
    if len(view.activity_feed) > 1:
        for prev, nxt in zip(view.activity_feed, view.activity_feed[1:]):
            assert prev.timestamp >= nxt.timestamp

    # Average latency matches the manual computation.
    if view.n_tool_calls:
        expected = sum(t.latency_ms for t in view.tool_calls) / view.n_tool_calls
        assert abs(view.avg_latency_ms - expected) < 1e-6


# ── scenario-key surface ──────────────────────────────────────────────


def test_all_projections_accept_explicit_scenario_key() -> None:
    """Spec: every projection takes scenario_key="evolving-notes" by default
    but accepts other vault keys too. Smoke-test with the same key explicitly."""
    assert isinstance(paper_library("evolving-notes"), PaperLibraryView)
    assert isinstance(registry_view("evolving-notes"), RegistryView)
    assert isinstance(curation_summary("evolving-notes"), CurationView)
    assert isinstance(evals_summary("evolving-notes"), EvalsView)
    assert isinstance(observability_rollup("evolving-notes"), ObservabilityView)
