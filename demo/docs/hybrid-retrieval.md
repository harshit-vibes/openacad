# Hybrid Retrieval — SQLite + NetworkX + Semantic

## The single composed `query()`

`api/services/retrieval.py` exposes one function that composes structured filters, graph traversal, semantic search, and keyword scan.

```python
class QueryResult(BaseModel):
    atoms: list[AtomicNote]
    explain: dict           # which filters fired, traversals run, scores per atom

def query(
    *,
    type: AtomKind | list[AtomKind] | None = None,
    where: dict[str, Any] | None = None,    # attribute equality / range (SQLite)
    related_to: str | None = None,           # anchor atom id (NetworkX)
    via: list[str] | None = None,            # relation types to traverse
    hops: int = 1,                           # graph distance
    semantic: str | None = None,             # cosine query (in-memory MiniLM)
    keyword: str | None = None,              # body substring scan
    limit: int = 20,
) -> QueryResult: ...
```

Every parameter is optional. The function composes whatever is provided.

## The four retrieval modes

### 1. SQL-style (SQLite)

```python
query(type="claim", where={"domain.sub": "nlp", "evidence.confidence": "high"})
```

The `atoms_index` SQLite table holds a flat projection of every committed atom: `{id, type, status, **flat_attributes}`. The dotted-namespace attribute keys (`evidence.confidence`) become flat field names in SQLite, which supports them natively in `where` queries.

Performance: indexed on `type` / `status` / `source_id`; attribute filters scan the JSON-encoded `attributes_json` column post-fetch (good for ≤10K atoms; can be moved to JSON1 path expressions if it gets slow).

### 2. Graph-style (NetworkX)

```python
query(related_to="atom-x", via=["extends", "supported-by"], hops=2)
```

The NetworkX `MultiDiGraph` is rebuilt at boot from `vault/notes/*.md` frontmatter. Edges carry the relation `type`. Inverse edges are synthesized from the registry's `inverse` field (so `a --extends--> b` is also queryable as `b --extended-by--> a` without storing both).

Performance: BFS is O(V+E) per traversal. Fine at any vault size we care about.

### 3. Semantic (in-memory cosine)

```python
query(semantic="attention is quadratic in sequence length")
```

Atom embeddings live in `data/embeddings/atoms.npz` (two numpy arrays: `ids` of dtype `<U64` and `vectors` of dtype `float32` shape `[N, 384]`). Loaded into memory at boot. Cosine is a single matrix-vector multiply.

Performance: O(N × 384) per query, trivially fast at vault sizes ≤100K.

### 4. Keyword (SQLite FTS5)

```python
query(keyword="quadratic attention")
```

A SQLite FTS5 virtual table indexes every atom's body. Returns matches ranked by relevance (BM25-style). Handles exact tokens, partial words, and natural-language keyword queries; sub-millisecond at our scale.

## The planner

When multiple modes are combined, the planner picks the order:

1. **Most selective first.** Registry `usage_count` provides a cardinality estimate. A `where` filter on a low-usage attribute is more selective than a vector search; do it first.
2. **Graph traversals start from the narrowest set.** If `where` + `via` are both present, run `where` first to narrow the candidate set, then traverse from those nodes.
3. **Semantic is a re-ranker by default.** When combined with structured filters, vectors rank the already-filtered candidates rather than searching the whole vault.
4. **Keyword is the last resort.** Only invoked if explicitly requested or all other filters return empty.

The planner's decisions are recorded in `QueryResult.explain` so the scholar can see what fired:

```json
{
  "plan": ["SQLite_where (selectivity=0.04)", "networkx_traverse (hops=1)", "semantic_rerank"],
  "candidates_after_step": [37, 12, 12],
  "scores": {"atom-a": 0.91, "atom-b": 0.87, ...}
}
```

## Used directly and by agent tools

`query()` is the implementation behind the synthesis agent's `query_atoms`, `traverse`, and `semantic_search` tools. The CLI and routers also call it directly.

This means the **planner is a single source of truth**. When the agent picks "query atoms by type=claim then traverse contradicts," the actual execution is the same code path as a CLI `cli ask --type claim --via contradicts`. No duplication, no drift.

## The flagship query (the demo's killer)

> "Find claims in NLP that contradict empirical findings."

```python
result = query(
    type="claim",
    where={"domain.sub": "nlp"},
    via=["contradicts"],
    hops=1,
)
```

Planner trace:

```
1. SQLite where type=claim ∧ domain.sub=nlp → 23 candidates
2. NetworkX traverse contradicts → 8 target atoms reached
3. SQLite where target.type=finding ∧ target.evidence.type=empirical → 5 final atoms
```

Five precisely-typed atoms returned, each citable. **No RAG approach can express this query.** That's the demo.
