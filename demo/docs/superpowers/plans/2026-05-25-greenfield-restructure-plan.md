# Greenfield Restructure — Execution Plan

**Spec:** [`2026-05-25-greenfield-restructure-design.md`](../specs/2026-05-25-greenfield-restructure-design.md)
**Date:** 2026-05-25
**Status:** Executing

## Scope

Realize the spec's target tree in one mechanical migration pass. Out-of-scope
items (new agent implementations, Next.js app, model swaps) are NOT touched.

## Pre-flight (already done)

- ✅ Streamlit instance stopped
- ✅ All 9 scenario vaults are seeded (atoms-only/attrs/attrs-rels just completed)
- ✅ pytest baseline: 22/22 structural tests passing

## Steps

### S1 — Create new directory skeleton under `src/openacad/`

```bash
mkdir -p src/openacad/{runtime/{corpus,answerers},notes/{schema,intake,curation,revision,persistence,registry,query},artifacts/{schema,composition,assessment,ingestion,persistence},feedback/{rubric,verdicts,scoring,refinement},agents,hooks,scenarios/prompts/{_defaults,_overrides}}
```

Drop a placeholder `__init__.py` in every package.

### S2 — Move files (dependency order — settings/scenario types FIRST)

Per the spec's "Migration approach" section, in order:

| # | From | To |
|---|---|---|
| 1 | `harness/settings.py` | `src/openacad/runtime/settings.py` |
| 2 | `harness/scenario.py` (the type + ContextVar; instances split out in S5) | `src/openacad/runtime/scenario.py` |
| 3 | `harness/llm.py` | `src/openacad/runtime/llm.py` |
| 4 | `harness/agent_base.py` | `src/openacad/runtime/agent_base.py` |
| 5 | `harness/runtime.py` | `src/openacad/runtime/dispatcher.py` |
| 6 | `domain/db.py` | `src/openacad/runtime/db.py` |
| 7 | `domain/pdf_service.py` | `src/openacad/runtime/corpus/pdf.py` |
| 8 | `domain/chunking_service.py` | `src/openacad/runtime/corpus/chunking.py` |
| 9 | `domain/ingest_service.py` | `src/openacad/runtime/corpus/ingest.py` |
| 10 | `domain/schema.py` | `src/openacad/notes/registry/validation.py` |
| 11 | `domain/models/atom.py` | `src/openacad/notes/schema/note.py` |
| 12 | `domain/models/registry.py` | `src/openacad/notes/registry/schema.py` |
| 13 | `domain/models/eval.py` | `src/openacad/feedback/schema.py` |
| 14 | `domain/models/source.py` | `src/openacad/runtime/corpus/source.py` |
| 15 | `domain/models/query.py` | `src/openacad/runtime/queries.py` |
| 16 | `tools/atoms_vault.py` | `src/openacad/notes/persistence/vault.py` |
| 17 | `tools/atoms_curate.py` | `src/openacad/notes/curation/__init__.py` (re-exports accept/edit/reject) |
| 18 | `tools/atoms_extract.py` | `src/openacad/notes/intake/from_chunks.py` |
| 19 | `tools/retrieval.py` | `src/openacad/notes/query/hybrid.py` |
| 20 | `tools/retrieval_semantic.py` | `src/openacad/notes/query/semantic.py` |
| 21 | `tools/registry.py` | `src/openacad/notes/registry/__init__.py` (re-exports) |
| 22 | `tools/registry_graph.py` | `src/openacad/notes/persistence/graph_index.py` |
| 23 | `tools/answer_b0.py` | `src/openacad/runtime/answerers/cold.py` |
| 24 | `tools/answer_b1.py` | `src/openacad/runtime/answerers/semantic.py` |
| 25 | `tools/answer_b2.py` | `src/openacad/runtime/answerers/lexical.py` |
| 26 | `tools/rubric.py` | `src/openacad/feedback/rubric/__init__.py` |
| 27 | `tools/scoring.py` | `src/openacad/feedback/scoring/__init__.py` |
| 28 | `tools/synthesis.py`, `tools/compare.py`, `tools/contradictions.py`, `tools/cross_paper.py`, `tools/gaps.py`, `tools/eval_report.py` | DELETE (unused stubs — CLI only, can re-add when needed) |
| 29 | `agents/extractor/agent.py` → unchanged path | `src/openacad/agents/extractor/agent.py` (mv whole dir) |
| 30 | `agents/synthesizer/` | `src/openacad/agents/synthesizer/` |
| 31 | `agents/scorer/` | `src/openacad/agents/scorer/` |
| 32 | `agents/meta_evaluator/agent.py` — split | `src/openacad/agents/meta_evaluator/agent.py` (builder) + `src/openacad/feedback/refinement/proposer.py` (logic) |
| 33 | `agents/paper_writer/`, `agents/book_writer/` | unchanged path under `src/openacad/agents/` |
| 34 | `hooks/*` | `src/openacad/hooks/*` (move + add new on_note_acquired, on_note_revised, on_artifact_composed, on_artifact_assessed) |
| 35 | `scenarios/prompts/*` | `src/openacad/scenarios/prompts/_defaults/*` (flat defaults) + `_overrides/<key>/*` (existing per-scenario overrides) |

### S3 — Convert scenarios from Python to YAML

- Read `scenarios/definitions.py` programmatically (import + serialize each Scenario)
- Write `src/openacad/scenarios/catalog.yaml`
- Write `src/openacad/scenarios/loader.py` that parses YAML → Scenario instances + caches them
- `src/openacad/runtime/scenario.py` re-exports `SCENARIOS, SCENARIOS_BY_KEY` from `loader.load()` so consumers keep working

### S4 — Create new empty stubs

- `src/openacad/artifacts/` — schema/, composition/, assessment/, ingestion/, persistence/ each get a README.md + minimal `__init__.py`
- `src/openacad/agents/{critic,consistency_checker,coverage_analyzer,gap_analyzer,briefing_writer}/` each get prompt.md + tools.toml + README.md (no agent.py)
- `src/openacad/feedback/timeline.py` — append-only SQLite-backed event log (skeleton with `log_event()`, `read_events()`)
- `src/openacad/hooks/on_agent_action.py`, `on_note_acquired.py`, `on_note_revised.py`, `on_artifact_composed.py`, `on_artifact_assessed.py` — skeleton hook files that delegate to feedback.timeline.log_event
- `src/openacad/runtime/tool_registry.py` — `@tool` decorator + lookup skeleton

### S5 — Split `tools/atoms_curate.py` into 3 files

- `notes/curation/score.py` (was domain/schema.score-related logic — actually scoring lives in atoms_extract.py:score())
- `notes/curation/accept.py` (was accept())
- `notes/curation/edit.py` (was edit())
- `notes/curation/reject.py` (was reject())
- `notes/curation/__init__.py` re-exports for back-compat

### S6 — Split `tools/registry.py` into 4 files

- `notes/registry/attributes.py`
- `notes/registry/relations.py`
- `notes/registry/kinds.py`
- `notes/registry/evolution.py` (recount_usage_and_promote)
- `notes/registry/__init__.py` re-exports

### S7 — Bulk import-path migration

Generate `.migrate_imports_greenfield.py` with rename map:

```
api.services.X         → openacad.notes.X / openacad.runtime.X / openacad.feedback.X (per S2 table)
harness.*              → openacad.runtime.*
domain.db              → openacad.runtime.db
domain.models          → openacad.notes.schema / openacad.runtime.corpus.source / openacad.feedback.schema
domain.{pdf,chunking,ingest,schema}_service → openacad.runtime.corpus.* / openacad.notes.registry.validation
tools.atoms_vault      → openacad.notes.persistence.vault
tools.atoms_curate     → openacad.notes.curation
tools.atoms_extract    → openacad.notes.intake.from_chunks
tools.retrieval        → openacad.notes.query.hybrid
tools.retrieval_semantic → openacad.notes.query.semantic
tools.registry         → openacad.notes.registry
tools.registry_graph   → openacad.notes.persistence.graph_index
tools.answer_b0/b1/b2  → openacad.runtime.answerers.{cold,semantic,lexical}
tools.rubric           → openacad.feedback.rubric
tools.scoring          → openacad.feedback.scoring
agents.X.agent         → openacad.agents.X.agent
hooks.X                → openacad.hooks.X
scenarios.definitions  → openacad.scenarios.loader
```

Run script across `apps/`, `tests/`, `scripts/`, and `src/openacad/` itself.

### S8 — Update config and entry points

- `Makefile` — `streamlit run src/openacad/../apps/streamlit/...` actually the path may stay; sys.path the project root
- `pyproject.toml` — `packages = ["openacad"]`, `[tool.hatch.build.targets.wheel] packages = ["src/openacad"]`
- `tests/test_streamlit_pages.py` — `PAGES_DIR = DEMO_ROOT / "apps" / "streamlit" / "walkthrough"` (unchanged — apps/ stays at top)
- `apps/streamlit/walkthrough/*.py` — DEMO_ROOT calc unchanged; only imports change
- `.env` — unchanged
- pytest sys.path: set `pythonpath = ["src"]` in `[tool.pytest.ini_options]` so `import openacad` works

### S9 — Public API in `src/openacad/__init__.py`

```python
from openacad.runtime.scenario import (
    Scenario, Tier, AgentRole, Step,
    SCENARIOS, SCENARIOS_BY_KEY,
    active_scenario, use_scenario,
)
from openacad.runtime.dispatcher import ask
from openacad.notes.curation import accept, edit, reject
from openacad.notes.persistence.vault import list_atoms, read_atom
from openacad.notes.query import semantic, lexical, hybrid
from openacad.feedback.rubric import record as capture_rubric
from openacad.feedback.refinement import propose_prompt, promote_prompt

__all__ = [...]
```

### S10 — Verification

1. `pytest tests/test_streamlit_pages.py tests/test_scenario_decomposition.py` — 22 tests should pass
2. `pytest tests/test_e2e_lifecycle.py -k "not test_each_scenario_answers and not test_compare and not test_scoring_runs and not test_meta_eval"` — non-LLM e2e tests
3. `make app` — Streamlit boots; sidebar shows 9 scenarios; click into each
4. `grep -rn "from harness\|from tools\|from domain\|from api" apps/ scripts/ tests/ src/openacad/` returns nothing
5. `python -c "import openacad; print(len(openacad.SCENARIOS))"` → 9

## Rollback strategy

The migration uses `mv` not `cp`, so a partial state exists if something fails
mid-way. Recovery: `git status` shows the moves; reverse with `mv` calls or
`git checkout`. The current repo is NOT a git repo (per env header), so
**before starting S2 I will `git init` + initial commit** so each phase has
checkpoints.

Wait — env header says `Is a git repository: false`. The user has explicitly
not wanted git initialized previously (CLAUDE.md note about `openacad/` parent
being a research notes directory). So no git init.

Mitigation without git: do the moves in small chunks, run pytest between
chunks, log every mv to a journal file so reverse-migration is mechanical.

## Order of operations (with checkpoint gates)

| Chunk | Steps | Gate |
|---|---|---|
| A | S1 + S2 (1-8) — runtime + corpus | `python -c "from openacad.runtime.scenario import SCENARIOS"` works |
| B | S2 (10-15) — domain/models split | imports resolve |
| C | S2 (16-22) — tools → notes | imports resolve |
| D | S2 (23-25) — tools → runtime/answerers | imports resolve |
| E | S2 (26-27) — feedback/rubric + scoring | imports resolve |
| F | S2 (29-33) — agents | imports resolve |
| G | S2 (34) — hooks | imports resolve |
| H | S2 (35) + S4 + S5 + S6 — new structure + splits | imports resolve |
| I | S3 — scenarios YAML | `python -c "from openacad import SCENARIOS"` → 9 items |
| J | S7 — bulk import migration across apps/tests/scripts | pytest |
| K | S8 + S9 — config + public API | pytest + boot |
| L | S10 — final verify + screenshot regen | done |

## Estimated tool-call budget

~80 file moves + ~5 splits + ~15 new stub files + ~1 migrator script + ~5
config edits + ~3-5 verification runs ≈ 100-120 tool calls. Doable in one
session given current context budget.
