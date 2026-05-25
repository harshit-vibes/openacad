# book_writer agent — slot (not yet implemented)

Reserves a slot in the harness for a future agent that drafts book-length
manuscripts from the curated atomic-notes vault. No `agent.py` yet.

## When to build this
After paper_writer is shipped and stable. Books add cross-chapter coherence
constraints that paper_writer doesn't need.

## What's already here
- `prompt.md` — the role description
- `tools.toml` — declarative allow-list (paper_writer's tools + contradictions
  + cross_paper)

See `agents/paper_writer/README.md` for the to-enable checklist.
