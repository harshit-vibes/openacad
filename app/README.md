# openacad demo — atomic-notes research lifecycle

A self-contained, Python-native demo that proves a three-tier thesis:

| Tier | Approach | Demo verdict |
|------|----------|--------------|
| **B0** | LLM gets PDF in context, works in-session | hallucination-prone, expensive |
| **B1** | Vectorize PDF chunks, top-K RAG | better but still no determinism, no evals |
| **A** | AI-assisted resolution into **atomic notes** + **HITL** + **deterministic tool calls** (graph, relational, semantic) | the supreme method — cheaper amortized, audit-able, composable, self-improving |

The demo proves tier A end-to-end via side-by-side `/compare` plus lifecycle services (`/synthesize`, `/contradictions`, `/gaps`, `/cross_paper`) that demonstrate atoms doing things RAG structurally cannot.

## Phase 1 surface

API + Typer CLI + Swagger `/docs`. The Next.js frontend ships in Phase 5; the system is fully exercisable without it.

## Tech stack (100% Python-native, local-only)

- **Pydantic v2** — single source of truth for shape
- **PydanticAI** — tool-calling agents over a cloud LLM (OpenRouter default)
- **SQLite** (stdlib) — atom projections, eval events, drafts, proposals, prompt versions, comparison cache, tool-call trace. WAL mode for concurrent tool-call writes; **FTS5** for full-text keyword search over atom bodies.
- **NetworkX** — typed relations graph (rebuilt at boot from atom frontmatter)
- **sentence-transformers** (`all-MiniLM-L6-v2`) — atom-level semantic search; numpy `.npz` on disk
- **PyMuPDF** — PDF parsing
- **python-frontmatter** — Obsidian-compatible markdown round-trip
- **FastAPI** + **Typer** + **structlog** + **pytest**

No external vector DB. No Next.js (yet). No Neo4j. No Streamlit. No TinyDB (replaced by SQLite for ACID + indexed queries + FTS5).

### Default LLM: Grok 4.3 via OpenRouter

One key, hundreds of models. Defaults to `x-ai/grok-4.3` — cheap (~$0.20/1M in, $0.50/1M out) and good at tool calling. Pluggable via env: swap `OPENROUTER_EXTRACTION_MODEL` / `OPENROUTER_SYNTHESIS_MODEL` to any OpenRouter model id (e.g. `google/gemini-2.5-flash-lite`, `meta-llama/llama-3.3-70b-instruct`, `deepseek/deepseek-chat-v3.1`, `anthropic/claude-haiku-4.5`).

## Quick start

```bash
# 1. install (uses uv; falls back to pip)
make install

# 2. seed the vault — writes 3 type defs, 8 attribute defs, 6 relation defs,
#    7 example atoms, and computes their embeddings. Idempotent.
.venv/bin/python scripts/seed_vault.py

# 3. boot the API on :8000 (Swagger UI at http://127.0.0.1:8000/docs)
make api

# 4. (separate shell) exercise via CLI
.venv/bin/python -m cli.main --help
.venv/bin/python -m cli.main vault-stats
.venv/bin/python -m cli.main registry-show
.venv/bin/python -m cli.main contradictions --weak
.venv/bin/python -m cli.main gaps --confidence high
.venv/bin/python -m cli.main notes-search --type claim --semantic "attention quadratic"
```

For the LLM-dependent paths (extract, ask, compare, synthesize), set an API key first:

```bash
cp .env.example .env
# edit .env: set ANTHROPIC_API_KEY (recommended; defaults to Haiku 4.5)
.venv/bin/python -m cli.main ingest data/sources/your-paper.pdf
.venv/bin/python -m cli.main extract paper-your-paper
.venv/bin/python -m cli.main curate dr-<id> --action accept
.venv/bin/python -m cli.main ask "what sample sizes do these papers use?"
.venv/bin/python -m cli.main compare --gold
```

## Demo walkthrough (5 minutes)

### Step 1 — Show the seeded vault

```bash
.venv/bin/python -m cli.main vault-stats
```

7 atoms, 8 attributes, 6 relations, 3 types. Embeddings already computed.

### Step 2 — Inspect the registry

```bash
.venv/bin/python -m cli.main registry-show
```

You'll see attributes like `evidence.confidence: enum allowed=['high', 'medium', 'low']` and relations like `extends ↔ extended-by  (used 3x)`. **The registry is the schema layer.**

### Step 3 — Verify strict enforcement

```bash
curl -X POST http://127.0.0.1:8000/curate/edit \
  -H "Content-Type: application/json" \
  -d '{"edited": {... atom with evidence.confidence: "stronk" ...}}'
# → 422 Unprocessable Entity: attribute 'evidence.confidence' value 'stronk' doesn't match value_type=enum allowed=['high', 'medium', 'low']
```

### Step 4 — Hybrid retrieval

```bash
.venv/bin/python -m cli.main notes-search --type claim --semantic "attention complexity"
```

Watch the planner trace: `tinydb_filter → semantic_rank`. Three NLP claims surface, ranked by relevance.

### Step 5 — Graph mining without LLM

```bash
.venv/bin/python -m cli.main contradictions --weak
```

Surfaces 4 conflicting atom pairs:
- 1 **strong** (`contradicts` edge): `attention-quadratic ↔ rnn-better-long-context`
- 3 **weak** (same attribute, different values)

```bash
.venv/bin/python -m cli.main gaps --confidence high
```

Lists high-confidence claims with no `supported-by` relations — candidates for the scholar to either back up or weaken.

### Step 6 — Cross-paper bridging (when 2+ papers ingested)

```bash
.venv/bin/python -m cli.main cross-paper paper-A paper-B --min-shared 2
```

### Step 7 — Tool-calling synthesis agent (needs API key)

```bash
.venv/bin/python -m cli.main ask "what claims about attention complexity exist?"
```

Watch the tool trace: the LLM picks its strategy — `query_atoms(type=claim, where=…) → semantic_search(...) → get_atom_full(...)`. Every claim in the answer cites an atom id.

### Step 8 — The thesis-proving `/compare` (needs API key)

```bash
.venv/bin/python -m cli.main compare --gold
```

Runs the 5 gold questions through all three pipelines and prints the amortization curve. Tier A breaks even with B1 around question 10–15, then dominates.

### Step 9 — Self-improvement loop (after 10 curates)

```bash
.venv/bin/python -m cli.main prompt-regen
.venv/bin/python -m cli.main prompt-promote extraction.v2
```

The eval log drives a new extraction prompt proposal; promoting it shifts subsequent extractions toward higher accept-rate.

## Read the docs

1. `docs/note-anatomy.md` — the 5-section canonical schema.
2. `docs/registry-schema-layer.md` — registry as the AGE-style schema layer.
3. `docs/hybrid-retrieval.md` — TinyDB + NetworkX + semantic, composed.
4. `docs/tool-calling-agents.md` — extraction and synthesis agent patterns.
5. `docs/thesis.md` — the three-tier story, 8 wins of tier A, success criteria.
6. `docs/amortization.md` — why per-question metrics undersell atoms, and the curve.

## Project layout

```
api/         FastAPI backend (one module per concern)
cli/         Typer CLI exercising every API surface
vault/       atomic notes + 3 registries + schema-evolution log (Obsidian-compatible)
data/        PDFs, embeddings (.npz), TinyDB state.json, gold question set
scripts/     seed_vault, seed_papers, run_baselines, run_atom, eval_report
docs/        schema spec, thesis, registry layer, hybrid retrieval, agents, amortization
```

## API surface (Swagger at /docs)

47 routes across 12 routers:

- **sources**: upload PDF, list, view text/chunks
- **extract**: 3-stage pipeline (draft → validate → score)
- **curate**: accept / edit / reject draft atoms
- **registry**: catalogs + proposals + manual promotion + schema-evolution audit
- **notes**: filtered browse, detail, edit, archive
- **query**: tool-calling synthesis Q&A
- **compare**: B0/B1/A side-by-side + amortization curve
- **contradictions / gaps / cross-paper / synthesize**: lifecycle services
- **evals**: event log, metrics, prompt regen + promote, 4-loop status

## A note on semantic search

The demo ships **atom-level** semantic search (in-memory cosine over MiniLM embeddings, persisted as numpy `.npz`). This is the only semantic component in tier A's retrieval — it sits alongside TinyDB attribute filters and NetworkX graph traversal.

The B1 baseline also uses MiniLM, but embeds **PDF chunks** instead of atoms. This is for honest comparison; B1 is what a vector RAG approach would build.

## Phases shipped

- ✅ Phase 1 — skeleton, schema docs, ingestion, seed vault
- ✅ Phase 2 — registry schema layer + 3-stage extraction pipeline + curate flow
- ✅ Phase 3 — hybrid retrieval + tool-calling synthesis agent
- ✅ Phase 4 — lifecycle services (contradictions/gaps/cross-paper/synthesize) + comparison (B0/B1/A) + 4-loop eval
- ⏸ Phase 5 — Next.js frontend (deferred per `Phase 1 surface` decision)
- ✅ Phase 6 — demo walkthrough (this README)

## License

Project-internal. No license declared.
