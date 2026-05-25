"""Run the gold question set through B0 (full-doc) + B1 (vector RAG) baselines.

Requires:
  - PDFs ingested via `cli ingest …`
  - LLM API key set in .env
"""

import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from openacad.runtime.answerers import cold as baseline_b0
from openacad.runtime.answerers import semantic as baseline_b1
from openacad import compare as compare_service

from openacad.runtime import llm as llm

from openacad.runtime import db
def main() -> None:
    if not llm.have_api_key():
        print("no LLM API key — set ANTHROPIC_API_KEY / OPENAI_API_KEY", file=sys.stderr)
        sys.exit(1)

    gold_path = Path(__file__).resolve().parent.parent / "data" / "gold" / "questions.yaml"
    questions = yaml.safe_load(gold_path.read_text())

    sources = db.list_sources()
    default_paper_ids = [s.id for s in sources]

    print(f"# baselines over {len(questions)} questions, {len(sources)} ingested papers")
    for q in questions:
        paper_ids = q.get("paper_ids") or default_paper_ids
        if not paper_ids:
            print(f"  {q['id']}: no papers ingested; B0/B1 skipped")
            continue
        print(f"  {q['id']}: {q['question'][:60]}")
        r0 = compare_service._persist(baseline_b0.run(q["question"], paper_ids), q["question"], paper_ids)
        r1 = compare_service._persist(baseline_b1.run(q["question"], paper_ids), q["question"], paper_ids)
        print(f"    B0: tokens_in={r0.tokens_in} latency={r0.latency_ms}ms")
        print(f"    B1: tokens_in={r1.tokens_in} latency={r1.latency_ms}ms")


if __name__ == "__main__":
    main()
