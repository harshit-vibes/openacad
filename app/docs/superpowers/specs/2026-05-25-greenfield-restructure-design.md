# Greenfield Restructure — Design Spec

**Date:** 2026-05-25
**Status:** Approved, awaiting writing-plans plan
**Supersedes:** the structural shape arrived at in
[`2026-05-24-scholarly-streamlit-redesign-design.md`](2026-05-24-scholarly-streamlit-redesign-design.md)
and the agent-first restructure executed earlier this week.

## Context

The current `openacad/demo` has been through two organic restructures:

1. **Scholarly Streamlit redesign** — gave the 6-scenario walkthrough its
   narrative shape (since extended to 9 scenarios in the progressive ladder).
2. **Agent-first restructure** — moved code out of `api/services/` into
   `agents/ tools/ hooks/ harness/ scenarios/ domain/ apps/`.

Both helped, neither was greenfield. The resulting layout has accumulated three
structural debts that this spec addresses:

1. **The atomic note isn't first-class.** Its anatomy (the 5-facet schema),
   lifecycle, storage, registry-governance, and retrieval are spread across
   `tools/atoms_*`, `tools/registry*`, `tools/retrieval*`, `domain/models/`,
   `domain/embeddings.py`. There's no single place a reader can answer "what
   is a note in openacad?"

2. **HITL + evals aren't framed as one loop.** Rubric capture, scholar
   verdicts, automated scoring, and prompt refinement are scattered across
   `tools/eval/`, `tools/rubric.py`, `hooks/on_rubric_submitted.py`,
   `agents/meta_evaluator/`. The continuous-feedback loop that defines the
   product isn't visible in the directory tree.

3. **The note's lifecycle is half-modeled.** We've built BIRTH (extraction +
   curation + revision) but not CONSUMPTION (using notes to compose or
   assess artifacts). The paper_writer/book_writer slots hint at this gap;
   nothing structural supports it.

This spec proposes a fully greenfield layout where each major concept has its
own top-level package, the consumption side is fleshed out, and naming reads
as a mature library rather than a research prototype.

## Locked decisions

| Decision | Locked value |
|---|---|
| Top-level layout | `src/openacad/` (one package, src layout, vendorable) |
| Six domain packages | `runtime/`, `notes/`, `artifacts/`, `feedback/`, `agents/`, `hooks/` |
| Two configuration packages | `scenarios/`, `apps/` |
| Acquisition vocabulary | `notes/intake/` + `artifacts/ingestion/` (distinct, not symmetric) |
| Typed entity structure | `schema/` (everywhere — not `anatomy/` or `model/`) |
| Spelling | `artifacts/` (American) |
| Tools package | Dissolved — tools live alongside their data; `runtime/tool_registry.py` indexes via `@tool` decorator |
| Domain package | Dissolved — DB engine → `runtime/db.py`; models distribute to their domains |
| Scenarios as data | `scenarios/catalog.yaml` instead of Python instance list |
| Test layout | `tests/{unit,integration,e2e}/` mirroring source structure |
| Existing scenario keys + vault data | Untouched — `data/vaults/<key>/` keeps the 9 keys |

## Target structure

```
openacad/
├── src/openacad/
│   ├── runtime/                          ← agent runtime substrate
│   │   ├── corpus/                       (Source, Chunk, PDF, chunking, embeddings, store)
│   │   ├── answerers/                    (cold, lexical, semantic, tool_calling)
│   │   ├── scenario.py                   (Scenario, Tier, AgentRole, Step, ContextVar)
│   │   ├── settings.py                   (pydantic-settings + .env)
│   │   ├── llm.py                        (model_for, settings_for, provider routing)
│   │   ├── agent_base.py                 (build_* + version cache + auto-log to timeline)
│   │   ├── dispatcher.py                 (the public ask())
│   │   ├── tool_registry.py              (@tool decorator + agent allow-lists)
│   │   └── db.py                         (shared.sqlite engine)
│   │
│   ├── notes/                            ← THE note as a domain
│   │   ├── schema/
│   │   │   ├── note.py                   (top-level AtomicNote — renamed)
│   │   │   ├── metas.py                  (id, type, status, timestamps, tags)
│   │   │   ├── provenance.py             (Origin: source_id, chunk_ids, page_range, scholar_action)
│   │   │   ├── attributes.py             (typed key-value store)
│   │   │   ├── relations.py              (Relation + inverse logic)
│   │   │   ├── content.py                (markdown body, splitting rules)
│   │   │   └── kinds.py                  (AtomKind: claim, method, finding, …)
│   │   ├── intake/                       (how a note enters the vault)
│   │   │   ├── from_chunks.py            (Extractor agent over PDF chunks — what we have)
│   │   │   ├── from_url.py               (future: arxiv, web pages)
│   │   │   ├── authored.py               (NEW: scholar writes from scratch)
│   │   │   ├── from_passage.py           (NEW: paste text, agent suggests notes)
│   │   │   └── from_artifact.py          (NEW: derived during artifact assessment)
│   │   ├── curation/                     (HITL gate before "active")
│   │   │   ├── score.py
│   │   │   ├── accept.py
│   │   │   ├── edit.py
│   │   │   └── reject.py
│   │   ├── revision/                     (post-active changes)
│   │   │   ├── edit.py
│   │   │   ├── deprecate.py
│   │   │   ├── merge.py
│   │   │   └── split.py
│   │   ├── persistence/
│   │   │   ├── vault.py                  (markdown files on disk)
│   │   │   ├── projection.py             (SQLite atoms_index for fast queries)
│   │   │   ├── embeddings.py             (MiniLM .npz for semantic search)
│   │   │   └── graph_index.py            (NetworkX rebuilt from relations)
│   │   ├── registry/                     (typed vocabulary that grows from accepted notes)
│   │   │   ├── attributes.py
│   │   │   ├── relations.py
│   │   │   ├── kinds.py
│   │   │   ├── validation.py
│   │   │   └── evolution.py              (recount_usage_and_promote)
│   │   └── query/                        (the 4 query modes the answerer composes)
│   │       ├── semantic.py
│   │       ├── lexical.py
│   │       ├── attribute.py
│   │       ├── graph.py
│   │       └── hybrid.py
│   │
│   ├── artifacts/                        ← OUTPUT-side: what notes are USED FOR
│   │   ├── schema/
│   │   │   ├── artifact.py               (base entity)
│   │   │   ├── paper.py                  (sections: abstract, intro, related-work, …)
│   │   │   ├── chapter.py                (book chapter w/ cross-chapter coherence)
│   │   │   ├── review.py                 (literature review structure)
│   │   │   ├── briefing.py               (short structured doc)
│   │   │   ├── slides.py                 (presentation outline)
│   │   │   └── assessment.py             (the OUTPUT of assessment/)
│   │   ├── composition/                  (notes → artifact)
│   │   │   ├── orchestrator.py           (planner → drafters → assembler)
│   │   │   ├── paper.py
│   │   │   ├── chapter.py
│   │   │   ├── review.py
│   │   │   └── briefing.py
│   │   ├── assessment/                   ((external artifact + notes) → critique)
│   │   │   ├── consistency.py
│   │   │   ├── coverage.py
│   │   │   ├── support.py
│   │   │   ├── critique.py
│   │   │   └── gap_analysis.py
│   │   ├── ingestion/                    (external artifact → chunks/embeddings)
│   │   │   ├── from_pdf.py
│   │   │   ├── from_url.py
│   │   │   └── from_text.py
│   │   └── persistence/
│   │       └── vault.py                  (artifact markdown + note citations)
│   │
│   ├── feedback/                         ← HITL + evals as ONE loop
│   │   ├── timeline.py                   (substrate event log — append-only SQLite table in
│   │   │                                  shared.sqlite; readers paginate by scenario + role + ts)
│   │   ├── rubric/                       (scholar ratings: capture, aggregate, schema)
│   │   ├── verdicts/                     (accept/edit/reject events on notes + artifacts)
│   │   ├── scoring/                      (pydantic-evals harness, scorers, gold datasets, reports)
│   │   └── refinement/                   (meta-evaluator proposer, prompt versions, promotion)
│   │
│   ├── agents/                           ← roles
│   │   ├── extractor/                    (existing)
│   │   ├── synthesizer/                  (existing — generic Q&A)
│   │   ├── scorer/                       (existing)
│   │   ├── meta_evaluator/               (existing)
│   │   ├── paper_writer/                 (existing stub → wires into composition/paper)
│   │   ├── book_writer/                  (existing stub → wires into composition/chapter)
│   │   ├── critic/                       (NEW stub → assessment/critique)
│   │   ├── consistency_checker/          (NEW stub → assessment/consistency)
│   │   ├── coverage_analyzer/            (NEW stub → assessment/coverage)
│   │   └── gap_analyzer/                 (NEW stub → assessment/gap_analysis)
│   │
│   ├── hooks/                            ← lifecycle events; all wire into feedback.timeline
│   │   ├── on_agent_action.py            (NEW: every agent call — fires for HITL UI subscription)
│   │   ├── on_note_acquired.py           (any intake path)
│   │   ├── on_note_curated.py            (was on_atom_accepted; broader)
│   │   ├── on_note_revised.py            (post-active changes)
│   │   ├── on_artifact_composed.py       (NEW)
│   │   ├── on_artifact_assessed.py       (NEW)
│   │   ├── on_rubric_submitted.py
│   │   └── on_prompt_promoted.py
│   │
│   ├── scenarios/
│   │   ├── catalog.yaml                  (the scenarios as data — 9 retrieval-ladder + N utility)
│   │   ├── loader.py                     (parse YAML → Scenario instances)
│   │   └── prompts/
│   │       ├── _defaults/                (per-role default prompts)
│   │       └── _overrides/               (per-scenario per-role overrides)
│   │
│   └── __init__.py                       ← public API
│
├── apps/                                 ← consumers, each independently runnable
│   ├── streamlit/
│   ├── cli/
│   ├── api/                              (FastAPI exposing runtime + feedback + notes + artifacts)
│   ├── web/                              (Next.js — future)
│   └── mcp_server/                       (exposes tool_registry over MCP — future)
│
├── data/                                 (runtime, gitignored)
│   ├── sources/
│   ├── shared.sqlite
│   ├── embeddings/
│   └── vaults/<scenario-key>/
│
├── tests/
│   ├── unit/                             (mirrors src/openacad/ — per-module unit tests)
│   ├── integration/                      (real SQLite, no LLM)
│   ├── e2e/                              (full Streamlit + LLM smoke)
│   └── conftest.py
│
├── scripts/
│   ├── seed/                             (seed_scenarios, seed_papers, seed_atoms, fixtures/)
│   ├── migrate/                          (legacy_vault_to_scenarios, restructure migration)
│   └── ops/                              (run_baselines, eval_report, prepare_atom_decomposition)
│
├── docs/
│   ├── concepts/                         (note-anatomy, thesis, registry-schema-layer)
│   ├── architecture/                     (runtime-notes-artifacts-feedback, scenarios-as-data)
│   ├── recipes/                          (add-an-agent.md, write-a-scenario.md, add-a-tool.md)
│   └── superpowers/                      (specs, plans, history)
│
├── pyproject.toml                        (one package: openacad; apps are entry-points)
├── Makefile
├── README.md
└── .env / .env.example
```

## The mental model

> openacad is a **runtime** that runs **agents** which **intake / curate / revise** **notes**,
> **compose / assess** **artifacts** with them, and continuously **refine** through **feedback** —
> orchestrated by **scenarios**, consumed by **apps**.

Eight nouns. Each maps to a top-level package.

## How HITL becomes first-class on every agent action

This is the architectural commitment that gives the system its character.

**1. The runtime auto-instruments every agent call.**

```python
# runtime/agent_base.py
def call_agent(role: AgentRole, *args, **kwargs) -> AgentResult:
    agent = build_*(role)
    result = agent.run_sync(*args, **kwargs)

    # Every call lands in the timeline. No agent runs silently.
    from openacad.feedback import timeline
    event_id = timeline.log_agent_action(
        role=role,
        scenario=active_scenario().key,
        prompt_version=agent.prompt_version,
        result=result,
        tokens=result.usage,
        latency_ms=result.latency_ms,
    )

    # The result carries flags the UI uses to render a rubric input.
    result.event_id = event_id
    result.awaiting_judgment = active_scenario().has_curation
    return result
```

**2. Every UI consumer surfaces a rubric prompt when `awaiting_judgment=True`.**

Streamlit, Next.js, CLI — they all read the same flag from the same result
object. No app re-implements "should I show a rubric?".

**3. The timeline is the substrate.**

`feedback/timeline.py` is the single append-only log of every agent action +
every verdict + every score. The meta_evaluator reads it. Reports read it.
Replay-and-rebuild reads it. One source of truth.

**4. Capability flags in scenarios decide WHICH actions need HITL.**

```yaml
# scenarios/catalog.yaml — example
- key: curated-notes
  has_curation: true
  hitl:
    on_extract: true
    on_answer: true
    on_propose_prompt: true

- key: drafted-notes
  has_curation: false
  hitl:
    on_answer: true  # rubric still captured on answers for eval
```

## How the note lifecycle becomes complete

The note's life now has four crisply-named stages, plus a consumption side
that lives in `artifacts/`:

| Stage | Package | What it owns |
|---|---|---|
| **Intake** | `notes/intake/` | how a note enters: from_chunks, from_url, authored, from_passage, from_artifact |
| **Curation** | `notes/curation/` | HITL gate — score, accept, edit, reject |
| **Revision** | `notes/revision/` | post-active changes — edit, deprecate, merge, split |
| **Query** | `notes/query/` | how agents and apps READ notes (semantic/lexical/attribute/graph/hybrid) |

And on the artifact side:

| Stage | Package | What it owns |
|---|---|---|
| **Ingestion** | `artifacts/ingestion/` | external artifact → chunks/embeddings for assessment |
| **Composition** | `artifacts/composition/` | notes → new artifact (planner + drafters + assembler) |
| **Assessment** | `artifacts/assessment/` | (artifact + notes) → consistency/coverage/support/critique/gap |

The **consumption → intake loop** is named: `notes/intake/from_artifact.py`
takes a `CritiqueResult` from `artifacts/assessment/critique.py` (which
suggests "you should record a note about X") and runs them through the
standard intake → curation → HITL flow.

## Scenarios catalog grows two-dimensionally

The current 9-rung ladder is the **retrieval family**. The new lifecycle
shapes are a **utility family** — distinct surfaces, not rungs of the same
ladder.

```yaml
# scenarios/catalog.yaml

retrieval_ladder:
  - cold-read · keyword-snippets · semantic-snippets
  - atoms-only · atoms-attrs · atoms-attrs-rels
  - drafted-notes · curated-notes · evolving-notes

utility:
  - ad-hoc-note-capture       (manual authoring, no extraction agent)
  - paper-from-vault          (composition: research paper)
  - chapter-from-vault        (composition: book chapter)
  - briefing-from-vault       (composition: short doc)
  - peer-review-against-vault (assessment: critique + consistency + coverage + gap)
  - consistency-check         (assessment: contradictions only)
```

UI surfaces a family selector at the top of the scenario picker.

## New agents this enables (stubs only — not implemented in this restructure)

The restructure adds **five new agent stubs**, each a folder with
`prompt.md` + `tools.toml` + `README.md` (no `agent.py`). They serve as
architectural commitments — they document where the consumption side
plugs in. Implementation comes in a separate work item.

| Agent | Status | Wires to | Reads notes via | Writes artifacts via |
|---|---|---|---|---|
| `paper_writer` | existing stub, kept | composition/paper | query.hybrid | persistence.vault |
| `book_writer` | existing stub, kept | composition/chapter | query.hybrid | persistence.vault |
| `briefing_writer` | NEW stub | composition/briefing | query.attribute + query.semantic | persistence.vault |
| `critic` | NEW stub | assessment/critique | query.semantic | (writes Assessment schema) |
| `consistency_checker` | NEW stub | assessment/consistency | query.graph | (writes Assessment) |
| `coverage_analyzer` | NEW stub | assessment/coverage | query.attribute | (writes Assessment) |
| `gap_analyzer` | NEW stub | assessment/gap_analysis | query.attribute + query.semantic | (writes Assessment) |

Existing stubs `paper_writer/` and `book_writer/` are NOT populated as part of
this restructure — they're just relocated into the new tree shape.

## Public API surface

`src/openacad/__init__.py` exports exactly what a downstream consumer needs:

```python
# Scenario context
from openacad import SCENARIOS, use_scenario, active_scenario

# Note ops
from openacad import list_notes, get_note, find_notes
from openacad import accept_draft, edit_draft, reject_draft, author_note

# Artifact ops
from openacad import compose_artifact, assess_artifact

# Question answering
from openacad import ask

# Feedback
from openacad import capture_rubric, propose_prompt, promote_prompt
```

The internal layout is free to evolve without breaking these imports.

## Migration approach (high-level)

Mechanical, scripted in one pass:

1. **Skeleton phase** — create new dirs + placeholder `__init__.py`
2. **Per-package phase** — `mv` files into their new homes, in dependency order:
   1. `runtime/` (scenario, settings, llm, agent_base, dispatcher, corpus, db)
   2. `notes/schema/` (was domain/models/atom.py, registry models)
   3. `notes/persistence/` (was tools/atoms_vault.py + domain/embeddings.py)
   4. `notes/registry/` (was tools/registry*.py)
   5. `notes/query/` (was tools/retrieval*.py)
   6. `notes/intake/` (was tools/atoms_extract.py + domain/ingest_service.py)
   7. `notes/curation/` (was tools/atoms_curate.py)
   8. `notes/revision/` (NEW — empty stubs)
   9. `artifacts/` (NEW — empty schema + stubs)
   10. `feedback/` (was tools/rubric.py + scoring.py + agents/meta_evaluator/agent.py portions)
   11. `agents/` (re-export from runtime.agent_base; add new stubs)
   12. `hooks/` (existing + new lifecycle hooks)
   13. `scenarios/` (Python definitions → YAML; loader.py parses)
   14. `apps/` (relocate streamlit/cli/api; rewire imports)
3. **Find-and-replace import paths** via one Python migrator script
4. **Update Makefile, pyproject.toml, .env paths**
5. **Run pytest; iterate on breakage**
6. **Boot Streamlit; smoke-test all 9 scenarios**

Same blast-radius shape as the previous restructure (~30-50 files, mechanical
import rewrites, no LLM calls needed to verify).

## Verification

1. `pytest tests/unit/` — fast, no LLM, every module imports cleanly
2. `pytest tests/integration/` — real SQLite, no LLM, vault operations work
3. `pytest tests/e2e/` — full Streamlit smoke + scenario decomposition
4. `make app` — Streamlit boots; sidebar shows 9 (or 9+N utility) scenarios
5. `python -c "import openacad; print(openacad.SCENARIOS)"` — public API works
6. `grep -rn "from harness\|from tools\|from domain" src/ apps/ scripts/ tests/`
   returns nothing — all import paths migrated
7. Existing screenshots regenerate identically (visual regression check)

## Out of scope

- No new agents implemented (all 5 new ones are stubs)
- No new functional capabilities — pure restructure
- No data migration (vault paths unchanged)
- No `.env`, OpenRouter, or model swap changes
- No deletion of `apps/streamlit/` — kept until Next.js reaches parity
- No commit message changes / git history rewrites
- Next.js app build is NOT part of this — handled separately

## Open risk

- **Scenarios from YAML**: shifts compile-time type checking to runtime. Loader must validate aggressively. Acceptable trade-off for the data/code separation.
- **One-file-per-tool granularity in `notes/query/`**: 5 separate files for what's essentially one capability cluster. Worth it for narrative clarity ("there are 4 query modes"), but could be over-fragmented.
- **`feedback/timeline.py` as a single file**: will grow. Plan for splitting into `timeline/{writer,reader,replay}.py` if it crosses ~400 lines.
- **Agent stub proliferation**: 5 new stubs nobody asked to implement. They serve as architectural commitments / documentation more than working code. Worth the disk space.

## What comes next (writing-plans)

After spec sign-off, write a detailed migration plan at
`docs/superpowers/plans/2026-05-25-greenfield-restructure-plan.md` that
specifies:

- Exact file-by-file move map (~80 entries)
- Import-path substitution table
- Order of operations with checkpoints
- Per-step verification gates
- Rollback strategy if pytest goes red
