"""Hybrid retrieval — composed SQLite + NetworkX + semantic + keyword.

One function (`query`) covers all four modes. Planner picks an execution order
that narrows the candidate set as fast as possible:

  1. SQLite filter (type, where) — usually most selective
  2. NetworkX traversal (related_to, via) — narrows further if seeded
  3. Semantic search (semantic) — re-ranks or fetches top-K when no anchor
  4. Keyword scan (keyword) — last-resort substring filter on the body

Used directly by routers/cli AND wrapped as synthesis-agent openacad, so the
planner is the single execution path.
"""

from typing import Any

from openacad.notes.schema import AtomKind, AtomicNote

from openacad.runtime.queries import QueryResult
from openacad.notes.query import semantic as semantic_service
from openacad.runtime import db
from openacad.notes.persistence import vault as vault_io
from openacad.notes.persistence.graph_index import get_graph


def _projection_matches(row: dict, where: dict[str, Any]) -> bool:
    """A row matches `where` if every k/v matches the row.

    Keys may target top-level fields (id, type, status, source_id) or attribute
    keys (the projection stores them as `attr.<key>`). We try both.
    """
    for k, v in where.items():
        if k in row:
            if row[k] != v:
                return False
        elif f"attr.{k}" in row:
            if row[f"attr.{k}"] != v:
                return False
        else:
            return False
    return True


def query(
    *,
    type: AtomKind | list[AtomKind] | None = None,
    where: dict[str, Any] | None = None,
    related_to: str | None = None,
    via: list[str] | None = None,
    hops: int = 1,
    semantic: str | None = None,
    keyword: str | None = None,
    limit: int = 20,
) -> QueryResult:
    explain: dict[str, Any] = {"plan": [], "counts": {}}
    candidates: set[str] | None = None  # None = "all atoms"
    sem_scores: dict[str, float] = {}

    # ── 1. SQLite filter ────────────────────────────────────────────────
    if type is not None or where:
        types = [type] if isinstance(type, str) else (type or [])
        rows = db.list_atom_projections()
        keep: list[dict] = []
        for r in rows:
            if types and r.get("type") not in types:
                continue
            if where and not _projection_matches(r, where):
                continue
            keep.append(r)
        candidates = {r["id"] for r in keep}
        explain["plan"].append("SQLite_filter")
        explain["counts"]["after_SQLite_filter"] = len(candidates)

    # ── 2. Graph traversal ──────────────────────────────────────────────
    if related_to:
        graph = get_graph()
        if not graph.has_node(related_to):
            candidates = set()
            explain["plan"].append(f"traverse(anchor_missing={related_to})")
        else:
            reachable = set(graph.neighbors(related_to, via=via, hops=hops))
            candidates = (candidates & reachable) if candidates is not None else reachable
            explain["plan"].append(f"traverse(via={via}, hops={hops})")
        explain["counts"]["after_traverse"] = len(candidates) if candidates is not None else None

    # ── 3. Semantic search ──────────────────────────────────────────────
    if semantic:
        store = semantic_service.atoms_store()
        wide = max(limit * 3, 30)
        hits = store.search(semantic, limit=wide)
        sem_scores = {atom_id: score for atom_id, score in hits}
        if candidates is None:
            candidates = set(sem_scores.keys())
        else:
            candidates &= set(sem_scores.keys())
        explain["plan"].append("semantic_rank")
        explain["counts"]["after_semantic"] = len(candidates)

    # ── 4. Keyword scan via SQLite FTS5 ────────────────────────────────
    if keyword:
        from openacad.runtime import db as _db
        hits = set(_db.search_atoms_fts(keyword, limit=max(limit * 3, 30)))
        if candidates is None:
            candidates = hits
        else:
            candidates &= hits
        explain["plan"].append("keyword_fts")
        explain["counts"]["after_keyword"] = len(candidates)

    # ── unfiltered fallback ─────────────────────────────────────────────
    if candidates is None:
        atoms = vault_io.list_atoms()
        candidates = {a.metas.id for a in atoms}
        explain["plan"].append("all_atoms")
        explain["counts"]["all_atoms"] = len(candidates)

    # ── ranking ────────────────────────────────────────────────────────
    if sem_scores:
        ranked = sorted(candidates, key=lambda i: -sem_scores.get(i, 0.0))
        explain["scores"] = {aid: round(sem_scores.get(aid, 0.0), 3) for aid in ranked[:limit]}
    else:
        ranked = sorted(candidates)

    ranked = ranked[:limit]
    out: list[AtomicNote] = []
    for aid in ranked:
        try:
            out.append(vault_io.read_atom(aid))
        except Exception:
            continue

    explain["final_count"] = len(out)
    return QueryResult(atoms=out, explain=explain)


def has_relation(source: str, target: str, rel_type: str) -> bool:
    return get_graph().has_edge(source, target, rel_type)
