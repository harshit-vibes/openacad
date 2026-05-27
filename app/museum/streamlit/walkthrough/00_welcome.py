"""Welcome — elaborated thesis, capability-ladder visual, journey overview."""

from __future__ import annotations

import sys
from pathlib import Path

DEMO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(DEMO_ROOT) not in sys.path:
    sys.path.insert(0, str(DEMO_ROOT))

import streamlit as st

from openacad.runtime.scenario import SCENARIOS, Tier


TIER_EMOJI = {Tier.COLD: "🥶", Tier.CHUNK: "🧩", Tier.ATOMS: "⚛️"}


# ── hero ────────────────────────────────────────────────────────────────


st.title("⚛️ openacad — a scholarly research AI agent harness")

st.markdown(
    f"""
Your AI research assistant has **{len(SCENARIOS)} different ways to remember your papers**.
Each rung adds **exactly one capability** on top of the previous one. Some rungs
are cheap and forgetful. Others are expensive and brilliant. **This demo walks
through all {len(SCENARIOS)} of them** — and shows you why the capability layering
matters more than the technology pick.
"""
)


# ── the problem ─────────────────────────────────────────────────────────


st.markdown("## The problem")

st.markdown(
    """
You drop a stack of research papers into an AI tool. You ask a question. You get an
answer. **But how did the AI remember those papers?** That choice — invisible to
you — determines everything downstream:

- 💸 What you pay per query (and per million queries)
- 🎯 Whether the answer cites a real source or makes one up
- 🎮 Whether *you* can audit, edit, or override what the AI "knows"
- 🧬 Whether the system gets *better* the longer you use it, or stays the same forever

Every retrieval-augmented system on the market today picks **one** strategy and
hides the rest from you. Most pick a strategy optimized for the demo, not for the
research workflow. The result: most AI research openacad are excellent at *looking*
helpful and mediocre at being it.
"""
)


# ── the thesis ──────────────────────────────────────────────────────────


st.markdown("## The thesis")

st.markdown(
    """
When the **unit of AI memory** is a **scholar-curated atomic note** — not a chunk,
not the whole PDF, not an embedding — your assistant flips on four dimensions at once:
"""
)

c1, c2 = st.columns(2)
with c1:
    with st.container(border=True):
        st.markdown(
            """
            ### 💰 Cheaper amortized

            Chunk-RAG pays the same token bill on every query — there's no memory,
            just retrieval. **Atom-RAG** pays an upfront cost (extraction + your
            curation) once per paper, then issues compact tool calls against
            high-information atoms. The slope flattens. Over a real research
            workload, you save.
            """
        )
    with st.container(border=True):
        st.markdown(
            """
            ### 🎯 Accurate with traceable citations

            Chunk citations point at "pages 4-7" of a PDF. **Atom citations**
            point at a specific claim you approved, with provenance back to the
            exact chunks it came from. Every assertion in the answer ties to a
            specific atom you can open, edit, or reject.
            """
        )
with c2:
    with st.container(border=True):
        st.markdown(
            """
            ### 🎮 Deterministically controllable

            In RAG systems, the LLM decides what to remember based on whatever
            embedding model + chunker the vendor picked. **In atom-RAG, you decide.**
            Every committed atom traces to a scholar accept-action in the event
            log. The LLM never writes to your vault. Nothing in your memory got
            there without your fingerprint on it.
            """
        )
    with st.container(border=True):
        st.markdown(
            """
            ### 🧬 Getting smarter with every rubric

            RAG systems don't learn — they retrieve. **Atom-RAG with a
            Meta-Evaluator does:** every rubric you submit feeds an eval log;
            after a threshold, an agent proposes a hardened version of the
            extraction or synthesis prompt; you approve it; the system gets
            better. **Your assistant's instructions earn their sophistication;
            the notes you approved stay exactly as you approved them.**
            """
        )


# ── plus structural wins ────────────────────────────────────────────────


st.markdown("### Plus four structural wins no chunk-RAG can match")

st.markdown(
    """
| Win | Why only atoms get it |
|-----|----------------------|
| 🧱 **Composable** | Typed attribute filters + graph traversal + semantic + keyword compose into queries chunk-RAG can't express ("claims in NLP that contradict empirical findings") |
| ♻️ **Reusable** | Each atom outlives the question that produced it. Tomorrow's query recombines yesterday's atoms in a new shape |
| 🔍 **Auditable** | Answer cites atom → atom cites chunk → chunk cites page. Every claim is traceable down to the original PDF location |
| 🔬 **Inspectable** | Browse the typed registry, edit constraints, watch the schema evolve. The mechanism is open; nothing is opaque |
"""
)


# ── capability ladder — one rung per scenario, one new capability per rung ─


st.markdown(f"## The {len(SCENARIOS)}-rung capability ladder")

st.markdown(
    """
The demo walks you through nine retrieval strategies, ordered from least to most
sophisticated. **Each rung adds exactly one capability** on top of the previous —
random chunking → keyword search → semantic embeddings → atomic chunks → +typed
attributes → +graph relations → +atom embeddings → +HITL curation → +self-improving
agent instructions.

Sophistication isn't free; it costs in moving parts. The cards below show how many
agents are wired in at each rung.
"""
)


# Capability added at each rung — derived from flag deltas, not hardcoded.
def _delta_label(prev, curr) -> str:
    if prev is None:
        if curr.tier == Tier.COLD:
            return "RAG on full doc"
        if curr.tier == Tier.CHUNK:
            return "random chunks + keyword"
    if curr.tier == Tier.CHUNK and prev is not None and prev.tier == Tier.COLD:
        return "+ random chunking + keyword"
    if curr.tier == Tier.CHUNK and prev is not None and prev.tier == Tier.CHUNK:
        return "+ semantic embeddings"
    if curr.tier == Tier.ATOMS:
        if prev is None or prev.tier != Tier.ATOMS:
            return "+ atomic chunking"
        if not prev.has_attributes and curr.has_attributes:
            return "+ typed attributes"
        if not prev.has_relations and curr.has_relations:
            return "+ graph relations"
        if not prev.has_atom_embeddings and curr.has_atom_embeddings:
            return "+ atom embeddings"
        if not prev.has_curation and curr.has_curation:
            return "+ HITL curation"
        if not prev.has_meta_eval and curr.has_meta_eval:
            return "+ self-improving"
    return curr.name


# Render as 3 rows × 3 columns to avoid cramping on a 9-wide grid.
prev = None
rungs_per_row = 3
for row_start in range(0, len(SCENARIOS), rungs_per_row):
    row = SCENARIOS[row_start : row_start + rungs_per_row]
    cols = st.columns(rungs_per_row)
    for col, s in zip(cols, row):
        n_agents = len(s.agents)
        delta = _delta_label(prev, s)
        with col:
            with st.container(border=True):
                st.markdown(
                    f"<div style='text-align:center; font-size:0.75em; color:#888;'>"
                    f"rung {row_start + row.index(s) + 1}</div>"
                    f"<div style='text-align:center; font-size:1.0em; font-weight:600;'>"
                    f"{TIER_EMOJI[s.tier]} {s.name}</div>"
                    f"<div style='text-align:center; font-size:0.85em; color:#aaa; margin-top:4px;'>"
                    f"{delta}</div>"
                    f"<div style='text-align:center; font-size:1.4em; font-weight:700; margin-top:6px;'>"
                    f"{n_agents} agent{'s' if n_agents != 1 else ''}</div>",
                    unsafe_allow_html=True,
                )
        prev = s


# ── what's in it for you ────────────────────────────────────────────────


st.markdown("## In the next 20 minutes you will…")

st.markdown(
    """
Pick a scenario in the sidebar — its steps light up. Atom-tier scenarios show
more steps because they have more to do; chunk-tier and Cold Read are leaner.

1. 📚 Look at **5 UN SDG briefing chapters** that ship as bundled raw material
2. 📝 Watch the AI propose atomic notes; **accept, edit, or reject** each one *(curated scenarios)*
3. 🕸️ Inspect **the typed graph** that emerges — attributes, relations, schema *(atom-tier)*
4. 🔎 **Ask a question** of the active strategy; see its answer + citations
5. 🧪 Run a **gold-graded audit** with pydantic-evals scorers *(atom-tier)*
6. 🎚️ **Refine your assistant** — let the Meta-Evaluator harden your prompts *(Self-Improving only)*
7. 🎓 Hit **Conclusion** — same question across every strategy, the **cost & performance table**, the **cumulative cost curve**, and why the Self-Improving Assistant is the destination
"""
)


st.info(
    "💡 **Start anywhere** — the sidebar lets you jump to any step. Or hit ▶ Start "
    "below to follow the recommended walkthrough order.",
    icon="📌",
)


# ── single Start CTA ────────────────────────────────────────────────────


st.markdown("---")
cols = st.columns([3, 1])
with cols[1]:
    if st.button("▶ Start: Your Library", type="primary", use_container_width=True):
        st.switch_page("walkthrough/10_papers.py")
