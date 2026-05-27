"""Seed past-query history across all 9 scenarios.

Runs a canonical set of demo questions against every scenario via
`runtime.dispatcher.ask()` and persists each result as a ComparisonResult so
the Query tab's "Past queries" section + the Numbers / Conclusion pages
have real data to showcase.

Cost (gpt-4o-mini, 4 questions × 9 scenarios = 36 LLM calls):
  cold-read: ~5-15k tokens per call (whole PDF in prompt)
  chunk-tier: ~1-2k tokens per call
  atom-tier: ~5-10k tokens per call (multiple tool calls)
  → estimated total ~$0.05 - $0.10

Usage:
  python scripts/seed_query_history.py                  # all 9 scenarios × all questions
  python scripts/seed_query_history.py cold-read        # one scenario, all questions
  python scripts/seed_query_history.py --skip-existing  # don't re-run questions already in DB
"""

from __future__ import annotations

import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from openacad.runtime.scenario import SCENARIOS, SCENARIOS_BY_KEY, use_scenario
from openacad.runtime import db, dispatcher
from openacad.feedback.schema import ComparisonResult


# Canonical demo questions and which paper each one is "about".
# The paper restriction keeps Cold Read's token cost bounded and gives
# chunk/atom retrievers a focused haystack.
DEMO_QUESTIONS: list[tuple[str, str]] = [
    (
        "What are the main strategies for ending poverty (SDG 1)?",
        "paper-sdg-briefing-ch02-sdg-1-5-people",
    ),
    (
        "What targets does SDG 5 (gender equality) include?",
        "paper-sdg-briefing-ch02-sdg-1-5-people",
    ),
    (
        "How does SDG 2 frame food security and nutrition?",
        "paper-sdg-briefing-ch02-sdg-1-5-people",
    ),
    (
        "What indicators are used to track SDG 3 (good health)?",
        "paper-sdg-briefing-ch02-sdg-1-5-people",
    ),
    (
        "What does the briefing say about clean water (SDG 6) and clean energy (SDG 7)?",
        "paper-sdg-briefing-ch03-sdg-6-10",
    ),
    (
        "How are decent work (SDG 8) and economic growth interconnected in the briefing?",
        "paper-sdg-briefing-ch03-sdg-6-10",
    ),
    (
        "What role do industry and innovation play in SDG 9?",
        "paper-sdg-briefing-ch03-sdg-6-10",
    ),
    (
        "Which urban sustainability goals are discussed in SDG 11?",
        "paper-sdg-briefing-ch04-sdg-11-15",
    ),
    (
        "Which SDGs are about peace, justice, and partnerships?",
        "paper-sdg-briefing-ch05-sdg-16-17-peace",
    ),
    (
        "What partnerships and global cooperation themes recur across the briefing?",
        "paper-sdg-briefing-ch05-sdg-16-17-peace",
    ),
]


def _pipeline_for(scenario_key: str) -> str:
    return {
        "cold-read": "B0",
        "semantic-snippets": "B1",
        "keyword-snippets": "B2",
    }.get(scenario_key, "A")


def _already_has(question: str, scenario_key: str) -> bool:
    """Return True if this exact question is already persisted for the scenario."""
    with use_scenario(scenario_key):
        existing = db.list_comparisons()
    return any(c.question == question for c in existing)


def run_one(scenario_key: str, question: str, paper_id: str, skip_existing: bool) -> dict:
    if skip_existing and _already_has(question, scenario_key):
        return {"status": "skipped", "reason": "already in DB"}

    try:
        with use_scenario(scenario_key):
            out = dispatcher.ask(question, [paper_id])
            cr = ComparisonResult(
                id=f"cmp-{uuid.uuid4().hex[:8]}",
                question=question,
                paper_ids=[paper_id],
                pipeline=_pipeline_for(scenario_key),
                answer=out.answer,
                citations=out.cited_units,
                tokens_in=out.tokens_in,
                tokens_out=out.tokens_out,
                latency_ms=out.latency_ms,
                n_units_retrieved=len(out.cited_units),
                run_at=datetime.now(timezone.utc),
            )
            db.insert_comparison(cr)
        return {
            "status": "ok",
            "tokens": out.tokens_in + out.tokens_out,
            "latency_ms": out.latency_ms,
            "citations": len(out.cited_units),
        }
    except Exception as e:
        return {"status": "error", "reason": str(e)[:120]}


def main() -> None:
    args = sys.argv[1:]
    skip_existing = "--skip-existing" in args
    args = [a for a in args if not a.startswith("--")]
    target_keys = args if args else [s.key for s in SCENARIOS]

    unknown = [k for k in target_keys if k not in SCENARIOS_BY_KEY]
    if unknown:
        print(f"ERROR: unknown scenarios: {unknown}", file=sys.stderr)
        sys.exit(1)

    print(f"== seed query history ==")
    print(f"  scenarios:      {target_keys}")
    print(f"  questions:      {len(DEMO_QUESTIONS)}")
    print(f"  skip existing:  {skip_existing}")
    print(f"  total LLM runs: {len(target_keys) * len(DEMO_QUESTIONS)}\n")

    grand_total_tokens = 0
    for sk in target_keys:
        print(f"— {sk} —")
        for q, paper in DEMO_QUESTIONS:
            short_q = q[:60] + ("…" if len(q) > 60 else "")
            print(f"  ❓ {short_q}", flush=True)
            r = run_one(sk, q, paper, skip_existing)
            if r["status"] == "ok":
                grand_total_tokens += r["tokens"]
                print(f"    ✓ {r['tokens']} tokens · {r['latency_ms']}ms · {r['citations']} citations")
            elif r["status"] == "skipped":
                print(f"    ⏭ skipped ({r['reason']})")
            else:
                print(f"    ✗ error: {r['reason']}")
        print()

    print(f"done. grand total tokens: {grand_total_tokens:,}")


if __name__ == "__main__":
    main()
