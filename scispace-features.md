# SciSpace — Feature & Route Inventory

Crawled **2026-05-22** (live, first-party HTML behind AWS WAF). 26 routes documented. Quotes are SciSpace's own marketing copy unless noted otherwise.

**Tagline:** "AI research assistant for academics. Run systematic literature reviews on 280M+ papers, and write papers with cited sources."
**Trust signal:** 1M+ researchers, 280M+ papers indexed.
**Parent:** PubGenius Inc. (Milpitas, CA). Formerly known as Typeset.

---

## Top-level navigation

Header surfaces only these tools — the rest live in the footer or the in-app agent gallery:

`Agent Gallery` · `AI Writer` · `Chat with PDF` · `Literature Review` · `Find Topics` · `Paraphraser` · `Citation Generator` · `Extract Data` · `AI Detector` · `Enterprise` · `Pricing`

Logged-in homepage exposes a "Tools" sidebar with: **Deep Research · Systematic Research – PRISMA · Biomedical Agent · Lite · Search Papers · Literature Review · Draft · Diagrams · Presentation**.

---

## 1. Home — `/`

- **H1:** "How can I help with your research?"
- **Sub:** "Handle everyday research tasks with reliable, citation-backed results"
- A chat-first landing: input box at the top, tool chips below ("Deep Research", "PRISMA", "Biomedical Agent", "Lite", "Search Papers", "Literature Review", "Draft", "Diagrams", "Presentation").
- New users get **100 free credits**.

## 2. Agent Gallery — `/agents`

- **Title:** "AI Agents for Research | Free Your Time from Monotony"
- **Meta:** "Let AI handle the monotonous steps—screening, data extraction, formatting—so you can do real research. Explore agents for PRISMA, patents, trials, grants & more."

40+ specialized agents identified in the gallery. They cluster into themes:

**Biomedical / -omics**
- scRNA-seq Clustering Assistant
- scRNA-seq QC Assistant (Single-Cell Quality Control)
- GTEx ID Lookup (Gene & Sample Mapping)
- GEO Export / Batch Query (Gene Expression Datasets)
- TCGA Export / Batch Query (Multi-Cohort Genomic Data)
- NCBI Gene Export / Batch Query
- Ensembl Batch Query / Export (Genes, Variants, FASTA)
- ClinVar Batch Query (Variant Lists)
- OMIM Batch Query / Export (Gene–Disease)
- ADME Profiling Prediction Assistant (Pharmacology)
- Cell Doubling Time Calculator
- Restriction Enzyme Digestion Calculator
- Pathway Diagram Generator (Biomedical Maps)

**Drug safety / clinical**
- MedDRA ID Lookup (Drug Safety Teams)
- MedDRA Coding Assistant for Pharmacovigilance
- Clinical Guidelines ID Lookup
- FDA Label ID Lookup (Drug Labeling Records)
- SRA ID Lookup (NCBI / ENA Accessions)
- UpToDate Export Tool

**Statistical reporting (APA style)**
- Report Risk Ratio in APA
- Report Cox Regression in APA
- Report Relative Risk APA Style
- Report Kruskal Wallis Test APA Style
- Report Number Needed to Treat in APA
- Report Hazard Ratio in APA (HR, CI, p)
- Interrater Reliability — Cohen's Kappa Calculator

**Patent / IP**
- Patent Citation Network Analyzer
- Patent Search Strategy Builder
- Prior Art Search Assistant
- USPTO Design Patent Search
- Patent Prior Art Disclosure Template
- Invention Disclosure Form Generator

**Operational / lab**
- Lab Notebook AI Template
- Code Availability Statement Generator
- Meta Analysis Funding Statement Generator

> **Take-away for openacad:** SciSpace's "agent" surface is not generic chat — it's a marketplace of narrow, vertical-specific tools (biomedical-heavy). They're effectively a hub for **single-purpose research tools wrapped in agent UX**.

## 3. AI Detector — `/ai-detector`

- **H1:** "Academic AI Detector"
- **Pitch:** "Instantly spots ChatGPT, GPT-4, Gemini, Llama and Claude's text, rates originality, and explains risky lines. Proven to outperform GPTZero, ZeroGPT, and Grammarly."
- **Limits:** 1,500 words per check, **50 pages of PDF**, 5,000 chars on free tier.
- **Features:** Sentence-level AI detection; generalized AI probability score.
- **Compared against:** GPTZero (explicit side-by-side).

## 4. AI Writer — `/ai-writer`

- **H1:** "Write Research Papers with Confidence — Powered by AI"
- **Sub:** "Find, edit & cite 280M+ papers instantly with AI assistance"
- **Pillars:**
  - **Cite as you write** — citations pulled from 280M+ papers
  - **Autocomplete your thoughts** — companion that detects, suggests, completes
  - **Limited only by your imagination** — open-ended generation
  - **Export on the fly** — no-loss formatting
- **Languages:** 75+
- **Compared against:** Jenni AI ($12/mo), PaperPal ($25/mo). SciSpace pitches **$20/mo for unlimited access to all features + AI writer** (excluding Deep Review).

## 5. Biomedical Agent — `/biomedical`

- **H1:** "SciSpace BioMed Agent" — "AI Co-Scientist for Drug Discovery, Genomics & Lab Protocol Reasoning"
- **Pitch:** "A specialized biomedical research co-scientist for multi-omics, clinical phenotypes, and lab protocol reasoning"
- **Action space:** "100+ Biomedical Software Packages · 150+ Specialized Biological Tools · Dozens of Curated Biomedical Databases"
- **Domain coverage:** genetics, genomics, synthetic biology, cell biology, physiology, microbiology, pharmacology, bioengineering, biophysics, molecular biology, pathology.
- **Three use-case lanes:**
  1. Drug Discovery & Pharmacology
  2. Clinical Genomics & Rare Disease
  3. Single-Cell & Multi-Omics
- **Personas:** academic labs, clinician-scientists (rare disease, translational), biotech / pharma teams (targets, screens, repurposing).
- Pitched as an org-scalable product (enterprise upsell).

## 6. Chat with PDF — `/chat-pdf`

- **Pitch:** "Upload any PDF, ask a question, get concise, citation-linked answers, summaries, and follow-ups in seconds — free tier, 256-bit encrypted, no data training, supports 75+ languages."
- **Capabilities:**
  - Citation-backed answers
  - Paper summary
  - Highlighted-text explanations
  - "Get related papers" surface
  - Note taking
  - Explanations for **math, equations, tables, figures**
  - Modify length / tone / format of answers
- **Compared against:** ChatPDF, PDF.ai (explicit side-by-side).

## 7. Citation Booster — `/citation-booster`

- **H1:** "Get more citations with AI-generated video abstracts and presentations"
- **Pitch:** Convert PDFs into video abstracts + slides, push them to social to boost citation count (claims +20%, +48% more views).
- **Capabilities:**
  - AI avatar with your own voice and style
  - Diverse AI voices to pick from
  - AI-generated scripts, editable
  - Subtitle superimposition
  - MP4 export, social-optimized
  - Auto-distribution to Instagram, TikTok, YouTube
  - Automatic slide generation from PDF sections
  - Research-publication insight analysis

## 8. Citation Generator — `/citation-generator`

- **Title:** "Access 2300+ Citation Styles on SciSpace"
- **Pitch:** "Generate citations in APA, MLA, Chicago, Harvard and 2300+ styles in 1-click. Free."
- Page is mostly SPA-rendered; specific style pages exist at `/citation-generator/<style-slug>`.

## 9. Chrome Extension — `/copilot-chrome-plugin`

- **H1:** "SciSpace Chrome Extension"
- **Pitch:** "Take your AI research assistant wherever you go. Real-time answers to articles, no matter where you read them online."
- **Targets:** publishers, repositories, news outlets, blogs.
- **Capabilities:**
  - Simplify technical language inline
  - Find context for math and tables in PDFs
  - "Delve deeper while learning" (related-papers surfacing)
  - Access in your native language

## 10. Data Sources — `/datasources`

- Page is mostly a structured list (SPA-rendered). Only a `Data Sources` title visible to crawler.
- (For full list, in-app view is needed — they advertise OpenAlex-class coverage across 280M+ papers, but the page itself lists explicit providers.)

## 11. Enterprise — `/enterprise`

- **H1:** "AI for Scientific Research, Tailored for Your Enterprise"
- **Positioning:** "Industry leading, AI native Research Workspace for R&D teams"
- **Headline claim:** Search 5+ databases at once; "10x" the literature-review cycle.
- **Sections:**
  - Automated Literature Reviews with the widest coverage
  - Start with Search & extend AI to your entire workflow
  - Custom AI Workflows (consulting offer)
  - Import data for your research
  - AI that's Secure and Auditable
  - Agentic Workflows for Every Industry (Medical Devices, CROs called out)
- **Capabilities listed:**
  - Extract data from papers (high accuracy)
  - Turn literature reviews into reports
  - Turn content into visually-stunning presentations
  - Write grant applications after finding research gaps
  - Personalised AI agents per use case
  - Tool integrations (ELNs, SharePoint, reference managers per FAQ)
- **FAQ exposes:**
  - Data isolation (your data not used to train models)
  - Audit / governance trail for submissions and reports
  - Paywalled-journal access strategy
  - Direct comparison to ChatGPT / Perplexity for research workflows
- **Personas mentioned:** universities, pharma, R&D, CROs, medical devices.

## 12. Extract Data — `/extract-data`

- **H2:** "Extract Data From Research Papers"
- **Pitch:** "Identifies tables, stats and citations in research PDFs, summarises key findings and exports clean data to CSV, Excel or RIS — supporting 75 languages."
- **Capabilities:**
  - Semantic search
  - Extract & compare information across papers
  - Citation-backed insights
  - Paper summary
  - Export in multiple formats (CSV, Excel, RIS)
- **Compared against:** Elicit, Consensus (explicit side-by-side).

## 13. Mobile App — `/mobile-app`

- **H1:** "Accelerate your scientific discoveries right from your pocket"
- **Pitch:** "Search, Summarize, and Explore Peer-Reviewed Journals in Seconds — all in One App"
- **Pillars:**
  - Academic focus (peer-reviewed sources only)
  - Time-saving insights (summaries on the go)
  - Trustworthy sources

## 14. Paraphraser — `/paraphraser`

- **H1:** "Free AI Paraphraser Tool"
- **Pitch:** "Rewrites academic text in 75+ languages. Keeps citations intact, helps you avoid plagiarism while sounding natural."
- **Capabilities:**
  - Style/tone selection (any tone)
  - 75 languages
  - Customize length and variation of paraphrased output
  - Stay in charge of your content (you keep ownership)
  - Built-in AI detection pass
- **Compared against:** Quillbot (explicit head-to-head with paragraph examples).

## 15. Recruit Researchers — `/recruit-researchers`

- **H1:** "Find, Recruit & Collaborate with Professors, Researchers and more with AI"
- **Pitch:** "AI Agent to 10x your recruitment workflow. Source from over 800M+ enriched profiles."
- **Pillars:**
  - Evidence-based sourcing for committees and academic hiring
  - Enrichment that committees can trust
  - Intelligent agent that simplifies your pipeline
- **Enrichment signals:**
  - Past work relationships
  - Publications & citations
  - Grants and funding eligibility
  - Job-change signals
  - Email lookup ("access candidate e-mails")
- **Database:** 6M+ researchers / academicians from premier institutions; 800M+ profiles total.
- Note: this is an *unexpected* product — SciSpace is not just a research workspace; they're also leveraging their citation graph as a B2B sourcing / talent-intel product.

## 16. Literature Review — `/search`

- **Title:** "SciSpace Literature Review | AI Agent for conducting reviews"
- **Pitch:** "Conduct faster, smarter literature reviews. Use Deep Review to run systematic literature reviews in minutes."
- Page is mostly SPA-rendered (in-app surface). Key product names: **Deep Review**, "Systematic Research – PRISMA" (separate agent).

## 17. Templates — `/templates`

- **Title:** "Writing Templates for Researchers"
- "All Templates" — free, downloadable in MS-Word format.
- This is a long-tail SEO surface, not a marquee feature.

## 18. Pricing — `/pricing`

- **H1:** "Simple and transparent pricing"
- 24-hour money-back guarantee on all plans.
- Credit-based system: monthly credits, optional Add-On Credits. FAQ surfaces:
  - Plans for Premium / Editor tools
  - Credit consumption per task
  - Whether unused credits roll over (separately for monthly and add-on)
  - Concurrent-task capacity (org plans)
  - Whether individual team members can buy their own add-on credits
- AI Writer comparison page suggests **~$20/mo** for an unlimited tier (their published number against PaperPal's $25/mo and Jenni's $12/mo).

## 19. Resources — `/resources/`

- Hub for blog / learning content. Also referenced: **Live Workshops**.

## 20–25. Directory pages (long-tail SEO surfaces)

These are SPA-rendered directory indexes. Sizes give the scale claim:

| Route | Title claim |
|---|---|
| `/papers` | "200 million+ research papers across 250,000+ topics" |
| `/authors` | "250 million academic researcher profiles" |
| `/journals` | "**119,463** scientific journals" |
| `/institutions` | "**62,350** Research institutions & Universities" |
| `/conferences` | "**7,027** research conferences" |
| `/topics` | "**259,573** most cited research topics" |
| `/concepts` | "Find Topics" — go deeper to extract insightful topics |

Each is the entry point to thousands of individual paper / author / journal landing pages used for SEO.

## 26. Other footer routes

- `/influencer-program` — SciSpace Affiliate Program
- `/privacy`, `/terms`, `/cancellation_and_refund_policy.pdf`
- Contact: `support@scispace.com`

---

## Competitive positioning (per SciSpace's own pages)

SciSpace explicitly compares itself to:

| Surface | Compared against |
|---|---|
| AI Detector | GPTZero, ZeroGPT, Grammarly |
| Chat with PDF | ChatPDF, PDF.ai |
| AI Writer | Jenni AI, PaperPal |
| Paraphraser | Quillbot |
| Extract Data | Elicit, Consensus |
| Enterprise | ChatGPT, Perplexity (general AI) |

That comparison set is itself a roadmap of what they consider their addressable surface: **detection + reading + writing + paraphrasing + extraction + chat copilot**, with biomedical agents as the vertical wedge.

---

## Implications for openacad

1. **SciSpace already covers Stage 1 (discovery) + Stage 4 (synthesis) + Stage 5 (writing)** of the landscape map. Their gap is **Stage 2 (systematic-review screening)** and **Stage 3 (lab/ELN)** — but they're encroaching on Stage 2 with "PRISMA Agent" and "Deep Review".
2. **Their moat is agent surface area**, not core LLM quality. 40+ vertical agents for biomedical specifically (drug safety, -omics, patents, APA stats reporting). To compete, you'd either pick a different vertical or beat them at agent UX.
3. **Recruit is their hidden monetisation play** — turning the citation/profile graph into a B2B talent product. This is leverage from data they already had, not a separate product build. Worth noting as a long-term revenue path.
4. **Credits-based pricing**, not flat-rate subscriptions. Their FAQ implies pricing complexity (monthly credits + add-on credits + concurrent-task limits) is a real friction point — competitor opportunity for transparent pricing.
5. **Math + equations are explicitly called out** in Chat with PDF copy ("Explanations for math, equations, tables and figures"). They have a working answer to the LaTeX/math rendering problem we flagged in NOTES.md — confirms it's not just nice-to-have, it's table stakes.
6. **No marquee annotation/highlighting product**. The Chrome extension touches it ("highlight to explain") but there's no Hypothes.is-grade annotation layer. **Potential wedge for openacad.**
7. **No PDF anchoring / bounding-box highlighting** is advertised. Suggests the hard problem we flagged in NOTES.md is *not* solved by the incumbent — also a wedge.
