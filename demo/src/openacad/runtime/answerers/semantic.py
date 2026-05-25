"""B1 baseline: vector RAG over PDF chunks. Top-K chunks → LLM.

Uses the same MiniLM embeddings the atom layer uses (chunks_store), so the
comparison against tier A is apples-to-apples on the embedding model.
"""

import time
from datetime import datetime, timezone
from typing import Any

from pydantic_ai import Agent

from openacad.notes.query import semantic as semantic_service
from openacad.runtime import db
from openacad.runtime.llm import model_string, settings_for

TOP_K = 6


def _agent() -> Agent:
    return Agent(
        model_string("synthesis"),
        output_type=str,
        model_settings=settings_for("synthesis"),
        system_prompt=(
            "You answer research questions strictly from the provided text chunks. "
            "If the answer cannot be found in the chunks, say so. "
            "Cite chunk ids inline like (c-paper-xyz-0042) and page ranges when given."
        ),
        retries=1,
    )


def run(question: str, paper_ids: list[str]) -> dict[str, Any]:
    """Top-K chunks by cosine similarity → LLM. Returns metrics + answer."""
    store = semantic_service.chunks_store()
    if len(store) == 0:
        return {
            "pipeline": "B1",
            "answer": "(no chunk embeddings indexed; run `cli ingest` first)",
            "citations": [],
            "tokens_in": 0,
            "tokens_out": 0,
            "latency_ms": 0,
            "n_units_retrieved": 0,
            "run_at": datetime.now(timezone.utc),
        }

    hits = store.search(question, limit=TOP_K * 4)  # over-fetch then filter by source
    paper_set = set(paper_ids)
    chunks: list[Any] = []
    citations: list[str] = []
    for chunk_id, _score in hits:
        c = db.get_chunk(chunk_id)
        if c is None:
            continue
        if c.source_id not in paper_set:
            continue
        chunks.append(c)
        citations.append(c.id)
        if len(chunks) >= TOP_K:
            break

    blocks = [
        f"## {c.id} (pages {c.page_range[0]}-{c.page_range[1]})\n{c.text}" for c in chunks
    ]
    prompt = "\n\n".join(blocks) + f"\n\n---\n\nQUESTION: {question}\n\nAnswer:"

    t0 = time.monotonic()
    result = _agent().run_sync(prompt)
    latency_ms = int((time.monotonic() - t0) * 1000)

    try:
        usage = result.usage
        tokens_in = (usage.input_tokens or usage.request_tokens or 0) if usage else 0
        tokens_out = (usage.output_tokens or usage.response_tokens or 0) if usage else 0
    except Exception:
        tokens_in = tokens_out = 0

    return {
        "pipeline": "B1",
        "answer": result.output,
        "citations": citations,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "latency_ms": latency_ms,
        "n_units_retrieved": len(chunks),
        "run_at": datetime.now(timezone.utc),
    }
