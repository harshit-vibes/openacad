"""B0 baseline: dump the full document text into the LLM context, ask the question.

Highest token cost; hallucination-prone; page-range citations at best. The honest
'naive' baseline that tier A is measured against.
"""

import time
from datetime import datetime, timezone
from typing import Any

from pydantic_ai import Agent

from openacad.runtime.settings import settings
from openacad.runtime import db
from openacad.runtime.llm import model_string, settings_for


def _agent() -> Agent:
    return Agent(
        model_string("synthesis"),
        output_type=str,
        model_settings=settings_for("synthesis"),
        system_prompt=(
            "You answer research questions strictly from the provided document text. "
            "If the answer cannot be found, say so. Cite page ranges when possible: (pp. X-Y)."
        ),
        retries=1,
    )


def run(question: str, paper_ids: list[str]) -> dict[str, Any]:
    """Send full source text(s) + question to the LLM. Returns metrics + answer."""
    text_blocks: list[str] = []
    pages_per_paper: dict[str, int] = {}
    for pid in paper_ids:
        source = db.get_source(pid)
        if not source:
            continue
        chunks = db.chunks_for_source(pid)
        pages_per_paper[pid] = source.n_pages
        text_blocks.append(f"# {pid} ({source.title or source.filename}, {source.n_pages} pages)\n")
        text_blocks.extend(c.text for c in chunks)

    full_text = "\n\n".join(text_blocks)
    prompt = f"{full_text}\n\n---\n\nQUESTION: {question}\n\nAnswer:"

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
        "pipeline": "B0",
        "answer": result.output,
        "citations": [],  # page ranges would need extraction; we leave it empty for v1
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "latency_ms": latency_ms,
        "n_units_retrieved": len(paper_ids),  # whole papers
        "run_at": datetime.now(timezone.utc),
    }
