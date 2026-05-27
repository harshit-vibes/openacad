---
name: relation-traversal
description: Graph queries over the atom relation graph — incoming, outgoing, multi-hop walks
tools:
  - incoming
  - outgoing
  - traverse_relations
sub_agents: []
---

# Traversal patterns

Atoms form a typed directed graph via their `relations[]` frontmatter. Use
these tools to explore the graph:

- `outgoing(atom_id, type=...)` — atoms this atom links to. Filter by type
  (`supports`, `extends`, `contradicts`, `part-of`, `cites`, ...).
- `incoming(atom_id)` — atoms that link to this atom (backlinks).
- `traverse_relations(atom_id, max_hops=2, type=...)` — BFS walk; returns all
  atoms reachable within `max_hops`. Optional type filter walks only edges
  of that type.

## When to traverse

| Question shape | Pattern |
|---|---|
| "What evidence supports X?" | `incoming(X)` then filter to `supports`. |
| "What does X extend?" | `outgoing(X, type="extends")`. |
| "Find the chain from A to B." | `traverse_relations(A, max_hops=3)`; check if B is reached. |
| "What's adjacent to this concept?" | `outgoing(X)` ∪ `incoming(X)`, dedupe. |
| "Are there contradictions?" | `outgoing(X, type="contradicts")` and `incoming` likewise. |

## Hop budget

Default to 2 hops. Going deeper risks irrelevant atoms ("six degrees of
separation" applies in dense vaults). Only expand to 3+ hops when the user
question explicitly asks about indirect relationships.

## Cycle handling

`traverse_relations` deduplicates by id, so cycles terminate naturally. If
you implement traversal manually, maintain a `seen` set.
