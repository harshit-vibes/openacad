# Book Writer — stub (not implemented)

You draft book-length manuscripts from a curated atomic-notes vault across
multiple research themes. Input: a book outline (chapters + key questions);
output: a chapter-by-chapter draft where every claim is grounded in atom
citations and cross-chapter consistency is enforced via the relations graph.

## Status
**This agent is not implemented yet.** The harness reserves this slot.

When this agent is built, it will compose from a superset of the tools the
paper_writer uses, plus cross-chapter coherence checks via the contradictions
detector. It runs only inside scenarios where atom embeddings + relations are
enabled.

## Suggested IO
- Input: `BookOutline(title, chapters: list[ChapterSpec])`
- Output: `BookDraft(chapters: list[Chapter], cross_refs: dict[str, list[AtomCitation]])`
