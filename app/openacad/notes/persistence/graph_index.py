"""NetworkX MultiDiGraph rebuilt from vault frontmatter at boot.

Edges carry relation type as the `type` attribute (and become networkx edge keys).
Inverse edges are materialized from registry RelationDef.inverse so reverse
traversal works without storing them in atom files.
"""

from threading import Lock

import networkx as nx

from openacad.notes.schema import AtomKind, AtomicNote
from openacad.notes.persistence import vault as vault_io
from openacad.notes.registry.validation import get_schema


class GraphService:
    def __init__(self) -> None:
        self._g: nx.MultiDiGraph = nx.MultiDiGraph()
        self._lock = Lock()
        self.rebuild()

    def rebuild(self) -> None:
        with self._lock:
            g = nx.MultiDiGraph()
            atoms = vault_io.list_atoms()
            for a in atoms:
                g.add_node(a.metas.id, type=a.metas.type, tags=a.metas.tags, source_id=a.origin.source_id)
            schema = get_schema()
            for a in atoms:
                for r in a.relations:
                    g.add_edge(a.metas.id, r.target, key=r.type, type=r.type)
                    rd = schema.get_relation(r.type)
                    if rd and rd.inverse:
                        # For symmetric relations (inverse == type), still add the reverse
                        # edge so traversal works from either side.
                        g.add_edge(r.target, a.metas.id, key=rd.inverse, type=rd.inverse)
            self._g = g

    # ── single-atom updates ─────────────────────────────────────────────

    def upsert(self, atom: AtomicNote) -> None:
        """Incremental update for one atom (called by curate.accept/edit)."""
        with self._lock:
            g = self._g
            # remove existing edges where this atom is the source (inverses cleaned via rebuild on remove)
            to_remove = [(u, v, k) for u, v, k in g.out_edges(atom.metas.id, keys=True)]
            for u, v, k in to_remove:
                g.remove_edge(u, v, key=k)
            # also drop any inbound inverse edges that this atom would re-add (avoid dupes)
            g.add_node(atom.metas.id, type=atom.metas.type, tags=atom.metas.tags, source_id=atom.origin.source_id)
            schema = get_schema()
            for r in atom.relations:
                g.add_edge(atom.metas.id, r.target, key=r.type, type=r.type)
                rd = schema.get_relation(r.type)
                if rd and rd.inverse and rd.inverse != r.type:
                    g.add_edge(r.target, atom.metas.id, key=rd.inverse, type=rd.inverse)

    def remove(self, atom_id: str) -> None:
        with self._lock:
            if atom_id in self._g:
                self._g.remove_node(atom_id)

    # ── queries ─────────────────────────────────────────────────────────

    def has_node(self, atom_id: str) -> bool:
        return atom_id in self._g

    def nodes_by_type(self, atom_type: AtomKind) -> list[str]:
        return [n for n, d in self._g.nodes(data=True) if d.get("type") == atom_type]

    def has_edge(self, source: str, target: str, rel_type: str) -> bool:
        if not self._g.has_edge(source, target):
            return False
        return any(
            d.get("type") == rel_type
            for _u, v, d in self._g.out_edges(source, data=True)
            if v == target
        )

    def neighbors(
        self,
        atom_id: str,
        via: list[str] | None = None,
        hops: int = 1,
    ) -> list[str]:
        """BFS from atom_id following only edges whose `type` is in `via`. `hops` bounds depth."""
        if atom_id not in self._g:
            return []
        via_set = set(via) if via else None
        seen = {atom_id}
        frontier = {atom_id}
        for _ in range(hops):
            nxt: set[str] = set()
            for n in frontier:
                for _u, v, d in self._g.out_edges(n, data=True):
                    if via_set and d.get("type") not in via_set:
                        continue
                    if v not in seen:
                        nxt.add(v)
                        seen.add(v)
            frontier = nxt
            if not frontier:
                break
        seen.discard(atom_id)
        return sorted(seen)

    def contradicting_pairs(self, include_weak: bool = False) -> list[tuple[str, str]]:
        """Pairs linked by `contradicts`. Weak conflicts (same attrs, opposite values) is Phase 4."""
        pairs: set[tuple[str, str]] = set()
        for u, v, d in self._g.edges(data=True):
            if d.get("type") == "contradicts":
                pairs.add(tuple(sorted([u, v])))  # type: ignore[arg-type]
        return sorted(pairs)


_graph: GraphService | None = None
_graph_lock = Lock()


def get_graph() -> GraphService:
    global _graph
    if _graph is None:
        with _graph_lock:
            if _graph is None:
                _graph = GraphService()
    return _graph


def rebuild_graph() -> None:
    get_graph().rebuild()
