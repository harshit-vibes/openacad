# The Atomic Idea: What Is the Unit of Knowledge?

A survey of philosophical, cognitive-scientific, computational, and library-science traditions that have tried to answer one question: when we say "an idea," what exactly is the *one* — and is there even such a thing?

---

## 0. Framing: why this question is unresolved

Your working hypothesis — that ideas can be distilled into atomic units with attributes, related by edges that themselves carry attributes — has a long and respectable intellectual pedigree. It is essentially the **frames-and-slots** picture from 1970s AI plus the **Zettelkasten principle of atomicity** plus the **property graph** data model. Three independent traditions converge on it. That is a good sign.

Your suspicion — that there is no objective atom, that what is atomic to one researcher decomposes for another — is also not a fringe view. It is, in fact, the **mainstream philosophical position after roughly 1950**: the dominant traditions in analytic philosophy (Quine, Wittgenstein, Brandom, Davidson), in linguistics (frame semantics, construction grammar), in cognitive science (prototype theory, distributed representations), and in philosophy of information (Floridi's levels of abstraction) all converge on some form of *holism* or *contextualism* about meaning.

So you are simultaneously right *and* right: the atom is a fine engineering primitive, and there is no metaphysically privileged atom. What the literature offers is a vocabulary for living with that tension, and a set of design choices that follow from it.

---

## 1. The philosophical lineage of "atomic thought"

The idea that thoughts decompose into elementary parts is old. The modern tradition has roughly four big moments.

**Ancient atomism transplanted to the mind.** Democritus and Leucippus argued the physical world is built of indivisible atoms. The metaphor jumps to mind cleanly: if matter is combinable particulars, perhaps thought is too. The word *atom* itself — Greek *atomos*, "uncuttable" — already carries the contested assumption: that there is a level where division stops.

**Locke (1689).** *An Essay Concerning Human Understanding* is the canonical atomist KM model. Locke distinguishes **simple ideas** (received passively from sensation or reflection — yellow, hot, the experience of doubting) from **complex ideas** (built by the mind from simples, by combining, comparing, abstracting). Locke gives you, almost exactly, the user-facing model: a substrate of primitives plus operators that combine them.

**Hume (1739).** Hume tightens Locke. There are **impressions** (the live original) and **ideas** (faded copies), and ideas combine via three association laws: *resemblance*, *contiguity*, and *cause-and-effect*. Hume is the first to give you a relational structure — the *links* are typed, and the types are few.

**Leibniz.** Leibniz proposed two things that still echo. First, **monads** — minimal indivisible substances of which everything is composed. Second, and more relevant here, the **characteristica universalis**: a hypothetical universal alphabet of human thought, in which every concept could be written as a combination of primitive symbols, and reasoning could become *calculation* (his *calculus ratiocinator*). This is the founding dream of formal knowledge representation. The dream did not die — Frege, Russell, Carnap, and ultimately the Semantic Web all chase it.

**Frege (1884–1892).** Frege opens the modern era and simultaneously plants the bomb that destroys naive atomism. Two contributions matter:
- The **sense / reference** distinction (*Sinn* / *Bedeutung*): a name has both a referent (the thing it points to) and a sense (the mode of presentation). "Morning star" and "evening star" share a reference (Venus) but differ in sense. Meaning is at least two-layered, not one atom.
- The **context principle**: "Only in the context of a proposition does a word have meaning." This is the first explicit denial of pure atomism — a word *outside* a proposition is meaningless, so the proposition is in some sense prior to the word.

**Russell and the early Wittgenstein.** *Logical atomism*, roughly 1918–1922. The world consists of *atomic facts*; language, properly analyzed, consists of *atomic propositions* that picture them. Russell's logical atomism and Wittgenstein's *Tractatus Logico-Philosophicus* are the high-water mark of the atomist picture. The *Tractatus* famously ends: "Whereof one cannot speak, thereof one must be silent." Inside the realm we can speak about, everything decomposes.

**The collapse.** Logical atomism does not last twenty years. Wittgenstein himself abandons it in the *Philosophical Investigations* (published 1953). He introduces **family resemblance** — categories like "game" have no shared essential feature, only overlapping similarities — and the slogan **"meaning is use."** Words mean what speakers do with them in *language games*, not what they pick out in some abstract space.

**Quine (1951)** finishes the demolition in "Two Dogmas of Empiricism." Beliefs do not face experience individually — they face it "as a corporate body." This is **confirmation holism** (also called the **Quine–Duhem thesis**): no isolated proposition is empirically meaningful on its own; you can always save any belief by adjusting other beliefs. If meaning depends on relations to other beliefs, there are no semantic atoms.

**Brandom (1994)** gives this its most muscular contemporary form — **inferentialism**. The meaning of a concept *is* its inferential role: the moves it licenses, the moves it precludes. "Red" means what it does because of how it functions in inferences (from "is red" you can infer "is colored," etc.). On this view, concepts cannot be atoms — they exist only as nodes in a web of inferential commitments.

The arc, very compressed: Locke → Hume → Leibniz → Frege → Russell/early-Wittgenstein were *atomists*. Frege already cracks it. Later Wittgenstein, Quine, Davidson, Brandom are *holists*. The holists win the 20th century.

---

## 2. Cognitive science: are concepts atoms?

If philosophy lost faith in atomic *meanings*, psychology lost faith in atomic *concepts* on a similar arc.

**The classical view** — a concept is defined by necessary and sufficient conditions ("bachelor = unmarried + adult + male") — fails empirically by the 1970s. People do not actually represent concepts this way; performance and judgment patterns do not fit.

**Eleanor Rosch's prototype theory (1973–1978).** Categories are **graded**: a robin is a more "central" bird than a penguin. People classify by similarity to a prototype, not by checking necessary conditions. There is no atomic core to "bird" — the category has a shape, with center and periphery.

**Exemplar theory** (Medin, Nosofsky) goes further: there is no prototype at all, only a memory of specific encountered instances. Concepts are *clouds* of remembered cases.

**The "theory" theory** (Murphy, Medin, Carey, Gopnik) holds that concepts are embedded in mini-theories about the world: knowing what "tiger" means is not knowing a list of features but holding a small theory of what tigers do, why they are dangerous, how they relate to lions. Concepts are theory-laden, not atomic.

**Jerry Fodor's conceptual atomism.** The major dissent. In *The Language of Thought* (1975) and especially *Concepts* (1998), Fodor argues — controversially — that **most lexical concepts are unstructured atoms**. DOG is just DOG; it is not built from MAMMAL + BARKS + DOMESTICATED. The meaning of an atom is determined by its **informational link** to the world (this is "informational atomism"). Fodor is the strongest modern defender of the atomist instinct, and he is a minority position even within cognitive science, but the position is alive and worth knowing.

**Schemas and frames.** Bartlett (*Remembering*, 1932) shows memory reconstructs via culturally shared **schemas**. Minsky (1974) formalizes this as **frames** — packets of expectations about a situation, with **slots** that have default values and constraints. Schank's **scripts** are the same idea for events ("the restaurant script"). The unit here is not the atom but the *structured packet*.

**Mental models** (Johnson-Laird, 1983) — people reason by simulating small structured models, not by applying logical rules to atomic propositions.

**Chunking.** Miller's famous 7±2 (1956), revised down to roughly four by Cowan (2001). The interesting thing for our question is that what counts as one chunk is **task-relative**: an expert chess player chunks a board position as a single unit; a novice sees twenty separate pieces. The same physical stimulus is one atom for one mind and twenty for another. *The cognitive atom is not in the stimulus — it is in the schema applied to it.*

**Connectionism and distributed representations.** From the 1980s on (Rumelhart, McClelland), concepts can be represented as patterns of activation across many units, with no discrete locus. The modern descendant is the **embedding**: in a transformer, "dog" is a 4,096-dimensional vector, and meaning is geometric proximity. There is *no* atom — there is a continuous space.

The state of play: in cognitive science, the *atom* survives as an engineering convenience and a Fodorian minority view; the *structured packet* (frame, schema, mental model) dominates classical theorizing; the *distributed pattern* dominates modern neural theorizing. None of the three privileges the atom.

---

## 3. Knowledge representation in computer science

When AI tried to actually build knowledge bases, it had to pick a unit. The history is a sequence of attempts.

**Semantic networks** — Quillian's 1968 thesis. Nodes for concepts, labeled edges for relations. This is the OG node-and-edge model and every knowledge graph since is a descendant.

**Frames** — Minsky's 1974 "A Framework for Representing Knowledge." A frame is a *unit with named slots*. Slots have types, defaults, and constraints. A "chair" frame has a SEAT slot, a LEG-COUNT slot (default 4), an OWNER slot. This is — almost word for word — your idea + attributes model. The frames tradition runs through KL-ONE, CLIPS, and into modern object-oriented programming.

**Conceptual graphs** — John Sowa's synthesis (1984) of semantic networks and Peircean existential graphs.

**RDF triples** — the World Wide Web's bet. The unit is the **triple**: subject, predicate, object.

```
<einstein> <wrote> <relativity-paper-1905> .
<relativity-paper-1905> <published-in> <annalen-der-physik> .
<einstein> <employer-1905> <swiss-patent-office> .
```

RDF makes the *relation* a first-class atomic unit. But classic RDF has a famous weakness: edges cannot have attributes. To say "Einstein wrote this paper *in 1905*" you have to **reify** the triple (turn it into a node), which is awkward. RDF-star (RDF*) fixes this.

**Description logics → OWL** — a formal layer on top of RDF for inference. The atomicity is the same; the additions are class hierarchies and reasoning rules.

**Property graphs** — Neo4j, TigerGraph, AWS Neptune. Nodes and edges both carry **properties** (key-value pairs). This matches your intuition exactly: relations are not just typed, they are typed *and attributed*. In Neo4j you can say `(einstein)-[:WROTE {year: 1905, language: "German"}]->(paper)` natively.

**Embeddings.** The radical alternative. The unit is a vector in a high-dimensional space; meaning is geometric. There is no symbolic atom at all. Modern vector databases (Pinecone, Weaviate, pgvector) and the retrieval substrate of every LLM application use this. The cost is *lost legibility*: you cannot look at the vector and say what it means.

**Neurosymbolic / hybrid.** The current research frontier. Combine discrete symbolic atoms (legible, composable, reasoning-friendly) with continuous embeddings (fuzzy, similarity-friendly, learnable). Examples: KG-augmented LLMs, retrieval-augmented generation over a typed knowledge graph, GraphRAG, neural theorem provers. This is where most of the live activity is.

The design lesson from this tradition: **the relation is at least as important as the node**, and modeling relations as bare typed edges is too poor — they need attributes, provenance, evidence.

---

## 4. Library and information science: the social atom

Libraries had to pick units centuries before computing existed.

**Ranganathan's facet theory** (1933, *Colon Classification*) decomposes any subject along five facets: **PMEST — Personality, Matter, Energy, Space, Time**. A book is not classified into one slot but indexed by where it lies along each facet. The "atom" here is *the facet value*, and a thing is a *combination* of values.

**Bliss classification**, **Library of Congress Subject Headings (LCSH)**, **Medical Subject Headings (MeSH)** — controlled vocabularies of concept atoms. The crucial observation: these atoms are *socially constructed*. A committee decided that "Information science" is one heading and "Information theory" is another. The atom is not discovered in nature; it is a convention agreed by a community for the purpose of indexing.

**SKOS — Simple Knowledge Organization System** (W3C, 2009). A vocabulary for representing thesauri and taxonomies as graphs. Concepts (the atoms) carry `prefLabel`, `altLabel`, `definition`, and stand in relations `broader`, `narrower`, `related`. SKOS is the practical engineering atom of LIS today.

The lesson from LIS: in real practice, "an atom" is a *socially negotiated convention for a purpose*, not a metaphysical fact. It is the unit that turned out to be useful for indexing, retrieval, comparison, and citation. Different communities (medicine, law, biology) settle on different units because their tasks are different.

---

## 5. Linguistics: are there semantic primes?

Linguists have repeatedly asked whether all meanings decompose into a small set of universal primitives.

**Anna Wierzbicka's Natural Semantic Metalanguage (NSM).** Since the 1970s, Wierzbicka and Cliff Goddard have argued for roughly **65 universal semantic primes** — concepts that appear lexicalized in every human language and into which every other meaning can be paraphrased. A partial list:

```
I, YOU, SOMEONE, SOMETHING, PEOPLE, BODY,
THIS, THE SAME, OTHER,
ONE, TWO, MUCH, ALL, SOME,
THINK, KNOW, WANT, FEEL, SEE, HEAR, SAY,
DO, HAPPEN, MOVE,
WHERE, HERE, ABOVE, BELOW,
WHEN, NOW, BEFORE, AFTER, A LONG TIME, A SHORT TIME,
NOT, MAYBE, CAN, BECAUSE, IF,
VERY, MORE, LIKE, GOOD, BAD, BIG, SMALL
```

This is the closest the field has come to Leibniz's *characteristica universalis* — a small finite set into which all human meaning is claimed to be expressible. NSM is contested, but it is a serious empirical research program with hundreds of cross-linguistic studies.

**Componential analysis** (Katz–Fodor, 1963) tried decomposing meanings into binary features ([+human], [+male]). It worked for kinship terms and failed for nearly everything else.

**Frame semantics** (Charles Fillmore, 1976) — the unit is not the word but the **frame** it evokes. The verb "buy" evokes the COMMERCIAL_TRANSACTION frame with roles BUYER, SELLER, GOODS, MONEY. **FrameNet** is the lexical resource that catalogs these. This is closer to Minsky's frames than to Wierzbicka's primes.

**WordNet** (Princeton, 1985–) — words grouped into **synsets** (synonym sets representing one sense), linked by hypernymy, meronymy, antonymy. The atom is the sense, not the word. WordNet is the most-used practical resource of this kind.

The linguistics lesson: even within one field, there are at least three competing units (the prime, the frame, the synset), each useful for different tasks. The unit is the *one chosen for the task*.

---

## 6. Note-taking: where atomicity is operationalized

This is the tradition closest to building a system.

**Luhmann's Zettelkasten.** Niklas Luhmann, the German sociologist, kept roughly 90,000 paper slips. The system has an explicit **principle of atomicity**: *one idea per slip*. Slips link to other slips by numerical address. Luhmann credits the system, not himself, with the productivity of writing ~70 books — the slips, through their links, produce arguments the author would not have constructed unaided. The intellectual movement is from *storing* to *thinking via* the system.

Two contemporary writers have absorbed and amplified this:

**Sönke Ahrens, *How to Take Smart Notes* (2017)** — the standard popularization of Zettelkasten for knowledge workers. Three note types: fleeting, literature, permanent. The "atom" is the permanent note: one idea, in your own words, linked.

**Andy Matuschak, "Evergreen notes."** Notes should be **atomic** (one idea), **concept-oriented** (titled by concept, not by source), **densely linked**, and **rewritten as understanding deepens**. Matuschak runs his entire research notebook publicly at notes.andymatuschak.org and has been the most influential thinker on "tools for thought" in the 2020s.

**Block-level atomicity** — Roam Research (2019) popularized treating *every bullet block* as an addressable unit with a unique ID and backlinks. Logseq and Obsidian (via block references) inherit this. The atom moves from the *file* to the *block*. This makes recursive nesting native: a block contains blocks contains blocks.

**Tiago Forte, *Building a Second Brain* / PARA.** A pragmatist countercurrent: stop fetishizing atomicity, organize by what you can *act on* (Projects, Areas, Resources, Archives). Forte's atom is "the smallest captureable unit," and his test is utility, not metaphysical cleanness.

**Maggie Appleton and the digital gardens movement.** Notes are *cultivated*, not filed; they move through stages (seed → sapling → evergreen) as understanding ripens. Atomicity is a *stage*, not a property.

The note-taking tradition is the only one in this survey that has actually *built systems that work for individuals at scale*. Its lesson: **atomicity is enforced as a discipline, not discovered; relations carry the value; and the unit must be allowed to be rewritten.**

---

## 7. Scholarly atomicity: the unit of research knowledge

What is the atomic unit of *scholarship* specifically?

**Stephen Toulmin's *The Uses of Argument* (1958).** An argument decomposes into six components: **claim** (the conclusion), **data** (the grounds), **warrant** (the inference rule), **backing** (support for the warrant), **qualifier** (modal hedging — "probably," "usually"), and **rebuttal** (conditions of defeat).

```
Data ─── (so, qualifier) ──→ Claim
         |
         since
         |
       Warrant
         |
       on account of
         |
       Backing
                              unless
                              ↑
                            Rebuttal
```

The Toulmin schema is the closest thing the field has to a candidate atom for *argumentation*. Variants ("Claim–Evidence–Reasoning") are taught in science education.

**Nanopublications** — Barend Mons, Paul Groth, and colleagues (~2010). The unit is a single scientific **assertion** plus its **provenance** (who claimed it, on what evidence, when) plus its **publication info** (DOI, authors). A nanopub is independently citable and machine-readable. Hundreds of thousands of nanopubs exist in life sciences databases. This is the most rigorous attempt to make the *scholarly* atom operational.

**Micropublications** — Tim Clark, Paolo Ciccarese, Carole Goble. A richer model than nanopubs: each claim comes with an argumentation graph linking it to the supporting evidence, methods, and counter-arguments.

**Open Research Knowledge Graph (ORKG)** — TIB Hannover, Sören Auer. Treats research contributions as **structured comparable units**: same problem, same dimensions, different papers, side-by-side. The atom here is "a contribution" — a unit slightly larger than a claim, smaller than a paper.

**SPAR ontologies and CiTO** — Peroni and Shotton. **CiTO (Citation Typing Ontology)** types citations: `extends`, `disagrees_with`, `uses_method_in`, `obtains_background_from`. Citations are typed relations, with attributes. This is the scholarly version of the property graph.

**Rhetorical Structure Theory** (Mann and Thompson, 1988). A text decomposes into elementary discourse units (EDUs) linked by **discourse relations** (elaboration, contrast, cause, condition, concession, …). Used in computational discourse analysis and argumentation mining.

The pattern in scholarly atomicity: **claim + evidence + provenance + typed relation** is the convergent unit, across nanopubs, micropubs, ORKG, CiTO. If you are building for research, this is the shape worth taking seriously.

---

## 8. Combination as creativity

A KM system that only *stores* atoms misses the point — the value is in how they recombine.

**Arthur Koestler, *The Act of Creation* (1964).** Creativity is **bisociation**: a single idea or event is perceived simultaneously in two normally incompatible frames of reference ("matrices"). A joke works by bisociating two frames at the punchline. Discovery works the same way (Archimedes' bath bisociates "displaced water" and "measure volume").

**Joseph Schumpeter.** Innovation is *neue Kombinationen* — new combinations of existing factors. The atoms preexist; the entrepreneur's job is recombination.

**Gilles Fauconnier and Mark Turner, conceptual blending** (1990s–2002, *The Way We Think*). Two or more "mental spaces" project selectively into a **blend** that inherits structure from both and develops emergent structure of its own. "Computer virus" blends BIOLOGICAL_VIRUS and COMPUTER_PROGRAM, with emergent properties (antivirus software) that neither input had.

**Douglas Hofstadter.** *Gödel, Escher, Bach* (1979) and *Surfaces and Essences* (with Sander, 2013): **analogy is the core of cognition**. Concepts are not atoms; they are points in a fluid landscape where what counts as "the same" depends on context. A good KM system should make *analogy-finding* a first-class operation.

The design lesson: **the system's job is recombination, not storage.** Search, blend, analogy, and surprising-juxtaposition should be primitives, not features.

---

## 9. The "no objective atom" thesis — direct treatment

This is the section you specifically asked about, and the strongest claim in this whole note: **the dominant position in modern philosophy is that there is no objective, mind-independent, purpose-independent atom of meaning or knowledge.** The arguments converge from several directions.

**Confirmation holism (Quine–Duhem).** No single belief can be tested in isolation. A failed experiment never tells you *which* belief in the network was wrong. So no belief has empirical meaning by itself — meaning is distributed across the web. Quine, "Two Dogmas of Empiricism" (1951): "Our statements about the external world face the tribunal of sense experience not individually but only as a corporate body." If meaning is non-atomic, the atom is not a natural kind.

**Wittgenstein's family resemblance.** The category "game" has no necessary feature. Card games, ball games, board games, language games — they share overlapping similarities but no common essence. Most natural-language concepts work this way. Whatever you call the "atom" of "game" is a stipulation, not a discovery.

**Wittgenstein's meaning-as-use.** A word's meaning is the role it plays in a *language game*. Different language games — different meanings. The "atom" is a function of the practice.

**Brandom's inferentialism.** A concept's content *is* its inferential role. Concepts cannot be atoms because their content is constituted by relations to other concepts.

**Floridi's Levels of Abstraction.** Luciano Floridi's *Philosophy of Information* (2011) argues that every description of a system is *at a chosen Level of Abstraction* (LoA) — a specified set of observables. A water molecule at one LoA is one entity; at another it is two hydrogens and an oxygen; at another, a cloud of electrons and three nuclei. None is privileged. The same goes for ideas: *atomicity is relative to the LoA chosen for a purpose.*

**The pragmatist resolution.** Put all this together and the working answer is: **an atom is whatever is convenient to treat as one unit for the task at hand.** Atomicity is a *parameter*, not a *property*. The same idea is one atom when you are filing it, three when you are arguing for it, ten when you are teaching it, and a thousand when you are reading the underlying paper. None of these is the "true" decomposition.

**Implications for design.**

1. *Do not enforce one granularity.* The system should let users decide what is a unit for *their* purpose, and let that decision change over time.
2. *Make granularity reversible.* Allow bundling and splitting without semantic loss — the way Roam/Logseq block references let you both nest and reference.
3. *Allow the same content to appear at multiple granularities simultaneously.* A claim, the paragraph containing it, the section, the paper — all addressable, all linkable.
4. *Treat the level of abstraction as a first-class metadata field on every reference.* What is this an atom *for*?
5. *Accept that some queries cross granularities.* "Find all claims by author X that contradict claim Y" is a query that operates at the claim atom; "find all papers that argue against this thesis" operates at the paper. Both need to work.

This is the most important takeaway in this note: **you are right that there is no objective atomicity, and that is not a bug in your model — it is a fact about knowledge that your model must accommodate.**

---

## 10. Active frontiers (2020s)

Where serious work is happening right now.

**Scholarly knowledge graphs at scale.** ORKG (Open Research Knowledge Graph), OpenAlex (the open replacement for Microsoft Academic Graph), SemOpenAlex, SciGraph, Wikidata-as-research-substrate. The bet: if research outputs become structured, comparable, queryable units, science speeds up. The unit varies (contribution, claim, dataset, methodology), and the lack of consensus on the unit is one of the field's main problems.

**Nanopublications and FAIR.** FAIR = Findable, Accessible, Interoperable, Reusable. Nanopubs are the canonical FAIR-native unit for assertions. Active in biomedicine; spreading to other fields. The Nanopublication Server Network now hosts millions of nanopubs.

**Tools for thought research.** Andy Matuschak and Michael Nielsen's 2019 essay "How can we develop transformative tools for thought?" reframed the field. *Quantum Country* (a textbook that interleaves spaced-repetition prompts with prose) and the mnemonic-medium experiments are the most concrete artifacts.

**LLM-augmented PKM.** Embedding-based linking (every note has a vector; suggest links by cosine similarity), RAG over personal notes, agentic synthesis ("write me a 500-word piece pulling on these 30 notes"). The atom blurs: is the unit the note, the chunk, or the embedding? Probably all three, redundantly.

**Neurosymbolic hybrids.** Discrete typed knowledge graphs combined with continuous embeddings. GraphRAG (Microsoft), LangGraph, Neo4j's vector indexes. The bet is that legibility (symbolic) plus similarity (vector) is strictly better than either alone.

**Argumentation mining.** NLP work extracting claims, evidence, and discourse relations from scientific papers automatically. ArgMining workshops at ACL. Practical tools: scite.ai (classifying citations as supporting/contradicting), Semantic Scholar's TLDRs, Elicit.

**Levels-of-abstraction tooling.** Less mature, but emerging: systems that explicitly let a user define and switch between LoAs over the same underlying content. Most are research prototypes; none yet dominant.

---

## 11. Synthesis — implications for your KM system

Not a product spec. Just principles that the literature actually converges on:

1. **Atomicity is a parameter, not a property.** Build for *recursive containment* — atoms inside atoms inside atoms, with the boundary chosen per use. Treat any flat single-layer "atomic notes" model as a UX preset, not a data-model constraint.

2. **Relations are first-class entities.** Typed, attributed, evidenced. This matches your intuition; it also matches property graphs, CiTO, nanopublications, and frame semantics. RDF-style untyped or bare-typed edges are too poor for research.

3. **Provenance binds meaning.** Frege's context principle, Quine's holism, and the nanopub model all say the same thing in different vocabularies: an atom out of context is meaningless. Every atom needs its origin (source, author, date, evidence) attached, not as decoration but as a constituent.

4. **Pluralize representation.** Carry both symbolic atoms (legible, composable) *and* embeddings (fuzzy, similarity-able) for every unit. The 2020s frontier is not one or the other — it is both, jointly.

5. **Three different atomicities, not one.** The unit of *cognition* (what a reader holds in mind), the unit of *publication* (what gets cited), and the unit of *argument* (what carries warrant) are not the same. A serious system distinguishes them and lets them coexist over the same content.

6. **Combination is where value lives.** Storage is free. The defensible part of any KM system is the operations: link suggestion, blending, analogy, contradiction-detection, comparison-tabulation. Build for those, not for "having captured."

7. **Atomicity is a discipline, not a discovery.** Luhmann's Zettelkasten worked because Luhmann *enforced* one idea per slip. Whatever your atom is, the system has to make it cheap to maintain the discipline — and cheap to *rewrite* the atom as understanding deepens.

You set out with a two-entity model: ideas and relations, each with attributes, each with functionality. The literature endorses this *as an engineering primitive* — Minsky's frames, property graphs, nanopublications, CiTO all run on it. The literature also warns: do not believe the primitive is metaphysically grounded; the atom is what you chose to call one, for the purpose you chose, at the level of abstraction you picked. Build the system to make those choices visible and revisable, and you will be on the side of the strongest tradition in 20th-century thought.

---

## Further reading, clustered

**Philosophical foundations**
- Locke, *An Essay Concerning Human Understanding* (1689) — Book II
- Frege, "On Sense and Reference" (1892)
- Wittgenstein, *Philosophical Investigations* (1953) — §65–67 on family resemblance
- Quine, "Two Dogmas of Empiricism" (1951)
- Brandom, *Making It Explicit* (1994) — chapter 1 is enough to get the inferentialism

**Cognitive science**
- Rosch, "Principles of Categorization" (1978)
- Fodor, *Concepts: Where Cognitive Science Went Wrong* (1998)
- Lakoff, *Women, Fire, and Dangerous Things* (1987) — the contra-Fodor case

**Knowledge representation**
- Minsky, "A Framework for Representing Knowledge" (1974)
- Sowa, *Conceptual Structures* (1984)
- Robinson, Webber & Eifrem, *Graph Databases* (2nd ed., O'Reilly) — the property-graph case
- Hogan et al., "Knowledge Graphs" (ACM Computing Surveys, 2021) — the canonical modern survey

**Library / linguistic units**
- Ranganathan, *Prolegomena to Library Classification* (1937)
- Wierzbicka & Goddard, *Words and Meanings* (2014) — NSM in practice
- Fillmore, "Frame Semantics" (1982)

**Note-taking and tools for thought**
- Ahrens, *How to Take Smart Notes* (2017)
- Matuschak, "Evergreen notes" — notes.andymatuschak.org/Evergreen_notes
- Matuschak & Nielsen, "How can we develop transformative tools for thought?" (2019) — numinous.productions/ttft

**Scholarly atomicity**
- Toulmin, *The Uses of Argument* (1958)
- Mons et al., "Nanopublications: a growing resource of provenance-centric scientific linked data" (IEEE eScience, 2018)
- Clark, Ciccarese, Goble, "Micropublications" (J. Biomedical Semantics, 2014)
- Auer et al., "Towards a Knowledge Graph for Science" (WIMS 2018) — ORKG
- Peroni & Shotton, "FaBiO and CiTO" — the SPAR ontologies (Journal of Web Semantics, 2012)

**Combination and creativity**
- Koestler, *The Act of Creation* (1964)
- Fauconnier & Turner, *The Way We Think* (2002)
- Hofstadter & Sander, *Surfaces and Essences* (2013)

**Philosophy of information**
- Floridi, *The Philosophy of Information* (2011) — especially the chapter on Levels of Abstraction
