"""Scenario instances — the rungs of the scholarly-research agent openacad.runtime.

Each `Scenario` declares which agents are active, which capability flags are on,
and what rubric criteria apply per agent role. The types themselves live in
`harness/scenario.py`; this module is just the registry of instances.

The 9 rungs progress one capability at a time:
  1. cold-read            — RAG on full document (no chunking)
  2. keyword-snippets     — random chunks + FTS5 keyword search
  3. semantic-snippets    — random chunks + MiniLM embeddings (logical chunking)
  4. atoms-only           — atomic extraction (no attrs, no rels, no atom-embeddings)
  5. atoms-attrs          — + attributes  (relational-DB friendly)
  6. atoms-attrs-rels     — + relations   (graphical Notes web)
  7. drafted-notes        — + atom embeddings (full atom-tier capabilities, auto-accept)
  8. curated-notes        — + HITL accept/edit/reject
  9. evolving-notes       — + Meta-Evaluator hardens agent instructions over time
                            (display name: "Self-Improving Assistant")
"""

from __future__ import annotations

from openacad.runtime.scenario import AgentRole, Scenario, Tier


SCENARIOS: list[Scenario] = [
    # ── Tier: cold (no chunking) ────────────────────────────────────────
    Scenario(
        key="cold-read",
        name="Cold Read",
        tier=Tier.COLD,
        description="LLM gets the whole PDF in context and answers from scratch.",
        agents=[AgentRole.ANSWERER],
        has_extraction=False,
        has_curation=False,
        has_meta_eval=False,
        # No atoms exist at this tier — atom-level capabilities are n/a.
        has_attributes=False,
        has_relations=False,
        has_atom_embeddings=False,
        rubric_criteria={
            AgentRole.ANSWERER: ["accuracy", "citation_quality", "conciseness"],
        },
    ),
    # ── Tier: chunk (random chunking + retrieval) ───────────────────────
    Scenario(
        key="keyword-snippets",
        name="Keyword Snippets",
        tier=Tier.CHUNK,
        description="Top-K chunks by SQLite FTS5 (BM25); the answerer synthesizes from them.",
        agents=[AgentRole.ANSWERER],
        has_extraction=False,
        has_curation=False,
        has_meta_eval=False,
        has_attributes=False,
        has_relations=False,
        has_atom_embeddings=False,
        rubric_criteria={
            AgentRole.ANSWERER: ["accuracy", "citation_quality", "retrieval_fit"],
        },
    ),
    Scenario(
        key="semantic-snippets",
        name="Semantic Snippets",
        tier=Tier.CHUNK,
        description="Top-K chunks by cosine similarity (MiniLM); the answerer synthesizes from them.",
        agents=[AgentRole.ANSWERER],
        has_extraction=False,
        has_curation=False,
        has_meta_eval=False,
        has_attributes=False,
        has_relations=False,
        has_atom_embeddings=False,
        rubric_criteria={
            AgentRole.ANSWERER: ["accuracy", "citation_quality", "retrieval_fit"],
        },
    ),
    # ── Tier: atoms (progressive capability ladder) ─────────────────────
    Scenario(
        key="atoms-only",
        name="Atomic Chunks",
        tier=Tier.ATOMS,
        description=(
            "Agent extracts atomic notes from chunks — one self-contained idea per "
            "atom. No typed attributes, no relations, no semantic embeddings on atoms. "
            "Just atoms-as-units."
        ),
        agents=[AgentRole.EXTRACTOR, AgentRole.ANSWERER],
        has_extraction=True,
        has_curation=False,
        has_meta_eval=False,
        has_attributes=False,
        has_relations=False,
        has_atom_embeddings=False,
        rubric_criteria={
            AgentRole.EXTRACTOR: ["atomicity"],
            AgentRole.ANSWERER: ["accuracy", "citation_quality", "conciseness"],
        },
    ),
    Scenario(
        key="atoms-attrs",
        name="+ Attributes",
        tier=Tier.ATOMS,
        description=(
            "Atomic notes with typed attributes (relational-DB friendly). Now you "
            "can filter atoms by typed fields like `study.year`, `population.region`, "
            "`finding.effect_size`. The attribute registry promotes recurring keys."
        ),
        agents=[AgentRole.EXTRACTOR, AgentRole.ANSWERER],
        has_extraction=True,
        has_curation=False,
        has_meta_eval=False,
        has_attributes=True,
        has_relations=False,
        has_atom_embeddings=False,
        rubric_criteria={
            AgentRole.EXTRACTOR: ["atomicity", "attribute_fit"],
            AgentRole.ANSWERER: ["accuracy", "citation_quality", "conciseness"],
        },
    ),
    Scenario(
        key="atoms-attrs-rels",
        name="+ Relations",
        tier=Tier.ATOMS,
        description=(
            "Atoms + attributes + typed relations between atoms (the notes graph). "
            "Now the answerer can traverse `supports`, `contradicts`, `extends`, "
            "and graph queries become possible alongside attribute filtering."
        ),
        agents=[AgentRole.EXTRACTOR, AgentRole.ANSWERER],
        has_extraction=True,
        has_curation=False,
        has_meta_eval=False,
        has_attributes=True,
        has_relations=True,
        has_atom_embeddings=False,
        rubric_criteria={
            AgentRole.EXTRACTOR: ["atomicity", "attribute_fit", "relation_fit"],
            AgentRole.ANSWERER: ["accuracy", "citation_quality", "conciseness"],
        },
    ),
    Scenario(
        key="drafted-notes",
        name="+ Atom Embeddings",
        tier=Tier.ATOMS,
        description=(
            "Atoms + attributes + relations + MiniLM embeddings on each atom. "
            "Now `find_similar_atoms` works — semantic neighborhood search joins "
            "typed retrieval. Still auto-accepts every valid draft (no HITL)."
        ),
        agents=[AgentRole.EXTRACTOR, AgentRole.ANSWERER],
        has_extraction=True,
        has_curation=False,
        has_meta_eval=False,
        has_attributes=True,
        has_relations=True,
        has_atom_embeddings=True,
        rubric_criteria={
            AgentRole.EXTRACTOR: ["atomicity", "attribute_fit", "relation_fit"],
            AgentRole.ANSWERER: ["accuracy", "citation_quality", "conciseness"],
        },
    ),
    Scenario(
        key="curated-notes",
        name="+ HITL Curation",
        tier=Tier.ATOMS,
        description=(
            "Full atom capabilities + scholar HITL: every draft passes through "
            "accept / edit / reject. Your standards encoded as the vault grows."
        ),
        agents=[AgentRole.EXTRACTOR, AgentRole.SCORER, AgentRole.ANSWERER],
        has_extraction=True,
        has_curation=True,
        has_meta_eval=False,
        has_attributes=True,
        has_relations=True,
        has_atom_embeddings=True,
        rubric_criteria={
            AgentRole.EXTRACTOR: ["atomicity", "attribute_fit", "relation_fit"],
            AgentRole.SCORER: ["recall", "precision"],
            AgentRole.ANSWERER: ["accuracy", "citation_quality", "conciseness"],
        },
    ),
    Scenario(
        key="evolving-notes",
        name="Self-Improving Assistant",
        tier=Tier.ATOMS,
        description=(
            "Curated Notes + a Meta-Evaluator that synthesises rubric ratings into "
            "hardened system prompts for each agent. The notes themselves are "
            "immutable; what evolves is the agents' instructions, so future notes "
            "and future answers get sharper as you submit more feedback."
        ),
        agents=[
            AgentRole.EXTRACTOR,
            AgentRole.SCORER,
            AgentRole.ANSWERER,
            AgentRole.META_EVAL,
        ],
        has_extraction=True,
        has_curation=True,
        has_meta_eval=True,
        has_attributes=True,
        has_relations=True,
        has_atom_embeddings=True,
        rubric_criteria={
            AgentRole.EXTRACTOR: ["atomicity", "attribute_fit", "relation_fit"],
            AgentRole.SCORER: ["recall", "precision"],
            AgentRole.ANSWERER: ["accuracy", "citation_quality", "conciseness"],
            AgentRole.META_EVAL: ["proposal_quality"],
        },
    ),
]


SCENARIOS_BY_KEY: dict[str, Scenario] = {s.key: s for s in SCENARIOS}
