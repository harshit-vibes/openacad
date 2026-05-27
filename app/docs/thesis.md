# Thesis — what this demo proves

## The three-tier claim

| Tier | Description | What it lacks |
|------|-------------|---------------|
| **B0** | LLM gets the PDF in-context, works in-session | hallucination-prone, no evaluations, token-heavy |
| **B1** | Vectorize the PDF, retrieve chunks, answer | better perf, lower cost; still non-deterministic, still no evals |
| **A** | AI-assisted resolution of PDFs into **atomic notes** + **HITL** + **deterministic tool calls** (graph, relational, semantic) for synthesis, deep work, etc. | the demo's target |

Tier A is the supreme method. This demo proves it end-to-end.

## The eight wins of tier A

Beyond the obvious cheaper/accurate, tier A has structural advantages the other tiers cannot reach:

| Win | What it means | Where you see it in the demo |
|-----|---------------|------------------------------|
| **Cheaper** | atom-RAG token-in is a fraction of B0; competitive with B1 per-query and dominant after amortization | `/compare` per-question + amortization curve |
| **Accurate** | structured retrieval surfaces precisely-relevant atoms; LLM has less room to hallucinate | `/compare` accuracy_vs_gold |
| **Controllable** | scholar curates every atom; LLM never writes to disk | `/extract/draft` → `/curate` flow; eval log shows every mutation |
| **Self-improving** | accept/edit/reject signal drives 4 refinement loops | `/evals`, `extraction/v{N}.md` versions |
| **Composable** | structured queries impossible in RAG (`type=claim ∧ contradicts→type=finding ∧ evidence=empirical`) | `/query` tool trace + explain output |
| **Reusable** | each atom outlives its extraction question; tomorrow's query surfaces yesterday's atom in a new combination | re-ask different question against same vault, watch atom-reuse |
| **Audit-able** | every answer cites a *single atom*, not a page range or chunk | synthesis answer rendering with `[[atom-id]]` citations |
| **Inspectable** | the graph is editable; the scholar can see, fix, archive any unit | `/registry` + `/notes` browse + edit |

## How `/compare` proves it

Same question, same source papers, three pipelines.

### Pipeline B0 — full-document baseline

Dump the source paper(s) into the LLM context, ask the question.

- Tokens: very high (paper-length + question + answer).
- Latency: dominated by LLM input processing.
- Citations: page-range at best.
- Hallucination risk: significant.

### Pipeline B1 — vector RAG baseline

Chunks of the raw PDFs are embedded with the same MiniLM model used for atom embeddings. Top-K chunks + question → LLM.

- Tokens: medium (K chunks × ~512 chars + question + answer).
- Latency: embedding cache + LLM call.
- Citations: page-range or chunk-id.
- Hallucination risk: lower than B0, still present.

### Pipeline A — atom-RAG with tool-calling agent

The synthesis agent receives the question + a registry summary + a tool list. It picks its retrieval strategy by calling tools:
- `query_atoms(type, where)` — SQLite attribute filters
- `traverse(atom_id, via, hops)` — NetworkX relation walks
- `semantic_search(query)` — in-memory cosine over atom embeddings
- `get_atom_full(id)` — full body when summary insufficient
- `check_contradiction(a, b)` — typed contradiction lookup

The agent composes these tools, synthesizes an answer, and returns it with inline `[[atom-id]]` citations + the full tool-call trace.

- Tokens: low (typically 3-8 atoms × ~80-200 tokens each + question + answer + tool overhead).
- Latency: tool calls add roundtrips, but each call is cheap.
- Citations: precise atom IDs, each resolving to a single span.
- Hallucination risk: very low; answers are bounded by what the tools returned.

## Reported metrics

For each pipeline, per question:

| Metric | Definition |
|--------|------------|
| `tokens_in` | LLM input tokens (all calls combined). |
| `tokens_out` | LLM output tokens. |
| `latency_ms` | End-to-end wall time. |
| `accuracy_vs_gold` | LLM-as-judge or hand-graded score against `data/gold/answers.yaml` (0–1). |
| `citation_precision` | proportion of citations that resolve to a single unambiguous unit (atom IDs always 1.0; page ranges variable). |
| `n_units_retrieved` | atoms vs chunks vs whole-doc. |
| `tool_calls` (A only) | list of tools invoked, in order. The audit trail. |

## Amortization — the missing chart

Per-question metrics underrate tier A because tier A has real upfront cost (extraction + curation). The honest comparison is amortized over N questions per paper:

| Pipeline | Upfront cost | Per-query cost | Break-even N |
|----------|--------------|----------------|--------------|
| B0 | 0 | very high | n/a (always expensive) |
| B1 | small (chunk embedding) | medium | tier A wins after ~3 queries |
| A | high (LLM extract + scholar curate) | very low | wins B1 around N=10–15, then dominates |

`/compare` returns both the per-question table and the amortization curve. The curve is the rhetorical centerpiece: it shows that **atoms are durable assets**, while B0/B1 retrievals are **single-use**.

## Success criteria

For the demo to be considered successful, the gold-set average must show:

- **Tokens**: A ≥ 5× cheaper than B1 per query; B1 ≥ 3× cheaper than B0.
- **Accuracy**: A ≥ B1 (bar is "equal or better"; A's structural advantage is on tokens + citations, not raw accuracy).
- **Citations**: 100% of A's citations resolve to a single atom; B0/B1 cite page ranges.
- **Amortization**: A's cumulative cost crosses B1's somewhere in N=10–15.
- **Eval loop**: after 10 curate actions, `extraction/v2.md` proposal is generated; promoting it shifts subsequent extractions toward higher accept-rate.

## Why this isn't a circular argument

*"Of course atom-RAG wins — atoms were hand-curated by the scholar."*

Three responses:

1. **Curation cost is amortized.** A scholar curates an atom once; the system answers many questions from it. Per-question runtime cost is what the scholar actually feels.
2. **Atoms were drafted by the same LLM.** The scholar's curation is *editing* LLM output, not authoring from scratch. The comparison is closer to "LLM with structured working memory" vs "LLM with raw text working memory" than "human" vs "LLM."
3. **The self-improvement loop is the meta-claim.** Even if the first comparison shows modest wins, the trend across prompt versions is the strong claim: accept-rate goes up, edit-distance goes down, and the atom-RAG advantage compounds.

## What this demo does *not* prove

- It does **not** prove atomic notes are the best representation for all research tasks. It proves they win on Q&A, contradiction-finding, gap-detection, cross-paper bridging, and synthesis — i.e., Phases 3–5 of `~/Documents/openacad/lifecycle.md`.
- It does **not** address the philosophical question of "is this *the* atomic level?" — that is answered (negatively) in `~/Documents/openacad/atomic-ideas.md` §9. Atomicity is a *pragmatic level of abstraction*; this demo shows the level works well for AI-assisted research.
- It does **not** scale-test. The vault is small. A 10,000-atom vault is left as future work.
