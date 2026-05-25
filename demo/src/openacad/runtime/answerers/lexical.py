"""Keyword Snippets baseline: SQLite FTS5/BM25 over chunks → Answerer agent.

Uses the shared `chunks_fts` virtual table built in `data/shared.sqlite`. No
embedding model in the loop on the retrieval side — matches purely lexical.
"""

import time
from datetime import datetime, timezone
from typing import Any

from openacad.runtime import db
from openacad.runtime.agent_base import build_answerer

TOP_K = 6


def run(question: str, paper_ids: list[str]) -> dict[str, Any]:
    """FTS5 top-K chunks (optionally filtered by source) → LLM. Returns metrics."""
    paper_set = set(paper_ids) if paper_ids else None

    # Over-fetch then filter by source to ensure we have TOP_K within the requested papers.
    hits = db.search_chunks_fts(question, limit=TOP_K * 4)
    chunks = []
    citations = []
    for c in hits:
        if paper_set and c.source_id not in paper_set:
            continue
        chunks.append(c)
        citations.append(c.id)
        if len(chunks) >= TOP_K:
            break

    blocks = [
        f"## {c.id} (pages {c.page_range[0]}-{c.page_range[1]})\n{c.text}"
        for c in chunks
    ]
    prompt = "\n\n".join(blocks) + f"\n\n---\n\nQUESTION: {question}\n\nAnswer:"

    t0 = time.monotonic()
    agent = build_answerer()
    result = agent.run_sync(prompt)
    latency_ms = int((time.monotonic() - t0) * 1000)

    try:
        usage = result.usage
        tokens_in = (usage.input_tokens or usage.request_tokens or 0) if usage else 0
        tokens_out = (usage.output_tokens or usage.response_tokens or 0) if usage else 0
    except Exception:
        tokens_in = tokens_out = 0

    return {
        "pipeline": "B2",
        "answer": result.output,
        "citations": citations,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "latency_ms": latency_ms,
        "n_units_retrieved": len(chunks),
        "run_at": datetime.now(timezone.utc),
    }
