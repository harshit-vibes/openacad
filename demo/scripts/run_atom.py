"""Run the gold question set through tier A (atom-RAG with tool-calling synthesis agent)."""

import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from openacad import compare as compare_service

from openacad.runtime import llm as llm

from openacad.agents.synthesizer import agent as synthesis_agent

from openacad.runtime import db
from datetime import datetime, timezone


def main() -> None:
    if not llm.have_api_key():
        print("no LLM API key — set ANTHROPIC_API_KEY / OPENAI_API_KEY", file=sys.stderr)
        sys.exit(1)

    gold_path = Path(__file__).resolve().parent.parent / "data" / "gold" / "questions.yaml"
    questions = yaml.safe_load(gold_path.read_text())

    sources = db.list_sources()
    default_paper_ids = [s.id for s in sources]

    print(f"# tier-A over {len(questions)} questions")
    for q in questions:
        paper_ids = q.get("paper_ids") or default_paper_ids or []
        print(f"  {q['id']}: {q['question'][:60]}")
        syn = synthesis_agent.ask(q["question"], paper_ids=paper_ids or None)
        a_dict = {
            "pipeline": "A",
            "answer": syn.answer,
            "citations": syn.cited_atoms,
            "tokens_in": syn.tokens_in,
            "tokens_out": syn.tokens_out,
            "latency_ms": syn.latency_ms,
            "n_units_retrieved": len(syn.cited_atoms),
            "tool_call_ids": syn.tool_call_ids,
            "run_at": datetime.now(timezone.utc),
        }
        compare_service._persist(a_dict, q["question"], paper_ids)
        print(f"    A: tokens_in={syn.tokens_in} latency={syn.latency_ms}ms cited={len(syn.cited_atoms)}")


if __name__ == "__main__":
    main()
