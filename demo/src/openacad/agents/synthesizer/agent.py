"""PydanticAI synthesis agent — tool-calling Q&A and longer-form synthesis.

The agent receives the question + a registry summary; it picks its retrieval
strategy by calling openacad that return verified data from our stores. The
answer is required to cite every claim with [[atom-id]].

Tool calls are extracted from the model's message trace and logged to SQLite.
"""

import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from pydantic_ai import Agent, RunContext

from openacad.runtime.settings import settings
from openacad.notes.schema import AtomicNote, AtomKind
from openacad.runtime.queries import SynthesisResult
from openacad.feedback.schema import ToolCall
from openacad.notes.query import hybrid as retrieval
from openacad.runtime import db
from openacad.notes.persistence import vault as vault_io
from openacad.runtime.llm import model_string, settings_for
from openacad.notes.registry.validation import get_schema


def now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class SynthesisDeps:
    session_id: str


def _load_system_prompt() -> str:
    return (settings.prompts_dir / "synthesis" / "v1.md").read_text(encoding="utf-8")


def _log_tool_call(
    session_id: str,
    tool: str,
    args: dict,
    n_results: int,
    ms: int,
    error: str | None = None,
) -> None:
    db.log_tool_call(
        ToolCall(
            id=f"tc-{uuid.uuid4().hex[:8]}",
            session_id=session_id,
            agent="synthesis",
            tool_name=tool,
            arguments=args,
            n_results=n_results,
            latency_ms=ms,
            timestamp=now(),
            error_message=error,
        )
    )


def _build_agent_with_prompt(body: str) -> Agent:
    """Build a tool-calling Answerer agent with the given system-prompt body.
    Used by openacad.runtime.agent_base.build_answerer() for scenario-aware
    construction. The legacy `_build_agent()` calls this with the on-disk v1."""
    agent = Agent(
        model_string("synthesis"),
        deps_type=SynthesisDeps,
        output_type=SynthesisResult,
        system_prompt=body,
        retries=2,
        model_settings=settings_for("synthesis"),
    )

    @agent.tool
    def query_atoms(
        ctx: RunContext[SynthesisDeps],
        type: AtomKind | None = None,
        where: dict[str, Any] | None = None,
    ) -> list[AtomicNote]:
        """SQL-style attribute query. Use for typed filters (domain, evidence, etc)."""
        t0 = time.monotonic()
        args = {"type": type, "where": where}
        try:
            atoms = retrieval.query(type=type, where=where, limit=10).atoms
            _log_tool_call(ctx.deps.session_id, "query_atoms", args, len(atoms), int((time.monotonic() - t0) * 1000))
            return atoms
        except Exception as e:
            _log_tool_call(ctx.deps.session_id, "query_atoms", args, 0, int((time.monotonic() - t0) * 1000), error=str(e))
            raise

    @agent.tool
    def traverse(
        ctx: RunContext[SynthesisDeps],
        atom_id: str,
        via: list[str],
        hops: int = 1,
    ) -> list[AtomicNote]:
        """Graph traversal. Use to follow relations from a known atom."""
        t0 = time.monotonic()
        args = {"atom_id": atom_id, "via": via, "hops": hops}
        try:
            atoms = retrieval.query(related_to=atom_id, via=via, hops=hops, limit=10).atoms
            _log_tool_call(ctx.deps.session_id, "traverse", args, len(atoms), int((time.monotonic() - t0) * 1000))
            return atoms
        except Exception as e:
            _log_tool_call(ctx.deps.session_id, "traverse", args, 0, int((time.monotonic() - t0) * 1000), error=str(e))
            raise

    @agent.tool
    def semantic_search(
        ctx: RunContext[SynthesisDeps],
        query: str,
        limit: int = 10,
    ) -> list[AtomicNote]:
        """Cosine search over atom embeddings. Use for fuzzy 'similar in meaning' lookups."""
        t0 = time.monotonic()
        args = {"query": query, "limit": limit}
        try:
            atoms = retrieval.query(semantic=query, limit=limit).atoms
            _log_tool_call(ctx.deps.session_id, "semantic_search", args, len(atoms), int((time.monotonic() - t0) * 1000))
            return atoms
        except Exception as e:
            _log_tool_call(ctx.deps.session_id, "semantic_search", args, 0, int((time.monotonic() - t0) * 1000), error=str(e))
            raise

    @agent.tool
    def get_atom_full(ctx: RunContext[SynthesisDeps], atom_id: str) -> AtomicNote | None:
        """Fetch the full atom body when a summary from another tool is insufficient."""
        t0 = time.monotonic()
        args = {"atom_id": atom_id}
        try:
            a = vault_io.read_atom(atom_id)
            _log_tool_call(ctx.deps.session_id, "get_atom_full", args, 1, int((time.monotonic() - t0) * 1000))
            return a
        except Exception as e:
            # Preserve existing contract: missing atom → return None (do not raise).
            # But surface the cause in the tool_calls log for observability.
            _log_tool_call(ctx.deps.session_id, "get_atom_full", args, 0, int((time.monotonic() - t0) * 1000), error=str(e))
            return None

    @agent.tool
    def check_contradiction(
        ctx: RunContext[SynthesisDeps],
        atom_a: str,
        atom_b: str,
    ) -> bool:
        """Does atom A have a 'contradicts' relation to atom B (or vice versa)?"""
        t0 = time.monotonic()
        args = {"atom_a": atom_a, "atom_b": atom_b}
        try:
            out = retrieval.has_relation(atom_a, atom_b, "contradicts") or retrieval.has_relation(atom_b, atom_a, "contradicts")
            _log_tool_call(ctx.deps.session_id, "check_contradiction", args, 1 if out else 0, int((time.monotonic() - t0) * 1000))
            return out
        except Exception as e:
            _log_tool_call(ctx.deps.session_id, "check_contradiction", args, 0, int((time.monotonic() - t0) * 1000), error=str(e))
            raise

    return agent


def _build_agent() -> Agent:
    """Legacy: build with the on-disk v1 prompt (no scenario awareness)."""
    return _build_agent_with_prompt(_load_system_prompt())


def get_agent() -> Agent:
    """Return the scenario-active Answerer agent (atom-tier path).

    Routes through agent_factory so prompt-version promotion is hot-reloaded.
    """
    from openacad.runtime.agent_base import build_answerer
    return build_answerer()


def _registry_preamble() -> str:
    """Compact registry summary to prime the agent (reduces tool roundtrips)."""
    schema = get_schema()
    lines = ["## registry"]
    lines.append("types: " + ", ".join(sorted(schema.types.keys())))
    if schema.attributes:
        attrs = sorted(schema.attributes.values(), key=lambda d: -d.usage_count)[:12]
        lines.append("top attributes:")
        for d in attrs:
            allowed = f" allowed={d.allowed_values}" if d.allowed_values else ""
            lines.append(f"  - {d.key}: {d.value_type}{allowed}")
    if schema.relations:
        rels = sorted(schema.relations.values(), key=lambda d: -d.usage_count)[:12]
        lines.append("top relations:")
        for d in rels:
            inv = f" ↔ {d.inverse}" if d.inverse else ""
            lines.append(f"  - {d.key}{inv}  (src={d.source_types}, tgt={d.target_types})")
    return "\n".join(lines)


def ask(question: str, paper_ids: list[str] | None = None) -> SynthesisResult:
    """Run the synthesis agent on a question. Returns answer + cited atoms + token usage."""
    agent = get_agent()
    session_id = f"synth-{uuid.uuid4().hex[:8]}"
    deps = SynthesisDeps(session_id=session_id)

    user_block = f"{_registry_preamble()}\n\n## question\n{question}"
    # NOTE: do NOT inject a "restrict to sources" line. For atom-tier scenarios
    # the agent's openacad have no source_id filter, and seeing the restriction in
    # the prompt causes it to give up rather than searching. For chunk-tier
    # scenarios the source filtering is already applied by the baseline runner
    # before the answerer is invoked.
    _ = paper_ids  # consumed by the chunk-tier baselines, not here

    # The atom-tier answerer is a multi-tool agent: query_atoms, traverse,
    # semantic_search, get_atom_full, check_contradiction. On complex questions
    # it routinely chains 30-80 tool calls (plan → retrieve → refine → cite),
    # easily exceeding PydanticAI's default request_limit=50. Bump to 250 to
    # match the extractor's allowance.
    from pydantic_ai.usage import UsageLimits
    t0 = time.monotonic()
    result = agent.run_sync(
        user_block, deps=deps,
        usage_limits=UsageLimits(request_limit=250),
    )
    latency_ms = int((time.monotonic() - t0) * 1000)

    out: SynthesisResult = result.output
    out.latency_ms = latency_ms

    # PydanticAI 1.x exposes token usage as a property.
    try:
        usage = result.usage
        out.tokens_in = (usage.input_tokens or usage.request_tokens or 0) if usage else 0
        out.tokens_out = (usage.output_tokens or usage.response_tokens or 0) if usage else 0
    except Exception:
        pass

    # Pull tool-call IDs we logged during this run
    out.tool_call_ids = [t.id for t in db.list_tool_calls(session_id)]

    return out
