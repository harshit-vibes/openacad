# Paper Writer — stub (not implemented)

You draft long-form research papers from a curated atomic-notes vault. Input:
a research question + scope; output: a structured paper draft (abstract,
introduction, related work, sections, conclusion, references) where every
claim is grounded in an atom citation and every citation traces to a source PDF.

## Status
**This agent is not implemented yet.** The harness reserves this slot.

When this agent is built, it will compose from the tools listed in `tools.toml`
(retrieval + atoms read + registry queries) and run inside any scenario whose
flags satisfy its requirements (atoms-attrs-rels and above for full graph
traversal, drafted-notes and above for semantic similarity over atoms).

## Suggested IO
- Input: `PaperBrief(question: str, scope: list[Tag], sections: list[str])`
- Output: `PaperDraft(sections: list[Section], references: list[AtomCitation])`
