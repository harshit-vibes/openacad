# Amortization — Why Atoms Pay Off

## The per-question metric undersells tier A

`/compare` reports per-question metrics for B0 (full doc), B1 (vector RAG), A (atom-RAG). On a *single* question, A might look only marginally better than B1 on tokens, and worse on latency (because tool calls add roundtrips).

This is the wrong frame.

The honest comparison is **amortized cost across N questions per paper**. Atoms are durable assets — extracted once, queried many times. B0 and B1 do all their work per-question.

## The cost equation

| Pipeline | Upfront cost (per paper) | Per-question cost | Cumulative at question N |
|----------|--------------------------|-------------------|--------------------------|
| **B0** | 0 | `C_B0` (very high — paper-length context) | `N · C_B0` |
| **B1** | `E_chunks` (one embedding pass) | `C_B1` (medium — K chunks) | `E_chunks + N · C_B1` |
| **A** | `E_extract + C_curate` (LLM extraction + scholar time) | `C_A` (low — few atoms + tool overhead) | `E_extract + C_curate + N · C_A` |

Where roughly:
- `C_B0` ≈ 8,000–30,000 tokens per question (paper-dependent)
- `C_B1` ≈ 2,000–4,000 tokens per question (K chunks × ~512 chars)
- `C_A` ≈ 400–800 tokens per question (3–8 atoms × ~100 tokens + tool overhead)
- `E_extract` ≈ ~5,000–10,000 tokens (one-shot extraction per paper)
- `E_chunks` ≈ negligible cost (local embedding model)
- `C_curate` is scholar-time, not token cost — typically 5–15 minutes per paper

## Break-even points

Setting cumulative costs equal:

**A vs B1**: `E_extract + N · C_A = E_chunks + N · C_B1`

With representative numbers:
`5000 + N · 600 = 0 + N · 3000`
`5000 = N · 2400`
`N ≈ 2` questions

But this ignores `C_curate` (scholar time). If we add a rough token-equivalent cost for scholar attention, break-even shifts to **N ≈ 10–15 questions** per paper. After that, tier A dominates and the gap widens linearly.

**A vs B0**: never — B0's per-question cost is always too high.

## The chart `/compare` returns

`POST /compare {questions: [...], paper_ids: [...]}` returns the per-question table plus the cumulative cost curve:

```
tokens cumulative
^
|                     B0 (slope = C_B0, large)
|                     /
|                    /
|                   /
|                  /                  B1 (slope = C_B1)
|                 /                  /
|                /                  /
|               /                  /
|              /                  /
|             /                  /                       A (slope = C_A, small)
|            /                  /                       /
|           /                  /        ____________
|          /                  /  ______/
|         /                  /__/
|        /              ____/  <- break-even ≈ N=10–15
|       /         ____/
|      /     ____/
|     /__/__/
|    /__/                          A starts high (upfront extraction cost)
|   /  /                           but the slope crushes B1 over time
|__/__/______________________________________________________________________
   0                                                                         N
```

The plot is rendered in the CLI (`cli compare --plot` → ASCII chart) and as a real chart in the Next.js dashboard at Phase 5.

## Why this matters for the demo

Three rhetorical wins:

1. **It honestly accounts for the upfront cost.** Critics who say "of course atom-RAG wins, you did all the work in extraction" are answered: yes, that work is on the chart, included in the curve.
2. **It surfaces the durability of atoms.** Each atom asks one question once and answers many later. The slope difference is the slope of *reuse*.
3. **It dictates when to invest in extraction.** For a paper you'll query once, B1 wins. For a paper you'll return to repeatedly, A wins. The break-even number is a usable decision rule for the scholar.

## What the gold set needs

To plot the curve credibly, the gold set in `data/gold/questions.yaml` needs **≥10 questions per paper**. The first few questions establish the per-question metrics; the rest let the curves cross visibly.

`scripts/eval_report.py` consumes the gold set, runs all three pipelines, accumulates costs, and prints both the per-question table and the cumulative curve.

## What the demo does *not* claim

- It does not claim A wins on a single question. Sometimes B1 wins on a single question with simple semantics.
- It does not claim curation is free. Scholar time is real and counted in the curve.
- It does not claim break-even is universal. The exact N depends on paper length, extraction quality, question difficulty.

What it *does* claim: across realistic research workloads (papers you actually care about, questions you actually keep asking), tier A dominates. The curve is the proof.
