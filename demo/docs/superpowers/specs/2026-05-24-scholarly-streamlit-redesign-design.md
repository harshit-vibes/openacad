# Scholarly-Flow Streamlit Redesign — Design Spec

**Date**: 2026-05-24
**Status**: Approved (brainstorming complete)
**Implements**: User goal "make the streamlit app much more presentable, as per the real workflow of a scholarly research" + session-scoped goal "run all the six scenarios as well so that we have a meaningful comparison of all the 6 approach."

## Context

The current Streamlit walkthrough (`app/walkthrough/*.py`) is functionally complete but feels engineer-coded:

- Page titles use demo vocabulary (Curate Atoms, Head-to-Head, Gold Test, Tune Prompts) rather than scholar verbs.
- The thesis claim is buried below the fold on the Welcome page.
- There is no global, persistent active-scenario picker — each page has its own redundant scenario selector widget.
- The page layouts lack consistent visual hierarchy: no shared hero zone, no shared "under the hood" pattern for the demo plumbing, no shared next/prev footer.
- The Drafted Notes scenario currently starts empty (no atoms), so a 6-way comparison is impossible — only 5 scenarios appear in any side-by-side run.
- Welcome dumps all 6 scenario cards, which is overwhelming before the viewer has a thesis frame to organize them around.

This spec re-skins and lightly re-narrates the walkthrough for a **demo audience** (locked viewer choice) doing a **20-30 minute deep dive** (locked length) framed as **"you, the researcher"** in second person (locked persona). The page count and underlying services do not change. No backend or scenario-mechanics changes.

## Locked decisions (from brainstorming)

| # | Decision | Value |
|---|----------|-------|
| 1 | Primary viewer | Demo audience watching a walkthrough |
| 2 | Demo length | 20-30 min deep dive — rich, every page can be poked |
| 3 | Redesign style | Narrate + polish (rewrite copy in scholar voice AND apply consistent visual polish) |
| 4 | Persona framing | Generic "you, the researcher" — second person throughout |
| 5 | Sidebar | Global active-scenario picker at top + thesis recap + live session counters |
| 6 | Welcome | Sharper thesis up top + concrete "what's in it for you" + single Start CTA |
| 7 | 6-way comparison | Drafted Notes auto-prepared during setup so all six scenarios run in head-to-head |

## Goals & non-goals

### Goals

1. Every page reads as a step in a researcher's workflow, not as a feature in a demo app.
2. Active scenario is a persistent sidebar control, set once, observed everywhere.
3. The thesis is visible on every page (sidebar recap).
4. The 6-way comparison actually runs across all six scenarios — Drafted Notes is no longer empty.
5. Each page follows a consistent 4-zone layout (hero / main / under-the-hood / nav-footer) so the visual rhythm stabilizes.

### Non-goals

- No backend/service/agent changes. (Services in `api/services/*.py` are untouched.)
- No new scenarios or new agent roles.
- No new pydantic-evals scorers.
- No login/auth/multi-user.
- No mobile responsiveness pass (desktop demo only).
- No persistence model changes (still per-scenario `state.sqlite` + shared chunks DB).
- No removal of the existing 10 pages — page count stays the same; titles + copy + layout change.

## Sidebar redesign

The sidebar replaces `st.navigation(...)` defaults with a custom layout. It contains, top to bottom:

1. **Brand block** — `⚛️ openacad` title + tagline.
2. **Active scenario picker** — single `st.selectbox` bound to `st.session_state["active_scenario_key"]`. Changing it triggers a `st.rerun()` so the current page re-renders against the new scenario. **Per-page `scenario_picker` widgets are removed** from every page; pages read `active_scenario()` directly.
3. **Thesis recap** — 3-4 line static markdown summarizing the four wins.
4. **Step navigation** — the existing `st.navigation` page groups, but with new section labels: Setup / Build / Use / Refine (replaces Setup / Build / Prove / Evolve).
5. **Session counters** — live count of papers, atoms, notes (rubrics), and head-to-head runs aggregated across all scenarios.

The brand + thesis + counters are rendered via `st.sidebar.*` calls in `streamlit_app.py` so they appear on every page automatically. The page navigation comes from `st.navigation(...)`.

## Page-by-page narration

| File (renamed) | Sidebar label | Hero blurb (second person) |
|----------------|---------------|----------------------------|
| `00_welcome.py` | 🏠 Welcome | "Your AI research assistant has 6 ways to remember your papers. Some are cheap and forgetful. Others are expensive and brilliant. Let's compare." |
| `10_library.py` | 📚 Your Library | "These are the papers your assistant will work with. Shared across every retrieval strategy." |
| `20_notes.py` | 📝 Read & Take Notes | "The AI proposes atomic notes from each paper. You accept, edit, or reject — your standards shape the vault." |
| `21_web.py` | 🕸️ Your Notes Web | "Your notes form a typed graph. Inspect what attributes and relationships have emerged." |
| `30_ask.py` | 🔎 Ask Your Library | "Ask any question. The active strategy retrieves the relevant material and answers with citations." |
| `31_compare.py` | ⚖️ Compare 6 Strategies | "Same question. Six different reading strategies. See which one your research actually needs." |
| `32_audit.py` | 🧪 Audit Quality | "A hand-graded test set. Every strategy answers the same questions; every answer gets scored." |
| `33_efficiency.py` | 📊 Efficiency Over Time | "Atom-curation costs more upfront. Over enough questions, you save. Here's where the lines cross." |
| `40_refine.py` | 🎚️ Refine Your Assistant | "Your ratings train the assistant. After enough feedback, it proposes a smarter prompt. You approve." |
| `90_conclusion.py` | 🎓 Conclusion | "Here's what your session produced and what you proved." |

Filenames change; the underlying logic of each page stays largely the same. The current `app/walkthrough/*.py` files are renamed in place (no new pages, no removed pages — Drafted Notes was the only "missing" surface and gets handled below via auto-prep, not a new page).

## Shared layout primitives

New helpers in `app/widgets.py`:

```python
def page_header(title: str, blurb: str, hero_metrics: list[tuple[str, str]] | None = None) -> None:
    """Top zone — page title + active-scenario chip + blurb + optional metric strip."""

def under_the_hood(label: str = "Show the agents + mechanism") -> "contextmanager":
    """Collapsible expander; content rendered inside is the 'demo plumbing'
    (agent boxes, current prompt versions, rubric counts) that lives below the
    scholar narrative."""

def nav_footer(prev_page: str | None, next_page: str | None,
               prev_label: str = "", next_label: str = "") -> None:
    """Consistent footer with Previous / Next CTAs. Pages pass the page module
    paths that st.navigation uses; st.switch_page handles transitions."""
```

Every page uses this skeleton:

```python
page_header(title="...", blurb="...", hero_metrics=[("Papers", "5"), ("Notes", "14")])

# ── main content ──
...

with under_the_hood():
    # show the agent boxes, prompt versions, rubric counts, etc.
    ...

nav_footer(prev_page="walkthrough/30_ask.py", next_page="walkthrough/32_audit.py",
           prev_label="Ask Your Library", next_label="Audit Quality")
```

The existing helpers (`rubric_input`, `answer_card`, `scenario_pill`, `status_chip`) stay; one helper is **removed**: `scenario_picker` — replaced by the global sidebar selector.

## Welcome page redesign

Replaces today's "thesis sentence + 6 scenario cards + recommended walkthrough list" with a tighter hook:

```
⚛️ openacad — atomic-notes lifecycle demo

Your AI research assistant has 6 ways to remember your papers.
Some are cheap and forgetful. Others are expensive and brilliant.
Most demos pick one. This one tries all six.

─── The thesis ───
✓ When AI memory is a scholar-curated atomic note, your assistant is:
✓ cheaper amortized
✓ more accurate with traceable citations
✓ deterministically under your control
✓ getting smarter with every rubric you submit

─── 1 → 4 agents as you climb ───
[6-column Streamlit row of bordered cards, each with the scenario's emoji+name
 as label and the agent count (1/1/1/2/3/4) as a large numeric value;
 implemented as `st.columns(6)` + `st.metric` per scenario]

─── In the next 20 minutes you will… ───
• Curate 5-10 notes from real UN SDG reports
• Ask a question across all 6 strategies
• Watch the cost curve cross over
• Train your assistant to write better atoms

[ ▶ Start: Your Library ]
```

The 6 scenario cards that used to dump on Welcome **move to Compare** (where they belong — as the things being compared).

## Auto-prepare all 3 atom-tier scenarios during setup

All three atom-tier scenarios (Drafted / Curated / Evolving) need atoms for the 6-way comparison to be meaningful. The differentiation between them is **acceptance policy**, not extraction policy — the same Haiku extraction pass feeds all three vaults, with different filters at accept time. Locked policy from sub-brainstorming:

| Scenario | Population policy |
|----------|-------------------|
| Drafted Notes | extract every chapter → auto-accept **all valid** drafts (noisy, dense, ~30-50 atoms) |
| Curated Notes | extract every chapter → auto-accept only drafts with `confidence_score ≥ 0.8` (cleaner, ~15-25 atoms) |
| Evolving Notes | mirror Curated Notes' atom set (the differentiation is runtime prompt evolution via the Meta-Evaluator, not extraction) |

This rule is implemented in `scripts/prepare_atom_scenarios.py` (already written this session). The script:

1. Wipes pre-existing atoms in all three atom-tier vaults (so the population is reproducible).
2. Runs extraction over every SDG chapter for Drafted + Curated (idempotent — skips sources whose drafts already exist).
3. Applies the per-scenario acceptance policy.
4. Mirrors Curated's resulting atom set into Evolving.

Library page wires this as the **"Prepare your assistant"** action:

1. **`10_library.py`** gets a new section: *"Prepare your assistant"* with two buttons:
   - **Quick prep** (default, recommended): invokes `scripts/prepare_atom_scenarios.py::main()` in-process; streams progress with `st.status`. Takes ~3-5 minutes total via the per-role Anthropic Haiku extractor.
   - **Skip** (advanced): leave atom-tier scenarios at whatever state they're in; head-to-head will run with fewer atoms.

2. **`31_compare.py`** (Compare 6 Strategies) defaults to all six scenarios pre-selected. If a scenario has no atoms, it is shown with a warning chip ("not prepared yet — go back to Library") and skipped, not silently dropped.

### Synthesis-prompt fix (required for atom-tier to honor paper restrictions)

The current `synthesis_agent.ask(paper_ids=...)` injects a `(restrict to sources: …)` line into the user prompt. For atom-tier scenarios this line backfires: the synthesis agent's tools (`query_atoms`, `traverse`, `semantic_search`, `get_atom_full`, `check_contradiction`) have no `source_id` filter, so the agent reads the restriction, can't honor it via tools, and gives up with "the vault contains no atoms from the specified source" even when matching atoms exist. The injection is removed; chunk-tier baselines already apply source filtering before calling the answerer, so they're unaffected.

## Per-page polish patterns (applied uniformly)

1. **Active-scenario chip** at the top of every page: a colored pill showing `⚛️ Curated Notes (3 agents)` so the viewer always knows which scenario the page is talking about.
2. **Hero metric strip** for pages with clear top-line numbers: Library shows papers/chunks, Notes shows draft/accepted counts, Compare shows tokens-saved, Efficiency shows break-even N, Audit shows accuracy.
3. **Under-the-hood expanders** keep the demo plumbing accessible but un-intrusive: which agent versions are active, which prompts they're using, rubric tallies. The scholar narrative reads cleanly; the curious can open the drawer.
4. **Bordered containers** for every distinct unit (each note, each comparison row, each agent box) so the visual rhythm is consistent.
5. **Consistent CTA hierarchy**: primary button = the next thing the viewer should do; secondary = poke around; tertiary = navigate elsewhere.

## Conclusion page redesign

Stays similar to today's structure (session totals + per-scenario breakdown + 8 wins + next-steps), but copy is rewritten in second person and the "wins" section is reframed as **what your session proved**, not what the demo proves. Numbers come from the live SQLite state per scenario.

## Implementation order

1. Sidebar layout helpers in `app/streamlit_app.py` (global picker + thesis + counters).
2. Shared widget primitives in `app/widgets.py` (`page_header`, `under_the_hood`, `nav_footer`); remove `scenario_picker`.
3. Welcome page rewrite (`00_welcome.py` — replaces today's content).
4. Library page rewrite (`10_library.py` — adds Prepare-your-assistant section that auto-preps Drafted Notes).
5. Iterate through remaining pages (`20_notes.py`, `21_web.py`, `30_ask.py`, `31_compare.py`, `32_audit.py`, `33_efficiency.py`, `40_refine.py`, `90_conclusion.py`) — rename where filename changes, then on every page: apply layout primitives, rewrite copy in second person, swap removed `scenario_picker` calls for reads of `active_scenario()`. No service changes.
6. Update `app/streamlit_app.py`'s `st.navigation(...)` mapping to use the new file paths + section labels.
7. Update `tests/test_streamlit_pages.py` to reference the new filenames.
8. **Run the goal verification**: boot the app, hit Library → Prepare → wait for Drafted Notes to populate, hit Compare → run a 6-way head-to-head against a SDG question. Assert all six scenarios produced a non-empty answer with token counts.

## Files affected

### Renamed (10)

| Current | New |
|---------|-----|
| `app/walkthrough/00_welcome.py` | `app/walkthrough/00_welcome.py` (content rewritten) |
| `app/walkthrough/10_papers.py` | `app/walkthrough/10_library.py` |
| `app/walkthrough/20_curate.py` | `app/walkthrough/20_notes.py` |
| `app/walkthrough/21_inspect.py` | `app/walkthrough/21_web.py` |
| `app/walkthrough/30_ask.py` | `app/walkthrough/30_ask.py` (content rewritten) |
| `app/walkthrough/31_head_to_head.py` | `app/walkthrough/31_compare.py` |
| `app/walkthrough/32_gold_test.py` | `app/walkthrough/32_audit.py` |
| `app/walkthrough/33_cost_curve.py` | `app/walkthrough/33_efficiency.py` |
| `app/walkthrough/40_tune.py` | `app/walkthrough/40_refine.py` |
| `app/walkthrough/90_conclusion.py` | `app/walkthrough/90_conclusion.py` (content rewritten) |

### Modified

- `app/streamlit_app.py` — new sidebar layout (brand, scenario picker, thesis, counters) + updated `st.navigation` mapping with new file paths + new section labels.
- `app/widgets.py` — add `page_header`, `under_the_hood`, `nav_footer`; remove `scenario_picker`.
- `tests/test_streamlit_pages.py` — reference new filenames.
- `README.md` and `app/README.md` (if it exists) — reflect new page names in the walkthrough description.

### Not modified

- `api/services/*.py` (all backend services unchanged).
- `api/scenarios.py` (scenario definitions unchanged).
- `api/models/*.py` (data models unchanged).
- `scripts/*.py` (seed/eval scripts unchanged).
- `cli/main.py` (Typer commands unchanged).
- All tests except `test_streamlit_pages.py` (e2e backend tests unchanged).

## Verification

After implementation:

1. **Boot**: `make app` brings up Streamlit; the sidebar shows brand + global scenario picker + thesis recap + step navigation grouped into Setup/Build/Use/Refine + live session counters.
2. **Welcome**: lands on the new tight hook; clicking ▶ Start jumps to Your Library.
3. **Library**: shows the 5 ingested PDFs; "Prepare your assistant" section visible with Quick-prep button. Clicking it streams extraction progress for Drafted Notes; on completion the session counter for atoms across all scenarios goes up by ~30-60.
4. **Global scenario picker**: changing the sidebar selectbox from Curated Notes to Cold Read immediately re-renders the current page against Cold Read — the active-scenario chip updates.
5. **Compare 6 Strategies**: all six scenarios pre-selected by default. Hit Run on the default question — all six produce non-empty answers. The result table shows 6 rows; the "win matrix" highlights the cheapest, most-cited, and (if a gold dataset row matches) most accurate.
6. **Every page**: hero zone + main + under-the-hood expander + nav footer present, in that order.
7. **`make test`**: all existing tests pass; `test_streamlit_pages.py` page-list assertion updated for the new filenames.
8. **Goal hook satisfied**: a 6-way Compare run on the default question completes with all six scenarios producing answers and metrics — proves "meaningful comparison of all 6 approaches."

## Open questions (intentionally none)

All design decisions were locked during brainstorming. The implementation plan derived from this spec should not need to revisit:
- viewer (demo audience)
- length (20-30 min)
- style (narrate + polish)
- persona (second person)
- structure (10 pages, renamed + rewritten, no add/remove)
- sidebar (global scenario picker + thesis + counters)
- 6-way comparison (auto-prep Drafted Notes during Library)
