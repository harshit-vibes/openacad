"""Seed demo fixtures to eliminate zero-state on the Streamlit demo pages.

Four surfaces are seeded for the `evolving-notes` scenario:
  1. Artifact compose history    (events kind="artifact_composed")
  2. Artifact assess history     (events kind="artifact_assessed")
  3. Pending drafts              (drafts table — DraftAtom rows)
  4. Synthetic tool-call errors  (tool_calls with error_message)

All fixtures use an id prefix `fixture-` so `--reset` can wipe just them.

Usage:
    PYTHONPATH=src:. .venv/bin/python scripts/seed_demo_fixtures.py [--reset]
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from openacad.feedback.schema import EvalEvent, ToolCall
from openacad.notes.schema.note import DraftAtom, Relation
from openacad.runtime import db
from openacad.runtime.scenario import use_scenario

SCENARIO_KEY = "evolving-notes"
NOW = datetime.now(timezone.utc)


# ─── Seed 1: artifact_composed events ────────────────────────────────────

COMPOSED_FIXTURES = [
    {
        "artifact_id": "fixture-art-001",
        "title": "Synthesis: SDG 1 strategies for ending extreme poverty",
        "kind": "paper",
        "section_count": 6,
        "citation_count": 24,
        "brief": "Cross-paper synthesis of strategies for SDG 1, weaving claims "
                 "from chapters 1 and 2 with findings on social protection floors.",
        "days_ago": 9,
    },
    {
        "artifact_id": "fixture-art-002",
        "title": "Briefing: Gender equality indicators (SDG 5)",
        "kind": "briefing",
        "section_count": 4,
        "citation_count": 17,
        "brief": "Two-page briefing surfacing SDG 5 indicators most off-track, "
                 "with comparative trend lines drawn from chapter 2 atoms.",
        "days_ago": 7,
    },
    {
        "artifact_id": "fixture-art-003",
        "title": "Chapter: SDGs 6-10 cross-cutting themes",
        "kind": "chapter",
        "section_count": 8,
        "citation_count": 41,
        "brief": "Long-form chapter on water, energy, work, industry and inequality. "
                 "Threads atomic findings into the convergence story across SDGs 6-10.",
        "days_ago": 6,
    },
    {
        "artifact_id": "fixture-art-004",
        "title": "Review: SDG 11-15 implementation gaps",
        "kind": "review",
        "section_count": 5,
        "citation_count": 22,
        "brief": "Critical review of implementation gaps for SDGs 11 through 15, "
                 "drawing on cross-paper contradictions found in chapter 4.",
        "days_ago": 4,
    },
    {
        "artifact_id": "fixture-art-005",
        "title": "Slides: SDG 16-17 — peace, partnerships, and the financing gap",
        "kind": "slides",
        "section_count": 12,
        "citation_count": 18,
        "brief": "12-slide deck distilling the financing gap and partnership "
                 "indicators from chapter 5 into a board-ready narrative.",
        "days_ago": 3,
    },
    {
        "artifact_id": "fixture-art-006",
        "title": "Paper: A unified scorecard across all 17 SDGs",
        "kind": "paper",
        "section_count": 9,
        "citation_count": 56,
        "brief": "Working paper proposing a unified scorecard methodology, "
                 "synthesising signals across all five briefing chapters.",
        "days_ago": 1,
    },
]


# ─── Seed 2: artifact_assessed events ────────────────────────────────────

ASSESSED_FIXTURES = [
    {
        "assessment_id": "fixture-assess-001",
        "target_artifact_id": "fixture-art-001",
        "target_title": "Synthesis: SDG 1 strategies for ending extreme poverty",
        "kind": "coverage",
        "summary": "Coverage review surfaces three missing strands: rural cash transfers, "
                   "climate-poverty interaction, and gender-disaggregated headcount.",
        "coverage_score": 0.72,
        "supporting_count": 18,
        "missing_count": 3,
        "days_ago": 8,
    },
    {
        "assessment_id": "fixture-assess-002",
        "target_artifact_id": "fixture-art-003",
        "target_title": "Chapter: SDGs 6-10 cross-cutting themes",
        "kind": "consistency",
        "summary": "Two internal contradictions detected between the energy-access and "
                   "decent-work sections; sources disagree on 2025 baseline figures.",
        "coverage_score": 0.86,
        "supporting_count": 35,
        "missing_count": 2,
        "days_ago": 5,
    },
    {
        "assessment_id": "fixture-assess-003",
        "target_artifact_id": "fixture-peer-001",
        "target_title": "External: World Bank Poverty & Shared Prosperity 2025",
        "kind": "critique",
        "summary": "Critique of peer review on the World Bank flagship — flags "
                   "methodological gaps in the lower-middle-income projection band.",
        "coverage_score": 0.64,
        "supporting_count": 11,
        "missing_count": 6,
        "days_ago": 3,
    },
    {
        "assessment_id": "fixture-assess-004",
        "target_artifact_id": "fixture-peer-002",
        "target_title": "External: UN SDG Progress Report 2025 — chapter 4 draft",
        "kind": "coverage",
        "summary": "Light coverage gap on indicator 11.6.2 air-quality data; "
                   "otherwise comprehensive across SDGs 11-15.",
        "coverage_score": 0.91,
        "supporting_count": 27,
        "missing_count": 1,
        "days_ago": 2,
    },
]


# ─── Seed 3: pending DraftAtoms ──────────────────────────────────────────

DRAFT_FIXTURES = [
    {
        "draft_id": "fixture-draft-001",
        "suggested_id": "atom-draft-001",
        "type": "claim",
        "content": "Halving extreme poverty by 2030 requires raising annual social-protection "
                   "coverage in low-income countries by at least 2.4 percentage points per year.",
        "tags": ["sdg-1", "poverty", "social-protection"],
        "attributes": {"region": "low-income", "annual_pp_required": 2.4, "horizon": "2030"},
        "days_ago": 4,
        "chunk_idx": 0,
    },
    {
        "draft_id": "fixture-draft-002",
        "suggested_id": "atom-draft-002",
        "type": "finding",
        "content": "Gender parity in primary completion (SDG 4.1) was reached in 73 of 142 "
                   "tracked countries by 2024, but secondary parity lags by 18 percentage points.",
        "tags": ["sdg-4", "sdg-5", "education", "gender-parity"],
        "attributes": {"countries_reached_primary": 73, "total_tracked": 142,
                       "secondary_gap_pp": 18},
        "days_ago": 3,
        "chunk_idx": 0,
    },
    {
        "draft_id": "fixture-draft-003",
        "suggested_id": "atom-draft-003",
        "type": "method",
        "content": "A two-stage difference-in-differences design isolates the causal effect "
                   "of safely managed sanitation rollouts on under-5 mortality (SDG 6.2 -> 3.2).",
        "tags": ["sdg-3", "sdg-6", "method", "causal-inference"],
        "attributes": {"design": "DiD", "outcome": "under5_mortality"},
        "days_ago": 3,
        "chunk_idx": 0,
    },
    {
        "draft_id": "fixture-draft-004",
        "suggested_id": "atom-draft-004",
        "type": "claim",
        "content": "Decoupling material footprint from GDP growth (SDG 8.4) has occurred in only "
                   "21% of OECD economies over the 2015-2024 window.",
        "tags": ["sdg-8", "decoupling", "oecd"],
        "attributes": {"oecd_share_pct": 21, "window": "2015-2024"},
        "days_ago": 2,
        "chunk_idx": 0,
    },
    {
        "draft_id": "fixture-draft-005",
        "suggested_id": "atom-draft-005",
        "type": "finding",
        "content": "City-level PM2.5 exposure (SDG 11.6.2) fell in 58% of large metros but rose "
                   "in 67% of secondary cities between 2018 and 2024.",
        "tags": ["sdg-11", "air-quality", "urban"],
        "attributes": {"large_metro_improving_pct": 58, "secondary_city_worsening_pct": 67},
        "days_ago": 2,
        "chunk_idx": 0,
    },
    {
        "draft_id": "fixture-draft-006",
        "suggested_id": "atom-draft-006",
        "type": "claim",
        "content": "Closing the SDG financing gap requires concessional flows to LDCs to roughly "
                   "double from $35B (2024) to $70B annually by 2027 (SDG 17.2/17.3).",
        "tags": ["sdg-17", "financing", "ldc"],
        "attributes": {"current_usd_b": 35, "required_usd_b": 70, "target_year": 2027},
        "days_ago": 1,
        "chunk_idx": 0,
    },
]


# ─── Seed 4: tool_call errors ────────────────────────────────────────────

ERROR_FIXTURES = [
    {
        "id": "fixture-tc-err-001",
        "session_id": "fixture-session-synthesis-001",
        "agent": "synthesis",
        "tool_name": "traverse",
        "arguments": {"start_atom": "atom-sdg1-001", "relation": "supports", "depth": 12},
        "n_results": 0,
        "latency_ms": 4821,
        "error_message": "RuntimeError: max recursion depth exceeded while traversing "
                         "relation chain (depth=12, fan-out>40 at level 7)",
        "days_ago": 4,
    },
    {
        "id": "fixture-tc-err-002",
        "session_id": "fixture-session-synthesis-002",
        "agent": "synthesis",
        "tool_name": "semantic_search",
        "arguments": {"query": "decoupling material footprint OECD", "k": 25},
        "n_results": 0,
        "latency_ms": 1132,
        "error_message": "ValueError: embedding dimension mismatch (384 != 768) — "
                         "scenario index built with MiniLM-L6 but query encoder is mpnet",
        "days_ago": 2,
    },
    {
        "id": "fixture-tc-err-003",
        "session_id": "fixture-session-synthesis-003",
        "agent": "synthesis",
        "tool_name": "query_atoms",
        "arguments": {"filter": {"tags": ["sdg-17", "financing"]}, "limit": 5000},
        "n_results": 0,
        "latency_ms": 30014,
        "error_message": "TimeoutError: semantic search exceeded 30s deadline "
                         "while expanding tag-union over 12 scenarios",
        "days_ago": 1,
    },
]


# ─── helpers ─────────────────────────────────────────────────────────────


def _ts_dt(days_ago: int) -> datetime:
    return NOW - timedelta(days=days_ago)


def _event_id_for(prefix: str, ix: int) -> str:
    return f"fixture-ev-{prefix}-{ix:03d}"


def _delete_fixtures() -> tuple[int, int, int]:
    """Reset: remove rows whose ids start with 'fixture-'. Returns (events, drafts, tcs)."""
    with db.transaction("scenario") as c:
        ev = c.execute("DELETE FROM events WHERE id LIKE 'fixture-%'").rowcount
        dr = c.execute("DELETE FROM drafts WHERE draft_id LIKE 'fixture-%'").rowcount
        tc = c.execute("DELETE FROM tool_calls WHERE id LIKE 'fixture-%'").rowcount
    return ev, dr, tc


def _fixtures_already_present() -> bool:
    """Quick check: any fixture-prefixed event already in events table."""
    row = db._scenario().execute(
        "SELECT COUNT(*) AS n FROM events WHERE id LIKE 'fixture-%'"
    ).fetchone()
    return (row["n"] or 0) > 0


def _seed_composed() -> int:
    n = 0
    for ix, f in enumerate(COMPOSED_FIXTURES, start=1):
        eid = _event_id_for("composed", ix)
        payload = {
            "artifact_id": f["artifact_id"],
            "title": f["title"],
            "kind": f["kind"],
            "section_count": f["section_count"],
            "citation_count": f["citation_count"],
            "brief": f["brief"],
        }
        db.log_event(EvalEvent(
            id=eid,
            timestamp=_ts_dt(f["days_ago"]),
            kind="artifact_composed",
            actor="scholar",
            payload=payload,
        ))
        n += 1
    return n


def _seed_assessed() -> int:
    n = 0
    for ix, f in enumerate(ASSESSED_FIXTURES, start=1):
        eid = _event_id_for("assessed", ix)
        payload = {
            "assessment_id": f["assessment_id"],
            "target_artifact_id": f["target_artifact_id"],
            "target_title": f["target_title"],
            "kind": f["kind"],
            "summary": f["summary"],
            "coverage_score": f["coverage_score"],
            "supporting_count": f["supporting_count"],
            "missing_count": f["missing_count"],
        }
        db.log_event(EvalEvent(
            id=eid,
            timestamp=_ts_dt(f["days_ago"]),
            kind="artifact_assessed",
            actor="meta_evaluator",
            payload=payload,
        ))
        n += 1
    return n


def _seed_drafts() -> int:
    sources = db.list_sources()
    if not sources:
        return 0
    n = 0
    for ix, f in enumerate(DRAFT_FIXTURES):
        src = sources[ix % len(sources)]
        chunk_id = f"{src.id}-c{f['chunk_idx']:03d}"
        draft = DraftAtom(
            draft_id=f["draft_id"],
            drafted_at=_ts_dt(f["days_ago"]),
            prompt_version="extractor.v3",
            source_id=src.id,
            chunk_ids=[chunk_id],
            page_range=(1, 4),
            type=f["type"],
            suggested_id=f["suggested_id"],
            tags=f["tags"],
            attributes=f["attributes"],
            relations=[Relation(type="from_source", target=src.id)],
            content=f["content"],
            confidence_score=0.78,
            validation_errors=[],
        )
        db.upsert_draft(draft)
        n += 1
    return n


def _seed_errors() -> int:
    n = 0
    for f in ERROR_FIXTURES:
        tc = ToolCall(
            id=f["id"],
            session_id=f["session_id"],
            agent=f["agent"],
            tool_name=f["tool_name"],
            arguments=f["arguments"],
            n_results=f["n_results"],
            latency_ms=f["latency_ms"],
            timestamp=_ts_dt(f["days_ago"]),
            error_message=f["error_message"],
        )
        db.log_tool_call(tc)
        n += 1
    return n


# ─── main ────────────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed demo fixtures for evolving-notes scenario.")
    parser.add_argument(
        "--reset", action="store_true",
        help="Delete prior fixture rows (id LIKE 'fixture-%%') before seeding."
    )
    args = parser.parse_args()

    with use_scenario(SCENARIO_KEY):
        if args.reset:
            ev, dr, tc = _delete_fixtures()
            print(f"[reset] cleared fixtures: events={ev} drafts={dr} tool_calls={tc}")
        else:
            if _fixtures_already_present():
                print("[skip] fixture events already exist; pass --reset to re-seed.")
                return 0

        n_composed = _seed_composed()
        n_assessed = _seed_assessed()
        n_drafts = _seed_drafts()
        n_errors = _seed_errors()

    print(f"[seed] composed events:   {n_composed}")
    print(f"[seed] assessed events:   {n_assessed}")
    print(f"[seed] pending drafts:    {n_drafts}")
    print(f"[seed] tool-call errors:  {n_errors}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
