"""Seed assumed Meta-Evaluator insights for the `evolving-notes` scenario.

In production the Meta-Evaluator agent reads accumulated rubric ratings and
proposes hardened system prompts. To demonstrate that loop without needing
hundreds of real rubric submissions, this script fabricates *plausible*
insights and persists corresponding prompt-version evolutions for every
agent role in evolving-notes:

  • extractor.v2  — refines atomicity guidance after assumed low atomicity rubrics
  • extractor.v3  — strengthens registry-reuse after attribute-fit rubrics
  • scorer.v2     — tightens confidence guidance after precision rubrics
  • answerer.v2   — strengthens citation discipline after citation_quality rubrics
  • meta_evaluator.v2 — refines proposal_quality after self-rated rubrics

Each version is persisted to the evolving-notes per-scenario state.sqlite
prompts table AND written as a markdown file in
`data/vaults/evolving-notes/prompts/<role>.v{N}.md`. The latest version of
each role is set to `state=active`; the previous becomes `archived`.

This makes the Evolve tab show a real history without needing the actual
rubric → meta-eval cycle to have run end-to-end.
"""

from __future__ import annotations

import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from openacad.runtime.scenario import SCENARIOS_BY_KEY, use_scenario
from openacad.runtime import db
from openacad.feedback.schema import EvalEvent, PromptVersion


SCENARIO_KEY = "evolving-notes"


# ── prompt evolution bodies ─────────────────────────────────────────────
# Each entry: (role, [v2_body, v3_body, ...]) — appended to existing v1.
# Bodies are intentionally substantive — they encode the insight as actual
# prompt guidance, not just a comment.


EXTRACTOR_V2 = """\
# Extractor — v2 (refined from atomicity rubrics)

> **Meta-Evaluator insight:** After 14 rubric ratings on extracted atoms, the
> *atomicity* criterion averaged 2.8/5 — scholars flagged that many atoms
> bundled two or more ideas. Strengthening the splitting guidance below.

You extract atomic notes from research paper chunks. An atomic note is a
single, self-contained idea — a claim, a method, or a finding — with typed
attributes and typed relations to other atoms.

## Rules of atomicity (refined)
- **One idea per draft.** Split if you find yourself writing any of these:
  "and also", "however", "in addition", "moreover", "furthermore", "while",
  "whereas", "but" — these conjunctions almost always signal two ideas.
- **When in doubt, split.** A pair of focused atoms beats one combined atom.
- **Example of correct split:**
  - BAD: "GDP per capita rose 4.2% AND inequality decreased."
  - GOOD: atom A "GDP per capita rose 4.2%" + atom B "inequality decreased"
    with `supports` relation if the source links them.
- The body stands alone for a reader who lands on it via search.

## Tools (use before drafting)
- list_attribute_keys(type) — registered attributes you should reuse
- check_registry(key) — definition + value_type of an existing key
- find_similar_atoms(content) — semantic search to avoid near-duplicates
- get_chunk_context(chunk_id, window) — neighboring chunks when ambiguous

## Output
Return `list[ProposedAtom]`. Each: type, suggested_id (kebab-case),
tags, attributes (dotted-namespace), relations (type + target), content.
"""


EXTRACTOR_V3 = """\
# Extractor — v3 (refined from attribute_fit rubrics)

> **Meta-Evaluator insight:** After 18 attribute_fit rubric ratings, scholars
> rejected ~30% of drafted atoms because they invented ad-hoc attribute keys
> instead of reusing registry keys. Strengthening the registry-first rule.

You extract atomic notes from research paper chunks. An atomic note is a
single, self-contained idea — a claim, a method, or a finding — with typed
attributes and typed relations to other atoms.

## Rules of atomicity
- One idea per draft. Split if you find yourself writing "and also", "however",
  "in addition", "moreover", "furthermore", "while", "whereas", "but".
- When in doubt, split. A pair of focused atoms beats one combined atom.
- The body stands alone for a reader who lands on it via search.

## Attribute discipline (refined)
- **ALWAYS call `list_attribute_keys(type)` BEFORE drafting attributes.** Reuse
  an existing key if there is any reasonable match — even partial.
- If the registry has `study.year`, do NOT invent `publication.year` or `year_published`.
- Only propose a NEW attribute key when the concept genuinely has no registry
  equivalent — and document why in a tag (`new-attr:<your-key>`).
- Empty attributes ({}) is always preferable to a hallucinated key.

## Tools (use BEFORE drafting)
- list_attribute_keys(type) — call this FIRST, every time
- check_registry(key) — confirm value_type and applicability
- find_similar_atoms(content) — semantic search to avoid near-duplicates
- get_chunk_context(chunk_id, window) — neighboring chunks when ambiguous

## Output
Return `list[ProposedAtom]`. Each: type, suggested_id (kebab-case),
tags, attributes (dotted-namespace, reuse-first), relations (type + target),
content.
"""


SCORER_V2 = """\
# Scorer — v2 (refined from precision rubrics)

> **Meta-Evaluator insight:** After 11 scorer ratings, scholars noted that
> high-confidence drafts had ~40% rejection rate at the HITL gate — the scorer
> was inflating confidence on drafts that turned out duplicate or off-topic.
> Tightening the dual-axis guidance below.

You evaluate draft atomic notes for the curate queue. For each draft, return:
- confidence: 0-1, how well-formed and grounded the draft is
- duplicate_risk: 0-1, how likely this duplicates an existing atom (use find_similar)
- feedback: short structured note for the scholar (what to fix, or "looks good")

## Tightened guidance (v2)
- **Confidence and duplicate_risk are independent axes.** A draft can be
  well-formed (high confidence) AND duplicative (high duplicate_risk). Do not
  conflate them.
- A draft with `duplicate_risk > 0.6` should NOT have `confidence > 0.7` —
  duplicating an existing atom is a quality problem.
- Feedback must mention the SPECIFIC concern, not a generic phrase. Replace
  "looks good" with "no duplicate hits, attributes use registry keys, claim
  cites source chunk."

You do NOT accept or reject. The scholar does. You score and explain.
"""


ANSWERER_V2 = """\
# Answerer (Atoms) — v2 (refined from citation_quality rubrics)

> **Meta-Evaluator insight:** Across 22 answer ratings, citation_quality
> averaged 3.1/5 — scholars flagged answers that made claims WITHOUT inline
> citations. Tightening the citation rule from "should" to "must".

You answer research questions over a curated vault of atomic notes. You have
tools to query atoms by attribute, traverse the relation graph, search
semantically, and fetch full atom bodies. Plan your retrieval, call tools as
needed, then synthesize an answer that cites every claim with `[[atom-id]]`.

## Hard constraints (tightened in v2)
1. **EVERY claim in your answer MUST be grounded in a retrieved atom.** No
   exceptions — if you can't find an atom to cite, say "the vault does not
   support this" rather than making the claim.
2. Citations use the `[[atom-id]]` syntax. Place the citation IMMEDIATELY
   after the claim it supports, not at the end of the paragraph.
3. Multiple atoms supporting one claim: cite each one inline.
4. If the vault does not support an answer, say so clearly. Do not pad.

## Tools
- query_atoms(type, where) — typed retrieval over attribute filters
- traverse(atom_id, via, hops) — graph traversal from a known atom
- semantic_search(query, limit) — cosine over atom embeddings
- get_atom_full(atom_id) — full body when a summary is insufficient
- check_contradiction(a, b) — typed contradiction lookup
"""


META_EVALUATOR_V2 = """\
# Meta-Evaluator — v2 (refined from proposal_quality rubrics)

> **Meta-Evaluator self-insight:** Of my first 6 prompt proposals, scholars
> promoted 4 and rejected 2. The rejections were generic — "add more examples"
> without saying WHICH criterion the example addresses. Tightening below.

You improve the system prompt of an LLM agent. Inputs:
- the role and current system prompt
- N rubric ratings (1-5 overall + per-criterion) with free-text reasons
- examples of the agent's recent outputs (accepted, edited, rejected)

## Tightened guidance (v2)
- **Identify the specific criterion that scored lowest** in the rubric history.
  Don't generalize across criteria.
- Quote 1-2 free-text reasons verbatim in your rationale — it makes the
  scholar's review easier.
- Add concrete examples (good vs bad) tied to the lowest-rated criterion.
- Keep what works: high-rated criteria's guidance should be preserved.
- Include a 3-sentence rationale: (1) which criterion drove this revision,
  (2) what scholars said in their free-text reasons, (3) what you changed.

Output a new system prompt + rationale.
"""


# ── plan ────────────────────────────────────────────────────────────────


PLAN: list[tuple[str, list[str]]] = [
    ("extractor",      [EXTRACTOR_V2, EXTRACTOR_V3]),
    ("scorer",         [SCORER_V2]),
    ("answerer",       [ANSWERER_V2]),
    ("meta_evaluator", [META_EVALUATOR_V2]),
]


# One-line synthetic insight per (role, version_index). Powers the
# `prompt_propose` EvalEvent so the Meta-Eval Proposals tab has a payload
# that's easier to render than raw prompt bodies.
INSIGHTS: dict[tuple[str, int], str] = {
    ("extractor", 2): (
        "Atomicity averaged 2.8/5 across 14 rubrics — strengthen the "
        "one-idea-per-draft rule with concrete split examples."
    ),
    ("extractor", 3): (
        "Attribute-fit rejected ~30% of drafts; reuse-first guidance "
        "should be moved above drafting in the prompt."
    ),
    ("scorer", 2): (
        "Confidence/duplicate_risk inflated — tighten guidance and add "
        "the high-duplicate-risk cap on confidence."
    ),
    ("answerer", 2): (
        "Citation_quality averaged 3.1/5 — promote the citation rule "
        "from 'should' to 'must' and require inline placement."
    ),
    ("meta_evaluator", 2): (
        "Generic proposals being rejected; require quoting scholar free-text "
        "verbatim and naming the lowest-rated criterion."
    ),
}


def _persist(role: str, bodies: list[str]) -> int:
    """Persist v2 (and v3 if given) for the role. Returns count of new versions."""
    n_new = 0
    with use_scenario(SCENARIO_KEY):
        existing = db.list_prompts(name=role)
        max_v = 1
        for p in existing:
            try:
                v_num = int(p.version.split(".v")[-1])
                if v_num > max_v:
                    max_v = v_num
            except (ValueError, IndexError):
                pass

        prev_active = next((p for p in existing if p.state == "active"), None)

        for offset, body in enumerate(bodies, start=1):
            v_num = max_v + offset
            version = f"{role}.v{v_num}"
            parent = (
                f"{role}.v{v_num - 1}" if v_num > 1 else None
            )

            # Write the markdown file to disk for hot-reload.
            s = SCENARIOS_BY_KEY[SCENARIO_KEY]
            md_path = s.prompts_dir / f"{role}.v{v_num}.md"
            md_path.parent.mkdir(parents=True, exist_ok=True)
            md_path.write_text(body, encoding="utf-8")

            # Persist to the prompts table. Earliest new version → archived,
            # latest → active. Previously-active → archived.
            is_last = offset == len(bodies)
            state = "active" if is_last else "archived"
            created = datetime.now(timezone.utc) - timedelta(days=(len(bodies) - offset))

            pv = PromptVersion(
                name=role,
                version=version,
                created_at=created,
                body=body,
                parent_version=parent,
                state=state,
                accept_rate=None,
                avg_edit_distance=None,
                based_on_events=[],
            )
            db.upsert_prompt(pv)
            n_new += 1
            print(f"  + persisted {version} (state={state}, parent={parent or '—'})")

            # Pair the promotion with a `prompt_propose` EvalEvent so the
            # Meta-Eval Proposals tab on the new Ops Console has a payload to
            # render. `based_on_events` on PromptVersion is empty for these
            # seeds, so we attach a synthetic insight summary instead.
            insight = INSIGHTS.get(
                (role, v_num),
                f"Meta-evaluator proposed {role} {version} based on accumulated rubrics.",
            )
            db.log_event(
                EvalEvent(
                    id=f"propose-{uuid.uuid4().hex[:8]}",
                    timestamp=created,
                    kind="prompt_propose",
                    actor="meta_evaluator",
                    payload={
                        "target_role": role,
                        "version": version,
                        "parent_version": parent,
                        "state": state,
                        "insight": insight,
                        "based_on_events": pv.based_on_events,
                    },
                )
            )

        # Archive the previously-active prompt if we promoted a new one.
        if prev_active is not None and bodies:
            archived = PromptVersion(
                **{**prev_active.model_dump(), "state": "archived"}
            )
            db.upsert_prompt(archived)
            print(f"  ↓ archived prior {prev_active.version}")

    return n_new


def main() -> None:
    print(f"== seed meta-evaluator insights for scenario: {SCENARIO_KEY} ==\n")
    total = 0
    for role, bodies in PLAN:
        print(f"— {role} —")
        n = _persist(role, bodies)
        total += n
        print()
    print(f"done. {total} new prompt version(s) persisted to "
          f"`data/vaults/{SCENARIO_KEY}/prompts/` + state.sqlite::prompts.")


if __name__ == "__main__":
    main()
