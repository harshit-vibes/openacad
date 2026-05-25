# Scholar Research Lifecycle — Activities, Features, Pain Points & Competitive Map

A combined map of:

1. **What a scholar actually does** at each phase of their research lifecycle
2. **What features** an all-in-one research assistant should offer at that phase
3. **What hurts today** — concrete pain points in the current stack
4. **Who plays here today** — the specific SaaS competitors active in this phase
5. **The opening for openacad** — where the gap is real and addressable

The lifecycle is **not strictly linear** — researchers loop back constantly. A new paper found in week 6 sends them back to discovery; analysis results force a rewrite of methodology; peer review pushes them back into synthesis. Build the platform as a graph of connected workspaces, not a wizard.

---

## The two lenses

This document holds both:

**Lens A — The scholar's lifecycle (12 phases + 5 cross-cutting concerns).** What a single researcher experiences, week to week.

**Lens B — The SaaS market segmentation (5 commercial stages).** How the industry has carved up the problem. Useful for competitive positioning.

| SaaS stage | Lifecycle phases it covers | Representative tools |
|---|---|---|
| **1. Find** (discovery & literature mapping) | Phase 0 (Ideation, partial) · Phase 1 (Discovery) | ResearchRabbit, Litmaps, Connected Papers, Inciteful, Semantic Scholar, Google Scholar, SciSpace, Elicit |
| **2. Filter** (screening & systematic review) | Phase 2 (Screening) | Covidence, Rayyan, Scholarcy, SciSpace Deep Review / PRISMA Agent |
| **3. Execute** (data & lab management) | Phase 6 (Research execution) | Benchling, SciNote, Zenodo, Figshare, OSF, GitHub, Jupyter |
| **4. Sense-make** (deep synthesis & extraction) | Phase 3 (Reading) · Phase 4 (Annotation) · Phase 5 (Synthesis) | Elicit, Consensus, SciSpace (Chat with PDF, Extract Data), SciSpace Chrome Extension, MarginNote, LiquidText, Hypothes.is |
| **5. Publish** (writing, editing, typesetting) | Phase 7 (Writing) · Phase 8 (Citations) · partial Phase 9 (Revision) | Overleaf, Typst, Authorea, Paperpal, Writefull, SciSpace AI Writer, Zotero, Mendeley, EndNote |
| *(no commercial stage)* | Phase 9 (Internal review) · Phase 10 (Submission & peer review) · Phase 11 (Dissemination & impact) | Editorial Manager / ScholarOne (journal-owned); Kudos, Altmetric, Plum, ResearchGate (impact); SciSpace Citation Booster |

**Where the market is fragmented:** every tool above is vertical-specialist. The horizontal play — one workspace spanning all five stages with provenance preserved end-to-end — is the open gap, and openacad's target.

---

## Phase 0 — Ideation & Question Formation

The phase before "real" research starts. Often invisible in existing tools.

### Activities
- Browse new arXiv submissions; follow specific authors / labs / Twitter accounts
- Notice a contradiction between two papers
- Hear a talk and wonder what's *unsolved* in the field
- Discuss with advisor / lab to refine a vague intuition into a researchable question
- Look for a research gap — what hasn't been done yet
- Check if anyone is already doing it (avoid duplicate work)
- Estimate feasibility — equipment, data access, time horizon
- Pre-register the hypothesis (in some fields)

### Features an all-in-one tool would offer
- **Daily feed** of new papers / preprints filtered by topic + your reading history
- **Author + lab tracking** with notifications on new releases
- **Gap-finder** — visualise where citation density is low between two concept clusters
- **"Has this been done?" search** — semantic dedup against existing literature + ongoing-research registries (OSF, ClinicalTrials, registered reports)
- **Question refinement workspace** — scratchpad linking to seed papers, with AI prompts that help operationalise a vague question into a testable one
- **Pre-registration integration** (OSF, AsPredicted)
- **Feasibility checklist** — estimated reading load, dataset availability, compute requirements

### Pain points today
- No tool tells you "this question is already 80% answered" — you waste weeks discovering this manually
- Finding gaps is artisanal — you read 200 papers and *hope* you spot the gap
- Pre-registration friction means most scholars skip it, hurting reproducibility later
- Advisor conversations are not captured; the *why* of a research direction is lost when grad students move on

### Who plays here today
- **Litmaps** touches it via "story arc" timelines — best for understanding how a theory evolved, weak for finding pristine gaps.
- **ResearchRabbit** maintains seed-paper collections with continuous recommendations — closer to "watch this space," not "find the gap."
- **OSF / AsPredicted** handle pre-registration but are paperwork-style; not integrated with discovery.
- **SciSpace, Elicit, Consensus** do not address this phase explicitly.

### The opening for openacad
**Almost nothing exists here.** A gap-finder grounded in the citation graph (low-density regions between active clusters) plus a "has-this-been-done" check against OSF + ClinicalTrials would be a defensible wedge. Ideation is also where lock-in starts — capturing it means the workspace owns the question from day zero.

---

## Phase 1 — Literature Discovery

Finding what exists.

### Activities
- Keyword search on Google Scholar, Semantic Scholar, PubMed, Web of Science, Scopus
- Snowballing — follow citations forward (citing papers) and backward (references)
- Browse a key journal's table of contents
- Ask peers / advisor / Twitter for recommendations
- Set up alerts for new papers matching specific queries
- Check gray literature — theses, technical reports, government docs, conference posters
- Hunt for the PDF behind paywalls (institutional access, Sci-Hub, author requests)

### Features an all-in-one tool would offer
- **Federated search** across OpenAlex, Semantic Scholar, Crossref, arXiv, PubMed, CORE — one query, deduped
- **Semantic search** by concept, not just keyword (vector embeddings)
- **Citation graph navigator** — visual forward / backward traversal with influence weighting
- **Saved queries with alerts** — daily / weekly digest of new matches
- **Gray-literature inclusion** as first-class — preprints, theses, working papers, technical reports, conference proceedings
- **Multilingual discovery** — surface non-English work via translation
- **Open-access resolver** — auto-find the legal free PDF; flag paywalled
- **Predatory-journal filter** — auto-flag items from known predatory venues
- **"More like this"** seeded from any paper, with explanation of *why* it's similar

### Pain points today
- Keyword search misses concepts ("LLM" vs "large language model" vs "GPT-4" vs "transformer model")
- Filter bubbles — Google Scholar surfaces what's already popular; long-tail relevant work stays buried
- Non-English literature systematically missed
- Manual snowballing across 50 papers is hours of tab-switching
- Paywalls force constant context-switching between search → VPN → library proxy → ILL request
- No single tool spans the 5+ databases researchers actually need

### Who plays here today
- **Google Scholar** — the default. Massive coverage, but no API, no real filters, no semantic search, full of predatory and duplicate entries.
- **Semantic Scholar** (Allen Institute, free) — AI search, TL;DRs, "highly influential citations" badge. Excellent free baseline.
- **OpenAlex** — open, comprehensive (250M+ works), great API. Library/infra layer, not a researcher-facing UI.
- **ResearchRabbit** — "Spotify for papers": seed collections + continuous recommendations. Best-in-class for ongoing discovery.
- **Litmaps** — chronological visual timeline; tracks the story arc of a theory across decades.
- **Connected Papers** — instant node-graph from a single seed; great for "what are the priors and descendants?"
- **Inciteful** — shortest-citation-path between two papers from different subfields.
- **SciSpace** — federated search across 280M+ papers with semantic embeddings; positioned as the modern Google Scholar.
- **Elicit** — search + structured extraction in one; aimed at research questions, not just papers.

### The opening for openacad
The base discovery problem is well-served — beating Semantic Scholar and ResearchRabbit at raw search is a fool's errand. The opening is **integration**: making discovery the natural front door to a workspace where every found paper *stays* connected to your annotations, drafts, and synthesis. Today, you find a paper in ResearchRabbit, save its DOI, then re-import it into Zotero, then download the PDF, then highlight in a separate reader, then quote in a separate writer. Owning the whole chain is the wedge.

---

## Phase 2 — Screening & Triage

Reducing 2,000 hits to the 50 worth deep-reading.

### Activities
- Skim title → abstract → conclusion → figures (in that order)
- Apply inclusion / exclusion criteria for a systematic review (PRISMA)
- Decide: read now / read later / reject / unsure → ask advisor
- For systematic reviews: dual-reviewer blind screening with conflict resolution
- Tag papers by relevance, theme, methodology, quality
- Maintain a "to read" pile that never shrinks

### Features an all-in-one tool would offer
- **Triage UI** — title + abstract + key figures in a swipeable card stack; one-key decisions
- **PRISMA-compliant systematic-review workflow** — blinded dual review, conflict adjudication, audit trail, exportable flow diagram
- **Inclusion / exclusion criteria editor** — codify rules, apply as filters; AI suggests decisions but human confirms
- **Auto-extracted decision aids** — sample size, study type, country, year, methodology pulled from abstract for fast eyeballing
- **Reading queue with smart prioritisation** — older items don't get lost; AI surfaces highest-value-per-minute next read
- **Tags + folders + smart collections** (saved-query-as-folder)
- **Quality / risk-of-bias scoring** — Cochrane RoB, JBI checklists, PRISMA 2020

### Pain points today
- Abstracts are clickbait — relevance often unclear until you read the methods
- Triage tools are excellent but **disconnected** from the rest of the workflow
- "To read" piles grow to thousands of items; no good way to declare bankruptcy
- Systematic-review tooling is clinical-medicine-centric and paywalled; CS, social science, humanities have no equivalent

### Who plays here today
- **Covidence** — gold standard for medical/Cochrane systematic reviews. Blind screening, dual reviewer, conflict resolution, PRISMA-compliant audit trail. Expensive, clinical-only-feeling.
- **Rayyan** — freemium alternative. Faster onboarding, popular with grad students for collaborative screening. Weaker audit trail than Covidence.
- **Scholarcy** — automated PDF summarisation. Pulls methodology, sample size, limitations into flashcards. Speeds eyeballing but doesn't manage the triage workflow itself.
- **SciSpace Deep Review / PRISMA Agent** — newer AI-driven entrant. Promises "systematic reviews in minutes." Quality and audit-trail rigor unproven vs. Covidence.
- **Reference managers (Zotero, Mendeley)** are sometimes pressed into service for triage with tags — works poorly at scale.

### The opening for openacad
Covidence owns clinical. The opportunity is **non-clinical systematic reviews** (CS, ML, social science, humanities) where Covidence feels alien and Rayyan feels primitive. A field-agnostic PRISMA workflow with the audit trail rigor of Covidence + the UX of a modern app + integration to the rest of the workspace would be defensible. Bonus: bring AI-suggested decisions but make the audit trail show human/AI provenance per inclusion — required for the discipline to trust AI-assisted reviews.

---

## Phase 3 — Deep Reading & Comprehension

Actually consuming a paper.

### Activities
- Read on screen (laptop, tablet) or print-then-annotate
- Look up unfamiliar terms — jargon, acronyms, methods
- Cross-reference figures and tables to the prose
- Parse equations — work through derivations in a notebook
- Check cited references when a claim seems weak or pivotal
- Skim related work to find more papers (loop back to Phase 1)
- Re-read sections — "wait, what did Figure 3 show?"

### Features an all-in-one tool would offer
- **First-class PDF reader** — smart zoom, dark mode, two-page layout, distraction-free mode
- **Inline AI explainer** — highlight any phrase, equation, table, or figure → get explanation tuned to your level
- **Equation rendering + step-by-step derivation** (LaTeX → KaTeX/MathJax + LLM derivation walk-through)
- **Inline glossary / acronym expansion** — hover any term for definition + usage in the paper
- **Cross-reference popovers** — click "[12]" → preview ref 12 inline without losing your place
- **Figure / table zoom + transcript** — figures rendered crisply; tables as actual structured data, not images
- **Reading progress sync across devices** — start on laptop, continue on tablet
- **Reading mode for math** — toggle between paper layout and "math notebook" layout that gives equations room to breathe

### Pain points today
- PDFs are print artifacts forced onto screens — two-column layouts are awful on phones, fine on paper
- Equations in scanned PDFs are images, not text — can't copy, render, or query
- Jargon-heavy fields demand constant tab-switching to Wikipedia / SEP / nLab
- "Where did they cite this?" → flipping back and forth between sections
- Math derivations skipped in the paper assume the reader can re-derive; few can without help
- No good way to read offline while syncing state back

### Who plays here today
- **SciSpace Chat with PDF** — upload PDF, highlight, ask the AI to explain math/equations/tables/figures, get citation-backed answers. Explicitly competes with ChatPDF and PDF.ai.
- **SciSpace Chrome Extension** — same explainer overlay anywhere on the web (publisher pages, repositories, news outlets).
- **Adobe Acrobat / Apple Preview / Foxit** — generic PDF readers. Powerful but utterly non-academic.
- **Mendeley / Zotero / Papers** built-in readers — basic annotation, no AI.
- **PDF Expert, LiquidText** — premium readers with infinite-canvas note layout (LiquidText). Mostly iPad-first.
- **SciSpace Mobile App** — search, summarise, explore on phone.
- **PaperQA / similar open-source** — chat with one or many PDFs locally; technical users only.

### The opening for openacad
Reading is well-covered by SciSpace and ChatPDF. The wedge is **math + cross-paper reading**. None of the current tools:
1. Render scanned-PDF equations back into editable, queryable LaTeX
2. Let you read 3 papers side-by-side with a shared annotation context
3. Treat the bibliography as live — click a reference and the cited paper opens *inside* your workspace, not in a new browser tab
Owning the reader is also strategic because it's where annotations begin, and annotations are the lock-in (next phase).

---

## Phase 4 — Annotation & Note-Taking

Capturing what you got from the paper.

### Activities
- Highlight passages, equations, figures
- Write margin notes — "this contradicts X"; "use this method in chapter 3"; "ask advisor"
- Create flashcards / Anki cards for memorisation
- Build a structured note (Zettelkasten / Obsidian / Notion) per paper
- Quote-collect — pull verbatim passages with locations for later citation
- Sketch diagrams interpreting the paper's argument
- Voice-memo while reading on the go

### Features an all-in-one tool would offer
- **Anchored highlights** — bound to exact PDF coordinates (page + bounding boxes), survive layout / rendering changes
- **Multi-target annotation** — same note can attach to multiple papers, sections, or annotations
- **Math-aware notes** — write notes in LaTeX, render inline; equations carry semantic meaning
- **Voice-to-text annotations**
- **Spaced-repetition export** — turn highlights into Anki / Mochi cards in one click
- **Backlinks** — every annotation knows what notes reference it; bi-directional like Obsidian
- **Annotation search across your entire library** — "what did I think about transformer attention last year?"
- **Quote-mode** — capture exact text + page + paragraph → drops cleanly into a future citation
- **Public / private annotations** (Hypothes.is-style social layer for trusted groups)

### Pain points today
- Highlights live in whichever PDF reader you used — Preview, Adobe, Zotero, Mendeley, PDF Expert — and don't sync
- You can't search your own highlights across papers
- Annotations are lost on re-import or version change
- Equations in notes are pain — Notion's LaTeX is shaky, Obsidian works but needs setup, Word is hostile
- No tool combines "annotate paper" + "build personal knowledge base" — you do both, twice, in separate apps

### Who plays here today
- **Hypothes.is** — the canonical open annotation layer. Strong for the web; weak for PDFs and offline; no math support.
- **MarginNote / LiquidText** — infinite-canvas iPad-first annotation tools. Drag snippets, tables, formulas out of multiple PDFs to physically map connections. Premium quality, iPad-locked.
- **Zotero / Mendeley / Readwise** — annotation stores attached to a reference manager. Cross-paper search exists but UX is rough.
- **Obsidian / Roam / Logseq** — personal knowledge graphs. Excellent backlink/graph view, but disconnected from the underlying PDF — you copy-paste highlights manually.
- **Notion / Capacities / Reflect** — note-taking apps; not academic-aware.
- **SciSpace** — has highlight-to-explain in its Chrome extension, but **no marquee annotation product**. Annotations live in chat threads, not on the PDF.

### The opening for openacad
**This is the weakest-covered phase in the entire lifecycle.** Hypothes.is hasn't evolved much. LiquidText is locked to iPad. Obsidian doesn't know about PDFs. Reference managers store annotations but don't help you reason about them. The wedge: an annotation system that is (1) anchored at the PDF coordinate level, (2) math-aware, (3) bi-directionally linked to your personal knowledge graph, and (4) shared across reading, synthesis, and writing phases. Annotations become the universal substrate. This is also the **strongest lock-in surface** — once a researcher has 500 annotated papers in openacad, switching cost is permanent.

---

## Phase 5 — Synthesis & Knowledge Management

Going from a pile of papers to *understanding*.

### Activities
- Build a literature matrix — papers × variables (method, sample, year, finding)
- Write a literature review section
- Map who-cites-whom and how the conversation evolved
- Identify camps / schools of thought — who agrees, who disagrees, what's contested
- Find consensus and dissent on specific claims
- Track contradictions, replications, retractions
- Build a personal knowledge graph linking concepts across papers
- Synthesize across modalities — combine text claims with data from supplementary materials

### Features an all-in-one tool would offer
- **Literature matrix builder** — auto-extract columns from your selected set; editable, exportable to CSV
- **Citation evolution view** — see a claim travel through the literature; who first said it, who reinforced it, who challenged it
- **Camps / clusters detection** — group papers by argument stance, not just topic
- **Contradiction surfacer** — "Paper A says X. Paper B says ¬X. Reconcile?"
- **Retraction watch** — flag any cited paper that has been retracted; surface predatory-venue concerns
- **Personal knowledge graph** — every annotation, every concept, every author is a node; bi-directional links; query by concept
- **AI-drafted lit-review section** with full citation provenance — every sentence traceable to a source highlight
- **Consensus / dissent meter** for any claim — like Consensus.app but inside your workspace
- **Cross-paper comparison** — pick 5 papers → side-by-side comparison on user-selected dimensions

### Pain points today
- Lit matrices live in Excel / Google Sheets, manually maintained, error-prone
- No tool shows how a *claim* (not a paper) propagates through citations
- "What's the field's current consensus on X?" requires reading 50 papers — no tool synthesises
- Retraction notices are not surfaced where you cite the paper; you find out at peer review
- Personal knowledge graphs (Obsidian, Roam) are disconnected from underlying paper data
- AI lit-review generators (Elicit, SciSpace) produce decent prose but **provenance is shaky** — you can't trust without re-verifying every claim

### Who plays here today
- **Elicit** — best-in-class structured extraction. Ask for "outcomes across 50 papers" → comparative matrix. Provenance shown per-cell but extraction quality varies; non-medical use is weaker.
- **Consensus** — search restricted to peer-reviewed claims; "Consensus Meter" shows yes / no / mixed. Useful for narrow claims, blunt for nuanced fields.
- **SciSpace Extract Data** — direct competitor to Elicit. Identifies tables, stats, citations; exports CSV / Excel / RIS. Explicit head-to-head pages vs. Elicit and Consensus on their site.
- **SciSpace AI Writer (lit-review mode)** — drafts prose with inline citations from 280M+ papers. Provenance traceable but fact-checking still required.
- **Litmaps / Connected Papers** — visualisations of citation evolution; descriptive but not analytic — they don't tell you what was *claimed*, only what was *cited*.
- **Obsidian / Roam / Logseq** — personal knowledge graphs, manual upkeep, not paper-aware.
- **Notion AI / generic ChatGPT** — used informally; no citation grounding.

### The opening for openacad
The market is crowded with **extraction** but thin on **claim-level synthesis**. The opening:
1. **Claim-level provenance** — every sentence in your synthesis traceable to a specific highlighted span in a specific paper. Currently, AI-drafted lit reviews give paper-level citations (you have to manually verify the claim is actually there).
2. **Contradiction surfacing as a primary feature**, not an afterthought — "These five papers disagree on X; here's how, in their own words."
3. **Personal knowledge graph that doesn't require an Obsidian-style manual workflow** — annotations become graph nodes automatically.

---

## Phase 6 — Research Execution (Methodology · Data · Analysis)

Doing the actual study.

### Activities
- Choose methodology — quantitative, qualitative, mixed, theoretical, computational
- Calculate sample size, power, effect sizes
- Design instruments — surveys, interview guides, experimental protocols
- Get ethical approval (IRB, ethics committee)
- Collect data — experiments, observations, surveys, simulations, dataset retrieval
- Manage raw data — store securely, version, document provenance
- Analyse — statistical tests, qualitative coding, computational modelling
- Validate — robustness checks, sensitivity analyses, peer review of analysis
- Create publication-quality figures and tables

### Features an all-in-one tool would offer
- **Methodology selector** — describe your question → AI suggests methods + cites canonical references
- **Sample size + power calculator** with assumption transparency
- **Pre-registration drop-in** — methodology + hypotheses → registered protocol on OSF
- **Electronic lab notebook (ELN)** with versioning — text, code, images, files; cryptographically signed entries
- **Data management** — schema-aware storage, FAIR-compliant metadata, automatic backup, audit trail
- **Code + data versioning** integrated with Git / DVC; reproducibility by default
- **Inline statistical analysis** — Python / R / Julia notebooks alongside the manuscript; results stay in sync
- **Figure / table generator** — publication-ready plots with per-journal style presets
- **Reproducibility checklist** — Cochrane / TOP / NIH-aligned, auto-validates as you go
- **Compute provisioning** — sandboxed notebooks with GPUs for heavy work, no devops needed

### Pain points today
- ELNs (Benchling, SciNote) are wet-lab-shaped; dry-lab researchers improvise with Notion + Drive + GitHub
- Code and prose live in separate tools — figures are out-of-date as soon as you tweak analysis
- Reproducibility is a checklist *after* the work; should be built into the workflow
- "I had three versions of this dataset and I don't remember which I used for Figure 4"
- Sample-size + power-calc tools are scattered (G*Power, Stata, R packages); rarely tied to your registered protocol
- Statistical software lock-in — switching from SPSS to R is a months-long project

### Who plays here today
- **Benchling** — the SaaS giant of biotech ELN. DNA sequences, CRISPR designs, lab inventory. Wet-lab native, irrelevant outside biology.
- **SciNote** — flexible ELN, integrates with manuscript tracking. Same wet-lab orientation.
- **LabArchives, Labii, OpenBIS** — smaller ELNs, similar shape.
- **OSF (Open Science Framework)** — project-level repository: pre-reg, files, materials, collaborators. Free, open, lightly opinionated.
- **Zenodo / Figshare / Dryad** — data repositories. Upload raw datasets/code; mint a citable DOI. Not workflow tools.
- **GitHub / GitLab + DVC** — code + data versioning; ad-hoc for academia.
- **Jupyter / Quarto / Observable** — computational notebooks; central to many CS / data-science workflows.
- **G*Power, Stata, SPSS, R, Python, Julia** — statistical software, all standalone.
- **SciSpace Biomedical Agent** — vertical play: 100+ biomedical packages, 150+ specialised tools, dozens of curated databases. Targets drug discovery, clinical genomics, single-cell / multi-omics. **Aggressively claims this phase for biomedical specifically.**

### The opening for openacad
**Skip this phase for v1.** It's heavily territorial: Benchling owns wet-lab; OSF + GitHub + Jupyter own dry-lab; SciSpace is making a biomedical play. Building an ELN is years of work in a fragmented market. Openacad's value comes from connecting Phase 6 *outputs* (datasets, figures, code) into the rest of the workspace — not from replacing Benchling.

The one cross-cutting opportunity: **bring methodology design and pre-registration upstream into Phase 0–1 workflows**, so reproducibility starts before data collection rather than as a submission-time afterthought.

---

## Phase 7 — Writing & Drafting

Producing the manuscript.

### Activities
- Outline the paper (some skip; some scaffold meticulously)
- Draft section by section — often introduction last
- Pull notes, quotes, and figures from across the knowledge base
- Cite as you go — or leave [CITE?] placeholders and fill later
- Re-write under advisor / coauthor feedback
- Handle equations, tables, figures with consistent formatting
- Track word count limits per section / per journal
- Convert between formats (Word ↔ LaTeX ↔ Markdown) painfully

### Features an all-in-one tool would offer
- **Outline-aware editor** — collapsible sections, drag-to-reorganise, word-count-per-section
- **Cite-as-you-write** — type "@" → search your library + global index → insert formatted citation + bib entry
- **AI suggestions grounded in your own annotations** — "you highlighted this 3 months ago, want to use it here?"
- **LaTeX-first or Markdown-with-math** — render math live, hide source unless wanted
- **Track-changes that don't break the document** — co-authors edit safely; structured commenting
- **Multi-format export** — Word, LaTeX, Markdown, PDF, journal-specific templates; lossless round-trip
- **Tone / clarity / journal-fit feedback** — academic AI feedback, inline
- **Figure / table version sync** — figures embedded as references to your analysis; update analysis → update figure everywhere
- **Section health** — flag sections without citations, without references to your own data, without thesis sentences
- **Collaborative real-time editing** with proper offline support
- **Pre-flight check** — required sections, citations within journal limits, formatting compliant

### Pain points today
- LaTeX (Overleaf) is great for math but painful for collaboration with non-LaTeX coauthors
- Word handles collaboration but mangles math, tables, references
- Switching between writing tool and reference manager breaks flow
- "Where did I read that quote?" — minutes lost finding the source
- Track changes in Word collapses into chaos with >3 reviewers
- Journal-specific templates are absurdly diverse; reformatting takes days per resubmission

### Who plays here today
- **Overleaf** — dominant collaborative LaTeX editor. Compiles heavy math in the browser. Killer feature: thousands of journal templates pre-loaded. Weak collaboration UX (line-based, not Word-comments-style).
- **Typst** — fast-growing modern LaTeX alternative. Instant compile, readable syntax. Strong CS uptake; not yet broadly adopted in life-sciences / humanities.
- **Authorea** — WYSIWYG editor with hundreds of journal templates and built-in figures / data integration. Niche traction.
- **Paperpal** — AI writing assistant trained on academic manuscripts. Tone, journal standards, phrasing.
- **Writefull** — similar to Paperpal; language feedback for scientific publishing.
- **SciSpace AI Writer** — drafts with inline citations from 280M+ papers. ~$20/mo unlimited; explicit comparisons to Jenni ($12) and Paperpal ($25).
- **Word + Mendeley/Zotero plugins** — the actual majority workflow despite being inferior.
- **Manuscripts.app, Curvenote** — newer markdown-first attempts.
- **Notion / Google Docs** — used informally; not academic-aware.

### The opening for openacad
Overleaf owns LaTeX. SciSpace owns AI-drafted-with-citations. The opening: **writing rooted in your own annotations**. None of the current writers know what you highlighted, what you noted, or what you've extracted into your knowledge graph. They draft from prompts or web search. Openacad's wedge: write with full access to your *own* synthesis, so suggestions are "use this annotation from Smith 2023" — citation-backed *and* personally grounded.

Secondary opening: **lossless round-trip Markdown ↔ LaTeX ↔ Word.** A real solution would let mathematicians and humanists co-author without religious wars over format.

---

## Phase 8 — Citation & Bibliography Management

The reference list and citation styles.

### Activities
- Add references to library — DOI, arXiv ID, manual entry, browser plugin
- Clean up imported metadata (incomplete BibTeX is rampant)
- Insert citations in the manuscript
- Change citation style on resubmission (APA → Vancouver → IEEE → Chicago)
- Generate bibliography in the chosen style
- Verify citations — does the paper actually say what I claim it says?
- Handle special cases — datasets, software, preprints, personal communications

### Features an all-in-one tool would offer
- **One-click import** from DOI / arXiv / PubMed / URL / PDF / drag-and-drop
- **Auto-fix incomplete metadata** — query Crossref / OpenAlex to fill missing fields
- **2,300+ citation styles** (CSL) with one-click switching
- **Citation-verification pass** — AI checks whether your claim matches the cited paper; flags weak / unsupported claims
- **Quotation provenance** — every quote linked back to the highlighted PDF location
- **Smart bibliography** — handles datasets, software, preprints, retractions correctly
- **Deduplication** at import time — never two records for the same paper
- **Conflict resolution** when two records for the same paper disagree on metadata
- **Browser extension** for one-click capture from any publisher page

### Pain points today
- Zotero / Mendeley / EndNote are powerful but **disconnected from reading and writing**
- BibTeX from publisher pages is often incomplete (missing DOI, page range, abstract)
- Citation styles are nightmarish — most tools support APA / MLA / Chicago well, fail at obscure journals
- "Did this paper actually say what I cited it for?" — almost never re-verified
- Software / dataset citation is hand-formatted; no good defaults
- Co-authors using different reference managers = merge hell

### Who plays here today
- **Zotero** — free, open-source, beloved by humanities + social science. Extensive plugin ecosystem. Aging UI.
- **Mendeley** (Elsevier) — large user base; product investment has tapered; trust eroded after Elsevier acquired.
- **EndNote** (Clarivate) — paid, institutional. Powerful but expensive and clunky.
- **Paperpile** — modern, paid, tight Google Docs integration. Loved by smaller labs.
- **SciSpace Citation Generator** — 2300+ CSL styles, one-click; positioned as a free standalone tool.
- **ReadCube Papers** — paid; reader + reference manager hybrid; modest traction.
- **BibBase, BibTeX manually** — for the LaTeX crowd who don't use tooling.

### The opening for openacad
Reference management is well-served in isolation. The opening is **integration** — citation management as a *consequence* of reading, annotating, and writing, not a separate tool. If a researcher annotates a paper in openacad, the citation entry is already complete (metadata, quotes, page locations). Insertion in the writer is just `@` → pick.

**Bigger structural opportunity: citation verification.** No mainstream tool verifies that a cited paper actually supports the cited claim. This is a known integrity problem (citation copying, citation laundering, AI-hallucinated citations). A verification pass on every citation — using the original PDF + the claim sentence — is a defensible feature.

---

## Phase 9 — Internal Review & Revision

Before submitting — friends, coauthors, advisor, lab.

### Activities
- Share draft with coauthors / advisor / friendly readers
- Collect comments via track-changes, Google Docs comments, email threads, PDF annotations, post-it notes
- Reconcile conflicting suggestions
- Re-draft sections
- Run pre-submission checks — language, format, plagiarism, AI detection
- Self-review against the journal's checklist
- Iterate 3–10 times before submission

### Features an all-in-one tool would offer
- **Structured comment threads** — like Figma / Linear, not Word comments-in-the-margin
- **AI summary of all coauthor comments** — group by theme, flag conflicts
- **Suggested resolution drafts** — AI proposes how to address a comment, you accept / edit / reject
- **Reviewer-style critique** — internal "fake reviewer" pre-mortem before real submission
- **Plagiarism + AI-detection self-check** — know your scores before the journal does
- **Language polish** — academic tone editor
- **Pre-submission checklist runner** — journal-specific, auto-validates structure / wordcount / figures / disclosures
- **Version diff** — see what changed between v3 and v4 across the whole manuscript

### Pain points today
- Comments arrive via 4+ channels (Word, email, Slack, voice) and have to be manually consolidated
- Conflicting suggestions ("make it shorter" vs "add more detail to methods") with no good resolution UX
- Self-plagiarism is easy when reusing your own prior work — most tools don't help
- "Final_v3_FINAL_actuallyfinal.docx" — version hell

### Who plays here today
- **Microsoft Word + Track Changes** — the default for most coauthor teams. Functional, ugly.
- **Google Docs** — modern collaboration; weak for math and journal formatting.
- **Overleaf** — line-by-line collab; weak for prose feedback.
- **Paperpal / Writefull** — pre-submission language polish.
- **SciSpace AI Detector** — pre-submission AI-content check (50 pages of PDF, 1500 words). Pitched specifically against GPTZero.
- **iThenticate / Turnitin** — plagiarism check; institutional access usually.
- **Grammarly** — generic; not academic-aware.

### The opening for openacad
**Genuinely underserved.** No tool today aggregates coauthor comments across channels, reconciles them, and tracks resolution. The wedge: a structured-comment system (think Figma-for-papers) where every comment has status (open / addressed / declined / discussing), can be tagged by reviewer, and can be auto-grouped by theme. AI-suggested resolutions for the easy ones; human-driven for the hard ones. This is a Linear/Figma-grade UX problem applied to academic writing.

---

## Phase 10 — Submission & Peer Review

The journal process.

### Activities
- Choose target journal — fit, impact factor, OA policy, turnaround time
- Reformat manuscript for journal template
- Write cover letter
- Suggest reviewers, declare COIs
- Submit via journal submission system (often slow, dated UIs)
- Wait — weeks to months
- Receive reviews (desk reject / major / minor / accept)
- Write point-by-point response, revise manuscript
- Re-submit
- Repeat 1–3 rounds

### Features an all-in-one tool would offer
- **Journal selector** — your manuscript + scope → ranked recommendations with fit score, IF, time-to-first-decision, acceptance rate, OA fees, predatory flag
- **Template auto-formatter** — one-click reformat for the chosen journal
- **Cover letter drafter** with journal-specific norms
- **Reviewer suggestion engine** — find non-conflicted, recent, relevant researchers from the citation graph
- **COI auto-check** — your coauthor network vs. suggested reviewers
- **Submission tracker** — status across journals (Trello for submissions)
- **Reviewer report parser** — break the report into individual concerns; assign to coauthors
- **Point-by-point response generator** — AI-drafted starting points; you edit and own the response
- **Revision diff** — show reviewer exactly what changed

### Pain points today
- Choosing a journal is folk art; matters for career outcomes; almost no tool helps formally
- Reformatting for each journal eats 1–3 days per resubmission
- Predatory journals are a real and growing trap, especially for early-career researchers
- Submission portals are 2010-era; uploading files is brittle and slow
- Response-to-reviewer letters are 5–20 pages of text with no good template
- Average paper takes 3–9 months to accept; opaque process throughout

### Who plays here today
- **Editorial Manager (Aries), ScholarOne (Clarivate)** — submission portals used by ~80% of journals. Journal-owned, not researcher-owned. Notoriously dated UX.
- **Journal/Author Finder (Springer, Elsevier, JANE, Edanz)** — journal-recommendation engines. Limited to one publisher's catalogue or based on title/abstract only.
- **Authorea, Curvenote** — try to bridge writing → submission with format-aware export.
- **Penelope.ai** — pre-submission compliance check (largely defunct).
- **No mature point-by-point response tool exists.**

### The opening for openacad
**Skip the submission portals** — journals own them and won't open. But there are sub-wedges:
1. **Journal selection** — a *publisher-neutral* recommendation engine using OpenAlex's open citation graph could beat publisher-specific finders.
2. **Reformatting** — one-click template swaps for the top 200 journals (Overleaf does this for LaTeX; Word users are stranded).
3. **Reviewer-response workflow** — none exists. Treating the reviewer report as a structured ticketing system with AI-drafted responses is a clean greenfield feature.

---

## Phase 11 — Publication, Dissemination & Impact

After acceptance.

### Activities
- Proofread galleys, sign copyright forms, choose OA option
- Announce on Twitter / Bluesky / LinkedIn / Mastodon
- Post preprint version (if not already)
- Update CV, Google Scholar profile, ORCID, institutional repository
- Present at conferences, give invited talks
- Create video abstract / lay summary / press release
- Track citations, downloads, altmetrics, news mentions
- Respond to follow-up questions, requests for code/data
- Watch for retractions / corrections in your own work
- See your work cited; loop back to ideation when new questions emerge

### Features an all-in-one tool would offer
- **Auto-dissemination** — push announcement copy to Twitter / Bluesky / LinkedIn / your own newsletter from one draft
- **AI-generated lay summary** in 5 languages
- **AI-generated video abstract** + slide deck
- **Multi-repo deposit** — push to preprint server, institutional repo, ORCID, Google Scholar in one action
- **Citation dashboard** — alerts when cited; daily/weekly digest; breakdown by field / country / institution
- **Altmetrics aggregator** — mentions in news, policy docs, Wikipedia, social
- **Follow-up tracker** — see what new questions your paper raises in citing work
- **Retraction watch** for your own and adjacent work
- **Data + code reuse tracker** — who's downloading your dataset, forking your repo, using it in published work

### Pain points today
- Promotion is awkward for many researchers — they have great work but no time / training to market it
- Tracking citations is fragmented: Google Scholar, Semantic Scholar, OpenAlex, Web of Science all disagree
- "Who's actually building on my work?" — citation count gives no answer; need to read citing papers
- Altmetrics are scattered across Altmetric.com, PlumX, ImpactStory
- Code / data reuse is invisible — you publish a dataset, never know who used it

### Who plays here today
- **SciSpace Citation Booster** — converts PDFs to video abstracts + AI avatars + slide decks; auto-posts to Instagram / TikTok / YouTube. Claims +20% citations, +48% views.
- **Kudos** — pioneered structured plain-language summaries + tracking. Lost momentum.
- **Altmetric.com, PlumX, ImpactStory** — altmetric dashboards. Institutional / publisher buyers.
- **ResearchGate, Academia.edu** — academic social networks. ResearchGate dominant in life-sciences, declining in CS.
- **Google Scholar Profile, ORCID, ImpactStory** — citation tracking with diverging counts.
- **Twitter / Bluesky / Mastodon / LinkedIn** — manual; no academic-aware tooling.

### The opening for openacad
**Citation Booster shows the pattern, but it's a feature not a moat.** This phase is fragmented but each piece is small. Not a primary wedge for openacad. The defensible play here is **owning the loop back to Phase 0** — when your paper gets cited, openacad surfaces the citing work as a new ideation prompt, closing the lifecycle into a cycle. That's a strategic feature, not a primary product.

---

## Cross-Cutting Concerns (every phase)

### Collaboration

**Activities:** co-author with peers; advise students; review others' work; participate in lab / reading groups.

**Features:**
- Shared collections, shared annotations (with permission boundaries)
- Lab / group workspaces with role-based access (advisor / postdoc / grad student / undergrad)
- Asynchronous discussion threads on papers, sections, claims
- Audit trail of who contributed what (for authorship disputes)
- Voice / video integration for lab meetings tied to the workspace

**Who plays here:** Slack + Google Drive + email is the actual stack. No academic-native tool. Notion / Confluence sometimes used. SciSpace Enterprise sells team workspaces but is heavy.

**Pain points:** lab knowledge walks out the door when students graduate; co-authoring across institutions is Slack + email + Google Drive chaos.

### Project & Time Management

**Activities:** juggle 3–10 concurrent projects; teaching duties; grant deadlines; thesis chapters.

**Features:**
- Project-level workspaces; per-project library, drafts, data, code
- Deadline tracker tied to journal targets, grant cycles, conference dates
- Reading goals — "finish lit review by April 1"
- Daily / weekly review prompts ("you haven't touched the Smith et al. paper in 3 weeks")
- Time-tracking per project (optional, for grant reporting)

**Who plays here:** Notion / Asana / Linear / Trello, all generic. No academia-specific project manager.

**Pain points:** PhD students are perpetually behind on everything; no tool helps them triage; advisors have no visibility into where students are stuck.

### Funding & Grants

**Activities:** find funding opportunities; write grant applications; track budgets; report to funders.

**Features:**
- Grant opportunity search (NSF, NIH, ERC, Wellcome, private foundations)
- Grant proposal workspace — reuses lit review, methods, prior pubs from your knowledge base
- Budget tracker + funder reporting templates
- Research-output report generator (auto-pulls publications, presentations, data)

**Who plays here:** Pivot (Clarivate), GrantForward, Cactus Mind (paid). Most universities offer in-house lookups. No good integrated drafter.

**Pain points:** writing grants requires repeatedly reformatting your CV, publications, and bio for each funder; auto-generation is rare.

### Open Science & Reproducibility

**Activities:** preregister; share data; share code; deposit preprints; document provenance.

**Features:**
- Preregistration on OSF / AsPredicted built into the methodology phase
- One-click preprint deposit (arXiv / bioRxiv / OSF) with cross-reference to journal submission
- FAIR-compliant data publishing (Zenodo / Figshare / Dryad) with auto-DOI
- Code archiving + DOI (Zenodo + GitHub release integration)
- Reproducibility checklist auto-validated at submission

**Who plays here:** OSF for pre-registration; Zenodo / Figshare / Dryad for data; arXiv / bioRxiv for preprints. All distinct, all manual handoff between.

**Pain points:** open-science workflows are *more* friction than the closed alternative; researchers do them when forced; tooling should invert this.

### Mental Health & Sustainability

**Activities:** survive rejection; manage workload; avoid burnout; sustain motivation.

**Features:**
- Encouragement tone in AI feedback (low-bar but real)
- Workload dashboard — flag overcommitment honestly
- "Progress wins" surface — show what you've finished, not just what's pending
- Optional check-ins and reflection prompts (some users will hate this; opt-in)

**Who plays here:** Nobody. Generic wellness apps don't model the PhD failure mode.

**Pain points:** academia has a culture of grind and isolation; software tools have ignored this entirely; an opinionated platform could subtly nudge sustainable habits.

---

## Composite Implications for openacad

Reading the lifecycle + competitive map together, the conclusions:

### Where the gaps are real

| Phase | Gap strength | Why |
|---|---|---|
| **Phase 0** (Ideation) | Strong | Almost no tools. Litmaps/ResearchRabbit only adjacent. |
| **Phase 2** (Screening, non-clinical) | Medium | Covidence owns clinical; CS/social-science/humanities are wide open. |
| **Phase 3** (Reading) | Weak | SciSpace + ChatPDF cover it well. Only edge cases left. |
| **Phase 4** (Annotation) | **Very strong** | Weakest phase in the entire landscape. Hypothes.is old, LiquidText iPad-locked, Obsidian not paper-aware. |
| **Phase 5** (Synthesis with provenance) | Strong | Elicit / SciSpace cover extraction but not claim-level provenance or contradiction surfacing. |
| **Phase 7** (Writing rooted in your own annotations) | Strong | Overleaf/SciSpace AI Writer don't know what you highlighted. |
| **Phase 8** (Citation verification) | Strong | No mainstream tool verifies the cited paper supports the cited claim. |
| **Phase 9** (Coauthor revision UX) | Medium | Nothing aggregates comments across channels with structured resolution. |
| **Phase 10** (Journal selection + reviewer response) | Medium | Submission portals owned by journals, but selection and response drafting are open. |

### Where to deprioritise for v1

- **Phase 6 (lab execution)** — territorial (Benchling, OSF, GitHub, Jupyter). Years of work for a fragmented market.
- **Phase 10 (submission portals)** — journals own them; you don't beat Editorial Manager from outside.
- **Phase 11 (dissemination)** — SciSpace Citation Booster shows the pattern; feature, not moat.

### The recommended wedge

**Phases 3–5: Read → Annotate → Synthesize, with provenance preserved end-to-end.**

Rationale:
1. **Competitive gap is real and large** — annotation in particular is genuinely underserved.
2. **Work is text/graph-native** — no wet-lab integration, no journal partnerships, no regulatory burden.
3. **Strongest lock-in surface** — annotations + personal knowledge graph become permanent switching cost. Five hundred annotated papers cannot be exported to a competitor.
4. **Natural expansion path** — forward into Phase 7 (writing) for monetisation, backward into Phase 1 (discovery) for acquisition.

The horizontal play — one workspace spanning Phases 0 → 11 — is the long-term map. But the wedge must be one phase done extraordinarily, with the rest growing out of it organically as users stay.

### What this means for the data model

The Publication schema work in `NOTES.md` is correct but insufficient. It defines what a paper *is*. The lifecycle reveals that the **annotation** and the **synthesis graph** are equally first-class entities, and the data model needs them at the same level of rigor:

- An **annotation** is a tuple of `(user, publication_version, anchor_target, content, timestamps, links_to_other_annotations, links_to_synthesis_nodes)`.
- A **synthesis node** is a claim or concept that aggregates annotations across publications, with backlinks in both directions.
- A **draft section** is a piece of prose whose every sentence resolves to one or more annotations (= the provenance chain).

This is the actual moat: not the paper graph (which OpenAlex / Semantic Scholar already give us), but the *user's* graph on top of it.
