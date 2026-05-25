# openacad — Design Notes

All-in-one scholarly research platform. Discovery → consumption → annotation → synthesis.

## Data sources (Google Scholar has no official API)

Skip Google Scholar scraping. Use these instead:

- **Semantic Scholar API** — free, citation graph, abstracts, author details
- **OpenAlex** — fully open catalog, papers / authors / institutions / concepts
- **Crossref REST API** — DOI metadata, peer reviews, components, funding
- **CORE API** — largest open-access full-text collection
- **arXiv / bioRxiv** — preprints with versioning

Commercial fallbacks for Scholar-specific data: SerpApi, DataForSEO, ZenSerp, `scholarly` (Python, rate-limited).

## Exhaustive `PublicationType` enum

Benchmarked against FaBiO ontology, OpenAlex/MAG, and Crossref DOI types.

```ts
type PublicationType =
  // Core textual
  | "journal-article"
  | "proceedings-article"   // conference papers
  | "preprint"
  | "book"
  | "book-chapter"
  | "dissertation"          // theses
  | "report"                // technical/government

  // Non-textual primary artifacts
  | "dataset"
  | "software"

  // Editorial / review (Open Science)
  | "peer-review"
  | "editorial"
  | "retraction-notice"

  // Supplementary
  | "component"             // figures, tables, supplementary PDFs with their own DOI
  | "other";
```

## Polymorphic `Publication` document — exhaustive JSON shape

```jsonc
{
  // 1. System & identifiers
  "_id": "pub_01H8X...",
  "type": "journal-article",
  "external_ids": {
    "doi": "10.1038/s41586-023-0...",
    "openalex": "W4298216350",
    "arxiv": "2303.12712",
    "semantic_scholar": "649def...",
    "pmid": "36814234"
  },

  // 2. Core content (LaTeX-aware)
  "title":    { "value": "...", "markup_language": "latex" },
  "abstract": { "value": "...", "markup_language": "latex" },
  "language": "en",

  // 3. Timeline (papers are living documents)
  "publication_date": "2023-04-15",
  "publication_year": 2023,
  "is_retracted": false,
  "versions": [
    { "version": 1, "date": "2023-03-01", "type": "preprint", "source": "arXiv" }
  ],

  // 4. Authors & affiliations (order matters in academia)
  "authors": [
    {
      "author_id": "auth_992...",
      "name": "Jane Doe",
      "raw_affiliation_string": "Department of Mathematics, Stanford...",
      "affiliations": [
        {
          "institution_id": "inst_11",
          "name": "Stanford University",
          "ror_id": "https://ror.org/00f54p054",
          "country_code": "US"
        }
      ],
      "identifiers": { "orcid": "0000-0002-1825-0097" },
      "sequence": "first",          // "first" | "middle" | "last"
      "is_corresponding": true
    }
  ],

  // 5. Venue / source
  "venue": {
    "venue_id": "ven_44...",
    "name": "Journal of Mathematical Physics",
    "publisher": "AIP Publishing",
    "issn": "0022-2488",
    "is_open_access": false
  },
  "volume": "64",
  "issue": "4",
  "pages": "042301",

  // 6. Taxonomy & classification
  "concepts":            [{ "name": "Differential Geometry", "level": 1, "score": 0.85 }],
  "keywords":            ["manifold", "tensor calculus", "Ricci flow"],
  "ams_classifications": ["53C44", "58J05"],

  // 7. Access & full text
  "open_access": {
    "is_oa": true,
    "oa_status": "green",           // "gold" | "green" | "bronze" | "hybrid" | "closed"
    "url": "https://arxiv.org/pdf/2303.12712.pdf"
  },
  "licenses": [{ "type": "CC-BY-4.0", "url": "https://creativecommons.org/licenses/by/4.0/" }],

  // 8. Citations & graph metrics
  "metrics": {
    "citation_count": 142,
    "reference_count": 45,
    "influential_citation_count": 12
  },
  "references": ["pub_01H8Y...", "pub_01H8Z..."],

  // 9. Linked artifacts (modern research output)
  "artifacts": [
    { "type": "software", "name": "...", "url": "https://github.com/...", "is_peer_reviewed": false },
    { "type": "dataset",  "url": "https://zenodo.org/record/123456" }
  ],

  // 10. System metadata
  "embeddings": { "model": "text-embedding-3-small", "vector": [/* 1536 floats */] },
  "created_at": "2026-05-15T10:00:00Z",
  "updated_at": "2026-05-22T07:16:21Z"
}
```

### Critical design choices

- **`markup_language` flags** on title/abstract — frontend knows when to initialize KaTeX/MathJax.
- **ORCID + ROR** for global disambiguation. Names alone ("J. Smith") are unreliable.
- **`oa_status`** — controls whether you can legally host the PDF (gold/green = yes, closed = link only).
- **`external_ids` as an object** (not array) — O(1) lookups when deduplicating during ingestion.

## Open issues to resolve before implementation

1. **References as internal IDs is a chicken-and-egg trap.** On ingestion you only have DOIs/OpenAlex IDs, not your `pub_*` IDs. Store both — raw external ID + resolved internal ID once known — so you don't block on resolution or lose references to un-ingested papers.
2. **Don't embed the vector in the main doc.** A `text-embedding-3-small` vector is ~6 KB; it'll be pulled on every list query. Put it in a sibling `publication_embeddings` collection (or use Atlas Vector Search's separate index).
3. **Three overlapping taxonomies** — `concepts`, `keywords`, `ams_classifications`. Keep all from upstream but pick one canonical for search/filter; treat the others as enrichment.
4. **Missing: funding / grants.** Crossref exposes funder data (NIH grant IDs, ERC IDs) — researchers care for citation/funding analysis. Add `funding[]`.
5. **Missing: retraction details.** `is_retracted: false` is too thin. Retractions need a reason, date, and link to the retraction notice (itself a `retraction-notice`-typed publication).

## Other entities (sketch)

- **`Author`** — id, name, aliases[], affiliations[], hIndex, totalCitations, orcid.
- **`Venue`** — id, name, publisher, ISSN, type (journal/conference/preprint server), open-access status.
- **`Institution`** — id, name, ror_id, country, parent (for departments).
- **`Collection`** (user workspace) — id, userId, name, description, items[{publicationId, addedAt, userTags[]}].
- **`Annotation`** (the hard one) — userId, publicationId, type (highlight/comment/math_note), target{pageNumber, boundingBoxes[][4], exactText, prefix, suffix}, content (LaTeX), timestamps.
- **`User`** — id, name, email, savedPapers, preferences.

## Architectural challenges flagged for later

- **Math rendering** — store raw LaTeX everywhere; never strip `$`/`$$` on ingest; render with KaTeX or MathJax.
- **PDF highlight anchoring** — store bounding boxes (page + `[x, y, w, h]`) so a highlight survives layout / dashboard rendering. Use pdf.js or a wrapper.
- **Citation graph at scale** — store outgoing `references[]` in-doc; compute incoming `cited_by` by reverse query, not by mutating the cited doc. Keep a cached `citation_count` for sort/order.
- **Semantic synthesis** — embed at both publication and annotation level so "summarize all derivations in this collection" works in an LLM context window.

## Next decisions (pending)

- Scaffold the project (Next.js App Router + MongoDB Atlas? Postgres + pgvector? Convex?) with these schemas as TS types + Zod validators.
- Deep dive #1: PDF parsing & highlight anchoring.
- Deep dive #2: AI synthesis + vector search pipeline.
- Deep dive #3: LaTeX rendering strategy.
