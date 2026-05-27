# Tool-Calling Agents — Extraction and Synthesis

## Why tool-calling, not context-stuffing

The default RAG pattern is: retrieve top-K → stuff context → ask. The LLM gets a static blob and answers.

The agent pattern is: **the LLM gets a question + a tool list + a registry summary**, then picks its own retrieval strategy by calling typed tools. Every tool call returns verified, typed data from the demo's stores. The LLM's choices are bounded by the registry's allowed shapes.

Two payoffs:

1. **The "deterministic tool calls" claim in the thesis is literal.** Tools return data, not generated text. The audit trail is structured.
2. **The eval substrate.** Every tool call is logged to SQLite. The eval loop reads these traces to refine prompts, planner heuristics, and registry constraints.

PydanticAI is the framework: type-safe agents, structured outputs, native tool registration.

## Extraction agent

Called by `POST /extract/draft`. Receives one source paper's chunks, emits draft atoms.

```python
from pydantic_ai import Agent, RunContext
from api.models.atom import DraftAtom

class ExtractionDeps:
    source_id: str
    registry: Schema
    semantic: SemanticService
    db: DBService

extraction_agent = Agent(
    model="...",                              # cost-effective default
    result_type=list[DraftAtom],
    deps_type=ExtractionDeps,
    system_prompt=PROMPT_VERSION_LATEST,
)

@extraction_agent.tool
def check_registry(ctx: RunContext[ExtractionDeps], key: str) -> AttributeDef | None:
    """Is this attribute key already registered? Returns def with value_type, applicable_types."""
    return ctx.deps.registry.get_attribute(key)

@extraction_agent.tool
def list_attribute_keys(
    ctx: RunContext[ExtractionDeps], applicable_to_type: AtomKind
) -> list[AttributeDef]:
    """Suggested registered attribute keys for this atom type."""
    return ctx.deps.registry.attributes_for_type(applicable_to_type)

@extraction_agent.tool
def find_similar_atoms(
    ctx: RunContext[ExtractionDeps], content: str, limit: int = 5
) -> list[AtomicNote]:
    """Semantic search to avoid drafting a near-duplicate of an existing atom."""
    return ctx.deps.semantic.search_atoms(content, limit=limit)

@extraction_agent.tool
def get_chunk_context(
    ctx: RunContext[ExtractionDeps], chunk_id: str, window: int = 1
) -> list[Chunk]:
    """Neighboring chunks for context when the focal chunk is ambiguous."""
    return ctx.deps.db.chunks_around(chunk_id, window=window)
```

The agent's prompt steers it to:
1. Read the focal chunk(s).
2. Call `list_attribute_keys` for the candidate atom type.
3. For any new attribute it wants to use, call `check_registry` to see if it should reuse an existing key.
4. Call `find_similar_atoms` on the draft body to avoid duplication.
5. Emit a `DraftAtom` (typed; Pydantic validates).

The agent returns `list[DraftAtom]`. Each draft carries `origin.prompt_version` and a `draft_id`. Drafts persist in SQLite `drafts` table until `/curate` accepts/edits/rejects them.

## Synthesis agent

Called by `POST /query` (Q&A) and `POST /synthesize` (longer-form draft). Receives a question (or topic) and produces a cited answer.

```python
class SynthesisDeps:
    retrieval: RetrievalService
    semantic: SemanticService
    registry: Schema
    vault: VaultIO

class SynthesisResult(BaseModel):
    answer: str                              # markdown with [[atom-id]] citations
    cited_atoms: list[str]                   # atom ids referenced
    tool_calls: list[ToolCall]               # full trace for the eval log

synthesis_agent = Agent(
    model="...",
    result_type=SynthesisResult,
    deps_type=SynthesisDeps,
    system_prompt=SYNTHESIS_PROMPT_VERSION_LATEST,
)

@synthesis_agent.tool
def query_atoms(
    ctx: RunContext[SynthesisDeps], *, type: AtomKind | None = None, where: dict | None = None
) -> list[AtomicNote]:
    """SQL-style attribute query. Use for typed filters (domain, evidence, etc)."""
    return ctx.deps.retrieval.query(type=type, where=where).atoms

@synthesis_agent.tool
def traverse(
    ctx: RunContext[SynthesisDeps], atom_id: str, via: list[str], hops: int = 1
) -> list[AtomicNote]:
    """Graph traversal. Use to follow relations from a known atom."""
    return ctx.deps.retrieval.query(related_to=atom_id, via=via, hops=hops).atoms

@synthesis_agent.tool
def semantic_search(
    ctx: RunContext[SynthesisDeps], query: str, limit: int = 10
) -> list[AtomicNote]:
    """Cosine search over atom embeddings. Use for fuzzy 'similar in meaning' lookups."""
    return ctx.deps.semantic.search_atoms(query, limit=limit)

@synthesis_agent.tool
def get_atom_full(ctx: RunContext[SynthesisDeps], atom_id: str) -> AtomicNote:
    """Fetch the full atom body. Use when a summary surfaced by another tool is insufficient."""
    return ctx.deps.vault.read_atom(atom_id)

@synthesis_agent.tool
def check_contradiction(
    ctx: RunContext[SynthesisDeps], claim_a: str, claim_b: str
) -> bool:
    """Does atom A have a 'contradicts' relation to atom B (or vice versa)?"""
    return ctx.deps.retrieval.has_relation(claim_a, claim_b, "contradicts")
```

The synthesis prompt:

> You are answering a research question over a curated vault of atomic notes. You have tools to query atoms by attribute, traverse the relation graph, search semantically, and fetch full atom bodies. Plan your retrieval, call tools as needed, then synthesize an answer that cites every claim with `[[atom-id]]`. Do not include any claim not grounded in a retrieved atom.

## Tool-call logging

Every tool call is logged to SQLite `tool_calls` with the full trace:

```json
{
  "id": "tc-2026-05-24-1742-0001",
  "session_id": "synth-2026-05-24-1742",
  "agent": "synthesis",
  "prompt_version": "synthesis.v1",
  "calls": [
    {"tool": "query_atoms", "args": {"type": "claim", "where": {"domain.sub": "nlp"}}, "n_results": 23, "latency_ms": 4},
    {"tool": "traverse", "args": {"atom_id": "...", "via": ["contradicts"]}, "n_results": 5, "latency_ms": 2},
    {"tool": "get_atom_full", "args": {"atom_id": "..."}, "n_results": 1, "latency_ms": 1}
  ],
  "tokens_in": 1247,
  "tokens_out": 318,
  "result_summary": "5 atoms cited, 3 cross-paper"
}
```

This is the **eval substrate**:

- The retrieval-refinement loop reads tool traces to find queries that should have surfaced different atoms.
- The constraint-tightening loop reads `check_registry` calls that returned `None` and proposes promotions.
- The prompt-regeneration loop reads which tools were called in which order and tunes the system prompt to favor effective patterns.

## Why this beats context-stuffing for the thesis

| Property | Context-stuffed RAG | Tool-calling agent |
|----------|---------------------|---------------------|
| Token cost | static top-K bill per query | adaptive — minimal tools for simple questions, more for complex |
| Audit trail | "we sent these K chunks" | full ordered tool trace with results |
| Eval substrate | thumbs up/down on final answer | structured signal at each step |
| Composability | flat retrieval | the LLM picks compositions (filter → traverse → re-rank) |
| Determinism | LLM can fabricate any chunk | tools return verified data; deviations are detectable |

The cost is more LLM roundtrips. For a small vault, this matters less than for a 10K-atom store. The trade we are making in this demo is correctness + audit + composability over per-call latency.
