# Evolving-Notes Ops Console — Design

**Date:** 2026-05-25
**Scope:** Replace the Streamlit "Cross-cutting" section with two new sections (🧰 Workflows + 🛠️ Operations) — 7 read-only dashboard pages, all hard-pinned to the `evolving-notes` scenario (rung 9). No logfire dependency. Adds a domain-layer projections module and a UI widgets layer.

---

## 1. Sidebar IA

```
OVERVIEW              Welcome · Conclusion (Goodness becomes a tab)
THE 9-RUNG LADDER     1..9 (unchanged)
🧰 WORKFLOWS          Ingest · Compose Artifact · Assess Artifact
🛠️ OPERATIONS         Notes & Registry · Curate · Evals & Prompt Hardening · Observability
```

- SESSION section + live counters: **DROPPED**.
- Compose/Assess hard-pinned to `evolving-notes` (no more active-scenario follow).

## 2. Architecture

### Domain projections — `src/openacad/projections/`

Pure functions, no Streamlit. Each takes `scenario_key: str = "evolving-notes"` and uses `with use_scenario(scenario_key):` internally.

```
projections/
├── __init__.py           # re-exports
├── _models.py            # all DTO BaseModels
├── observability.py
├── evals.py
├── curation.py
├── registry.py
└── ingest.py
```

### UI widgets — `apps/streamlit/views/`

Pure render functions. Take DTOs from projections, call `st.*`, return None.

```
views/
├── pin.py                # PINNED_SCENARIO + pinned() ctx-mgr
└── widgets/
    ├── header.py · kpi_row.py · latency_hist.py · cost_rollup.py
    ├── tool_call_table.py · error_log.py · activity_feed.py
    ├── prompt_history.py · verdict_table.py · draft_card.py
    ├── atom_table.py · schema_viewer.py · paper_card.py
```

### Pages — flat under `apps/streamlit/`

```
workflows/{ingest,compose,assess}.py
operations/{notes_registry,curate,evals_prompt_hardening,observability}.py
```

Each page is a thin `render()` that opens `pinned()`, calls a header widget, fetches a projection, renders widgets.

---

## 3. DTO Contracts

All in `src/openacad/projections/_models.py`. Sub-agents code to these.

```python
# ── Ingest ──────────────────────────────────────────────────────────
class PaperRow(BaseModel):
    source_id: str
    title: str
    authors: list[str]
    year: int | None
    pages: int | None
    chunks: int
    atoms: int
    ingested_at: datetime

class PaperLibraryView(BaseModel):
    papers: list[PaperRow]
    total_papers: int
    total_chunks: int
    total_atoms: int
    last_ingested_at: datetime | None

# ── Registry / Notes ────────────────────────────────────────────────
class AtomRow(BaseModel):
    atom_id: str
    kind: str
    content_preview: str  # first 200 chars
    n_attrs: int
    n_rels: int
    source_id: str | None

class AttributeDef(BaseModel):
    key: str
    value_type: str
    allowed_values: list[str] | None
    usage_count: int
    first_seen: datetime | None

class RelationDef(BaseModel):
    key: str
    source_types: list[str]
    target_types: list[str]
    inverse: str | None
    usage_count: int

class RegistryView(BaseModel):
    atoms: list[AtomRow]
    attributes: list[AttributeDef]
    relations: list[RelationDef]
    total_atoms: int
    total_attrs: int
    total_rels: int
    orphan_attrs: list[str]
    orphan_rels: list[str]

# ── Curation ────────────────────────────────────────────────────────
class DraftRow(BaseModel):
    draft_id: str
    source_id: str | None
    drafted_at: datetime
    prompt_version: str
    payload_preview: str

class VerdictRow(BaseModel):
    event_id: str
    timestamp: datetime
    kind: str  # accept/edit/reject/deprecate
    draft_id: str | None
    actor: str
    delta: dict

class CurationView(BaseModel):
    pending_drafts: list[DraftRow]
    verdict_history: list[VerdictRow]
    counts: dict[str, int]  # {accept: N, edit: N, reject: N, deprecate: N, pending: N}

# ── Evals & Prompt Hardening ────────────────────────────────────────
class ComparisonRow(BaseModel):
    id: str
    question: str
    tokens_in: int
    tokens_out: int
    latency_ms: int
    citations: int
    answer_preview: str
    run_at: datetime

class RubricRow(BaseModel):
    id: str
    role: str  # answerer, extractor, ...
    criteria: dict[str, float]  # e.g. {accuracy: 0.9, citation: 0.8}
    timestamp: datetime
    notes: str | None

class PromptTimeline(BaseModel):
    role: str  # answerer, extractor, scorer, meta_evaluator
    versions: list[PromptVersion]  # from openacad.feedback.schema

class MetaProposalRow(BaseModel):
    event_id: str
    timestamp: datetime
    target_role: str
    insight_kind: str
    proposed_change_preview: str
    based_on_events: list[str]
    state: str  # proposed/active/archived

class EvalsView(BaseModel):
    comparison_runs: list[ComparisonRow]
    rubric_scores: list[RubricRow]
    rubric_avg_by_criterion: dict[str, float]
    prompt_timelines: list[PromptTimeline]  # one per role
    meta_proposals: list[MetaProposalRow]

# ── Observability ───────────────────────────────────────────────────
class ToolCallRow(BaseModel):
    id: str
    session_id: str
    agent: str
    tool_name: str
    arguments: dict
    n_results: int
    latency_ms: int
    timestamp: datetime
    error_message: str | None  # new field

class LatencyBucket(BaseModel):
    upper_ms: int  # bucket upper bound
    count: int

class CostRollupItem(BaseModel):
    bucket_label: str  # e.g. "answerer" or "2026-05-23"
    tokens_in: int
    tokens_out: int
    cost_usd: float  # gpt-4o-mini: 0.15/M in, 0.60/M out

class ActivityFeedItem(BaseModel):
    timestamp: datetime
    kind: str  # tool_call, verdict, prompt_promote, rubric, ...
    actor: str
    summary: str  # human-readable one-liner
    detail: dict

class ObservabilityView(BaseModel):
    tool_calls: list[ToolCallRow]
    latency_histogram: list[LatencyBucket]
    cost_by_role: list[CostRollupItem]
    cost_by_day: list[CostRollupItem]
    activity_feed: list[ActivityFeedItem]
    errors: list[ToolCallRow]  # subset where error_message is not None
    n_tool_calls: int
    avg_latency_ms: float
    total_cost_usd: float
    n_errors: int
```

---

## 4. Projection function signatures

```python
# observability.py
def observability_rollup(scenario_key="evolving-notes") -> ObservabilityView: ...

# evals.py
def evals_summary(scenario_key="evolving-notes") -> EvalsView: ...

# curation.py
def curation_summary(scenario_key="evolving-notes") -> CurationView: ...

# registry.py
def registry_view(scenario_key="evolving-notes") -> RegistryView: ...

# ingest.py
def paper_library(scenario_key="evolving-notes") -> PaperLibraryView: ...
```

Data sources (read-only):
- `db.list_sources()` — papers
- `db.list_atom_projections()` — atoms (per-scenario via `use_scenario`)
- `db.list_chunks_for_source()` if exists, else infer via FTS
- `db.list_prompts()` — prompt versions
- `db.list_events(kind=…)` — EvalEvents
- `db.list_proposals()` — meta-eval proposals
- `db.list_comparisons()` — ComparisonResults
- `db.list_tool_calls()` — ToolCalls (per-scenario)
- `db.list_rubric_rows()` — rubric submissions
- `db.upsert_draft` / `db.list_drafts` if it exists; else implement
- Registry schema: `openacad.notes.registry.validation.get_schema()`

---

## 5. Schema changes

`tool_calls` table: add `error_message TEXT` (nullable).

In `db.py::_create_tables()`:
```sql
CREATE TABLE IF NOT EXISTS tool_calls (
  ..., error_message TEXT NULL
)
```

Plus migration block (run on every `connect()`):
```python
try:
    cur.execute("ALTER TABLE tool_calls ADD COLUMN error_message TEXT")
except sqlite3.OperationalError:
    pass  # already added
```

Extend `ToolCall` model in `feedback/schema.py` with `error_message: str | None = None`.

In `agents/synthesizer/agent.py` and `agents/extractor/agent.py` `_log_tool_call(...)`: accept optional `error: str | None = None` and pass through.

Wrap tool bodies in `try/except` that logs the error_message and re-raises.

---

## 6. Seed scripts (NEW)

### `scripts/seed_rubric_scores.py`
For evolving-notes: submit 8-12 RubricRow entries spanning answerer + extractor roles, with `criteria` like `{accuracy: 0.85, citation: 0.92, clarity: 0.78}`. Uses `db.insert_rubric_row` (add if missing).

### `scripts/seed_verdicts.py`
For evolving-notes: emit ~20 EvalEvents with kinds in `{accept, edit, reject}` referencing existing draft_ids. Distribution: 60% accept, 25% edit, 15% reject. Uses `db.log_event`.

### Extend `scripts/seed_meta_eval_insights.py`
For each meta-eval insight already seeded, also emit a paired EvalEvent of `kind="prompt_propose"` with payload referencing `based_on_events`.

---

## 7. Page contents

### 📥 Ingest (`workflows/ingest.py`)
- pipeline strip (PDF→chunks→atoms→registry, static)
- KPI row: papers, chunks, atoms, last_ingested_at
- Paper library table (sortable), expander per row with chunks preview + per-kind atom counts

### 📜 Compose Artifact (`workflows/compose.py`)
- Rewrite of `walkthrough/50_compose.py`: wrap in `pinned()`, add KPI row at top, drop scenario picker, filter artifact history to evolving-notes.

### 🔍 Assess Artifact (`workflows/assess.py`)
- Rewrite of `walkthrough/51_assess.py`: same treatment.

### 🧱 Notes & Registry (`operations/notes_registry.py`)
- 3 tabs: Atoms · Attributes · Relations
- Atoms: paginated table from `RegistryView.atoms` + click-row expander
- Attributes: schema table, sort by usage, orphan callout
- Relations: schema table, missing-inverse callout

### ✍️ Curate (`operations/curate.py`)
- KPI row: counts dict
- Pending drafts: list of draft_cards
- Verdict history table
- (Optional) verdict trend sparkline by day (skip if matplotlib not available)

### ⭐ Evals & Prompt Hardening (`operations/evals_prompt_hardening.py`)
- 4 tabs: Comparison Runs · Rubric Scores · Prompt Versions · Meta-Eval Proposals
- Each tab consumes one slice of `EvalsView`

### 📡 Observability (`operations/observability.py`)
- KPI row: n_tool_calls, avg_latency_ms, total_cost_usd, n_errors
- Latency histogram (st.bar_chart on bucket data)
- Cost rollup: tabs "By role" / "By day" with bar charts
- Tool call table (filterable by agent/tool)
- Activity feed (chronological)
- Error log (separate section, only shown if errors > 0)

---

## 8. Conclusion page tabs

`apps/streamlit/walkthrough/90_conclusion.py` becomes:

```python
tab_thesis, tab_goodness = st.tabs(["🎓 Thesis", "📐 Goodness"])
with tab_thesis: _render_thesis()  # existing content
with tab_goodness: _render_goodness()  # ported from 95_goodness.py
```

Delete `apps/streamlit/walkthrough/95_goodness.py`. Drop `PAGE_GOODNESS` from `streamlit_app.py`.

---

## 9. Sidebar registration (`streamlit_app.py`)

```python
WORKFLOWS_PAGES = [
    st.Page("workflows/ingest.py",  title="📥 Ingest"),
    st.Page("workflows/compose.py", title="📜 Compose Artifact"),
    st.Page("workflows/assess.py",  title="🔍 Assess Artifact"),
]
OPERATIONS_PAGES = [
    st.Page("operations/notes_registry.py",         title="🧱 Notes & Registry"),
    st.Page("operations/curate.py",                  title="✍️ Curate"),
    st.Page("operations/evals_prompt_hardening.py",  title="⭐ Evals & Prompt Hardening"),
    st.Page("operations/observability.py",           title="📡 Observability"),
]

PAGES = [PAGE_WELCOME, *SCENARIO_PAGES, PAGE_CONCLUSION, *WORKFLOWS_PAGES, *OPERATIONS_PAGES]
```

In `_render_sidebar()`:
- After ladder section, add `_section_label("Workflows")` + page_link loop
- Then `_section_label("Operations")` + page_link loop
- Delete the SESSION section + counters entirely

---

## 10. Testing

- `tests/test_streamlit_pages.py`: expected count → **18** (2 overview + 9 ladder + 7 cross-cutting)
- NEW `tests/test_projections.py`: one test per projection asserting DTO shape + key invariants on seeded evolving-notes data
- Existing tests untouched

---

## 11. Build order (parallel agents)

Three independent batches:

**Batch 1 (parallel — 3 agents):**
- Agent P: projections module (5 modules + `_models.py` + `__init__.py` + `tests/test_projections.py`)
- Agent W: widgets module (`apps/streamlit/views/` complete)
- Agent S: schema/seed (add `error_message` column + migrate + extend `ToolCall` + try/except wrap + 2 new seed scripts + extend `seed_meta_eval_insights.py`)

**Batch 2 (sequential — single agent):**
- Agent C: pages (7 page files) + Conclusion tab refactor + sidebar restructure + delete old files (60_timeline, 95_goodness) + update `test_streamlit_pages.py` expected count

**Batch 3:**
- Run pytest, run seed scripts, fix any breakage.

---

## 12. Out of scope

- Logfire integration (deferred per user decision)
- Live PDF upload + real-time extraction (Ingest is read-only)
- Mutations (no accept/edit/reject buttons on Curate; no prompt promote button on Evals)
- Per-page scenario picker (hard-pinned to evolving-notes)
- New mutation APIs / new HTTP routes
