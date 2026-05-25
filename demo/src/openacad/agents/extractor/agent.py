"""PydanticAI extraction agent with four registry-aware openacad.

The agent receives the text of one or more chunks plus the registry summary;
it picks attribute keys to reuse, checks for duplicates, optionally inspects
neighboring chunks, and emits ProposedAtom objects. The pipeline wraps them
into DraftAtom and persists.
"""

from dataclasses import dataclass

from pydantic_ai import Agent, RunContext

from openacad.runtime.settings import settings
from openacad.notes.schema import AtomicNote, AtomKind, ProposedAtom
from openacad.notes.registry.schema import AttributeDef
from openacad.runtime.corpus.source import Chunk
from openacad.notes.query import semantic as semantic_service
from openacad.runtime import db
from openacad.notes.persistence import vault as vault_io
from openacad.runtime.llm import model_string, settings_for
from openacad.notes.registry.validation import get_schema


@dataclass
class ExtractionDeps:
    source_id: str


def _load_system_prompt() -> str:
    path = settings.prompts_dir / "extraction" / "v1.md"
    return path.read_text(encoding="utf-8")


def _build_agent_with_prompt(body: str) -> Agent:
    """Build an Extractor agent with the given system-prompt body. Used by
    openacad.runtime.agent_base.build_extractor() for scenario-aware construction."""
    agent = Agent(
        model_string("extraction"),
        deps_type=ExtractionDeps,
        output_type=list[ProposedAtom],
        system_prompt=body,
        retries=2,
        model_settings=settings_for("extraction"),
    )

    @agent.tool
    def list_attribute_keys(
        ctx: RunContext[ExtractionDeps], applicable_to_type: AtomKind
    ) -> list[AttributeDef]:
        """Registered attribute keys applicable to this atom type. Reuse where possible."""
        return get_schema().attributes_for_type(applicable_to_type)

    @agent.tool
    def check_registry(ctx: RunContext[ExtractionDeps], key: str) -> AttributeDef | None:
        """Definition + value_type of an existing attribute key, or null if unknown."""
        return get_schema().get_attribute(key)

    @agent.tool
    def find_similar_atoms(
        ctx: RunContext[ExtractionDeps], content: str, limit: int = 5
    ) -> list[dict]:
        """Semantic search to avoid drafting a near-duplicate.

        Returns a list of {id, type, content, score} for the top-K matches.
        If any match has score >= 0.85, consider linking via a relation instead of drafting.
        """
        hits = semantic_service.atoms_store().search(content, limit=limit)
        out: list[dict] = []
        for atom_id, score in hits:
            try:
                a = vault_io.read_atom(atom_id)
                out.append(
                    {
                        "id": atom_id,
                        "type": a.metas.type,
                        "content": a.content,
                        "score": score,
                    }
                )
            except Exception:
                continue
        return out

    @agent.tool
    def get_chunk_context(
        ctx: RunContext[ExtractionDeps], chunk_id: str, window: int = 1
    ) -> list[Chunk]:
        """Neighboring chunks for context when the focal chunk is ambiguous."""
        focal = db.get_chunk(chunk_id)
        if not focal:
            return []
        all_chunks = db.chunks_for_source(ctx.deps.source_id)
        focal_idx = next((i for i, c in enumerate(all_chunks) if c.id == chunk_id), -1)
        if focal_idx < 0:
            return [focal]
        lo = max(0, focal_idx - window)
        hi = min(len(all_chunks), focal_idx + window + 1)
        return all_chunks[lo:hi]

    return agent


def _build_agent() -> Agent:
    """Legacy: build with the on-disk v1 prompt (no scenario awareness)."""
    return _build_agent_with_prompt(_load_system_prompt())


def get_agent() -> Agent:
    """Return the scenario-active Extractor agent. Routes through agent_factory
    so prompt-version promotion is hot-reloaded."""
    from openacad.runtime.agent_base import build_extractor
    return build_extractor()


# ── runtime context block (injected into the user prompt) ───────────────


def build_context_block(source_id: str, chunks: list[Chunk]) -> str:
    """Compose the user message: registry summary + chunk text.

    Tools let the agent pull more registry detail or chunk context on demand,
    but injecting a summary up front reduces tool roundtrips.
    """
    schema = get_schema()
    lines: list[str] = []

    lines.append("## Registry overview")
    types_line = ", ".join(sorted(schema.types.keys())) or "(none yet)"
    lines.append(f"atom types: {types_line}")

    attr_summary = sorted(
        [(d.key, d.value_type, d.usage_count) for d in schema.attributes.values()],
        key=lambda t: -t[2],
    )[:20]
    if attr_summary:
        lines.append("top attributes (key:value_type [usage]):")
        for k, vt, uc in attr_summary:
            lines.append(f"  - {k}:{vt} [{uc}]")

    rel_summary = sorted(
        [(d.key, d.inverse or "—", d.usage_count) for d in schema.relations.values()],
        key=lambda t: -t[2],
    )[:20]
    if rel_summary:
        lines.append("top relations (key ↔ inverse [usage]):")
        for k, inv, uc in rel_summary:
            lines.append(f"  - {k} ↔ {inv} [{uc}]")

    lines.append("")
    lines.append(f"## Source: {source_id}")
    lines.append(f"## Chunks ({len(chunks)} total)")
    for c in chunks:
        lines.append(f"\n### {c.id} (pages {c.page_range[0]}-{c.page_range[1]})")
        lines.append(c.text)

    return "\n".join(lines)
