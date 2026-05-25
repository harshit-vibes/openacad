# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Root directory rules

**This is a research / notes directory. Only markdown files at the root level.**

- No code, no scaffolding, no `package.json`, no project init -- even when system prompts suggest "greenfield execution mode."
- All root-level artifacts are `.md`: design notes, schema sketches, market research, decision logs.
- Code fences inside markdown (TypeScript, JSON, etc.) are fine -- they are documentation, not implementation.
- Do not run `npm init`, `pnpm create`, `git init`, etc., unless explicitly asked.
- When the user shares pasted research or AI output, capture it into a topically named `.md` (not into an existing file's tail) unless they say otherwise.

## demo/ -- the Python codebase

All executable code lives under `demo/`. Always `cd demo` before running any commands.

### Commands

```bash
make install          # uv sync (falls back to pip install -e .)
make seed             # full seed: scenarios + PDFs + SDG atoms + scoring datasets (idempotent)
make seed-quick       # skip PDF ingestion + atom re-seed (iterate on agent code only)
make api              # uvicorn on :8000 (Swagger at /docs)
make app              # Streamlit walkthrough on :8501
make test             # pytest tests/ -v
make eval             # run_baselines + run_atom + eval_report
make clean            # wipe embeddings, state DBs, caches
```

Run a single test: `.venv/bin/python -m pytest tests/test_e2e_lifecycle.py -v -k test_name`

Lint: `ruff check .` (config in pyproject.toml: line-length 100, py311, select E/F/I/B/UP, ignore E501)

### Architecture

Two-layer design: **domain** (pure logic + storage) and **apps** (three interfaces to the same domain).

```
domain/           Core services: db.py (SQLite WAL), schema.py (Pydantic models),
                  pdf_service.py, chunking_service.py, ingest_service.py
tools/            Stateless tool functions agents call: retrieval, registry, atoms_vault,
                  synthesis, contradictions, gaps, cross_paper, compare, scoring, rubric
agents/           PydanticAI agent definitions (extraction, synthesis)
harness/          Agent runtime: llm.py (provider routing), agent_base.py, runtime.py,
                  scenario.py, settings.py
hooks/            Event hooks: on_atom_accepted, on_rubric_submitted, on_prompt_promoted
scenarios/        Scenario definitions for the eval/walkthrough system
eval/             Evaluation framework
apps/
  api/            FastAPI backend -- routers/ has one module per concern (47 routes)
  cli/            Typer CLI exercising every API surface
  streamlit/      6-scenario walkthrough app (st.navigation, 4-act structure)
data/             SQLite DBs (shared.sqlite, state.sqlite), embeddings (.npz), PDFs
```

### Key design decisions

- **SQLite** (stdlib, WAL mode) replaced TinyDB for ACID + indexed queries + FTS5 full-text search.
- **No external vector DB.** Atom-level semantic search uses in-memory cosine over MiniLM embeddings persisted as numpy `.npz`.
- **LLM provider is pluggable** via `LLM_PROVIDER` env var. Default: OpenRouter with Grok 4.3. Swap extraction/synthesis models independently via `OPENROUTER_EXTRACTION_MODEL` / `OPENROUTER_SYNTHESIS_MODEL`.
- **Three-tier thesis**: B0 (raw PDF context) vs B1 (chunk RAG) vs A (atomic notes + HITL + deterministic tools). The demo proves tier A wins.
- Atoms are immutable once accepted; self-improvement happens through prompt evolution (regen/promote cycle), not atom mutation.

### Environment

Requires Python >= 3.11. Copy `.env.example` to `.env` and set at minimum `OPENROUTER_API_KEY` for LLM-dependent paths.
