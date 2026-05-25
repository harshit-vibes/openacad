"""Per-scenario page template — the 4-or-5 standard tabs.

Each of the 9 scenarios has a thin Streamlit page that calls
`render_scenario(scenario_key)` from here. The template is capability-aware:
the Evolve tab only shows when `has_curation` or `has_meta_eval`; sub-sections
within other tabs adapt to the scenario's flags (atoms vs chunks vs cold).

Tab narrative: KNOW → DO → PROVE
  1. About    — lineage visuals, capability flags, agent definitions,
                + what's in this scenario's vault right now
  2. Build    — produce notes / inspect chunks
  3. Query    — ask a question; see cited units; past-query history
  4. Evolve   — HITL queue + prompt versions (capability-gated)
  5. Results  — Δ vs the previous rung + signature metric + per-question table
"""

from __future__ import annotations

import sys
import uuid
import json
from datetime import datetime, timezone
from pathlib import Path

import streamlit as st

from openacad.runtime.scenario import (
    SCENARIOS, SCENARIOS_BY_KEY, AgentRole, Tier, Scenario, use_scenario
)
from openacad.runtime import db, dispatcher
from openacad.notes.persistence import vault as vault_io
from openacad.feedback import timeline


TIER_EMOJI = {Tier.COLD: "🥶", Tier.CHUNK: "🧩", Tier.ATOMS: "⚛️"}
ROLE_EMOJI = {
    AgentRole.ANSWERER: "💬",
    AgentRole.EXTRACTOR: "🪓",
    AgentRole.SCORER: "🎯",
    AgentRole.META_EVAL: "🧬",
}

# Scenario-aware agent tool surface. Each agent's tool list depends on the
# active scenario's capability flags — e.g. `traverse` only works if the
# scenario has relations; `semantic_search` only if atom embeddings exist.
# The agent.py code gates these tools (some scenarios just never call them);
# we mirror that gating here so the About tab tells the truth.

def _agent_tools_for(role: AgentRole, s: Scenario) -> list[tuple[str, str]]:
    """Tools available to `role` IN scenario `s`. Returns (signature, purpose) pairs."""
    if role == AgentRole.EXTRACTOR:
        if not s.has_extraction:
            return []
        tools = [
            ("get_chunk_context(chunk_id, window)", "fetch neighboring chunks when ambiguous"),
        ]
        if s.has_attributes:
            tools.extend([
                ("list_attribute_keys(type)", "registered attribute keys to reuse"),
                ("check_registry(key)", "fetch attribute definition + value_type"),
            ])
        if s.has_atom_embeddings:
            tools.append(
                ("find_similar_atoms(content)", "semantic dup-check against existing atoms")
            )
        return tools

    if role == AgentRole.ANSWERER:
        if s.tier in (Tier.COLD, Tier.CHUNK):
            return []  # context-injection answerers don't expose tools
        # Atom-tier
        tools = [
            ("get_atom_full(atom_id)", "fetch full body when summary insufficient"),
        ]
        if s.has_attributes:
            tools.append(
                ("query_atoms(type, where)", "typed attribute filter over atoms")
            )
        else:
            tools.append(
                ("query_atoms(type)", "filter atoms by type (no attribute filter at this rung)")
            )
        if s.has_relations:
            tools.extend([
                ("traverse(atom_id, via, hops)", "follow typed relations from a known atom"),
                ("check_contradiction(a, b)", "typed contradiction lookup over the graph"),
            ])
        if s.has_atom_embeddings:
            tools.append(
                ("semantic_search(query, limit)", "MiniLM cosine over atom embeddings")
            )
        return tools

    # SCORER / META_EVAL: structured output, no tools
    return []


def _capability_pills_html(s: Scenario) -> str:
    """Render the 6 capability flags as inline pills (✓ on, ✗ off)."""
    flags = [
        ("extraction", s.has_extraction, "extractor drafts atoms from chunks"),
        ("curation", s.has_curation, "HITL accept/edit/reject gate"),
        ("meta-eval", s.has_meta_eval, "Meta-Evaluator hardens prompts"),
        ("attrs", s.has_attributes, "atoms carry typed attributes"),
        ("rels", s.has_relations, "atoms link via typed relations"),
        ("embeds", s.has_atom_embeddings, "MiniLM vectors on atoms"),
    ]
    parts = []
    for name, on, tip in flags:
        if on:
            bg, fg, mark = "#1a3a1a", "#7ed87e", "✓"
        else:
            bg, fg, mark = "#2a2a2a", "#666", "✗"
        parts.append(
            f"<span title='{tip}' "
            f"style='display:inline-block; background:{bg}; color:{fg}; "
            f"border-radius:14px; padding:3px 12px; margin:2px 4px 2px 0; "
            f"font-size:0.85em; font-family:monospace;'>"
            f"<b>{mark}</b> {name}</span>"
        )
    return "<div style='margin:6px 0 12px 0;'>" + "".join(parts) + "</div>"


def _fmt_attrs_short(attrs: dict) -> str:
    """Compact, table-friendly attribute summary: 'k=v, k=v'  (cap at 80 chars)."""
    if not attrs:
        return "—"
    pieces = [f"{k}={v}" for k, v in list(attrs.items())[:3]]
    out = ", ".join(pieces)
    if len(attrs) > 3:
        out += f" (+{len(attrs) - 3} more)"
    return out[:80]


def _fmt_rels_short(rels) -> str:
    """Compact relations summary: 'supports atom-id-1; contradicts atom-id-2'."""
    if not rels:
        return "—"
    pieces = [f"{r.type} {r.target}" for r in list(rels)[:2]]
    out = "; ".join(pieces)
    if len(rels) > 2:
        out += f" (+{len(rels) - 2} more)"
    return out[:80]


def _agent_output_for(role: AgentRole, s: Scenario) -> str:
    """Pydantic output type the agent returns, scenario-aware."""
    if role == AgentRole.ANSWERER:
        if s.tier == Tier.ATOMS:
            return "SynthesisResult (answer + cited atom ids)"
        return "str (raw answer with inline chunk-id / page-range citations)"
    return {
        AgentRole.EXTRACTOR: "list[ProposedAtom]",
        AgentRole.SCORER: "ScorerOutput(confidence: float, duplicate_risk: float, feedback: str)",
        AgentRole.META_EVAL: "MetaProposal(new_body: str, rationale: str)",
    }.get(role, "—")

# Which LLM role each agent uses (drives model selection via openacad.runtime.llm).
AGENT_LLM_ROLE: dict[AgentRole, str] = {
    AgentRole.EXTRACTOR: "extraction",
    AgentRole.SCORER: "extraction",
    AgentRole.META_EVAL: "synthesis",
    AgentRole.ANSWERER: "synthesis",
}


def render_scenario(scenario_key: str) -> None:
    """Top-level entry point. Renders the 7 standard tabs for a scenario."""
    s = SCENARIOS_BY_KEY[scenario_key]
    rung_index = next(i for i, sc in enumerate(SCENARIOS) if sc.key == scenario_key) + 1

    # Sync ContextVar so every page-level service call sees this scenario.
    st.session_state["active_scenario_key"] = scenario_key
    from openacad.runtime.scenario import _active
    _active.set(scenario_key)

    # ── hero ────────────────────────────────────────────────────────────
    cols = st.columns([1, 4])
    with cols[0]:
        st.markdown(
            f"<div style='font-size:3em; text-align:center; line-height:1;'>{TIER_EMOJI[s.tier]}</div>"
            f"<div style='text-align:center; color:#888; font-size:0.85em;'>rung {rung_index} / {len(SCENARIOS)}</div>",
            unsafe_allow_html=True,
        )
    with cols[1]:
        st.title(s.name)
        st.markdown(f"_{s.description}_")

    # ── tab list (capability-gated) ─────────────────────────────────────
    # Scenario-unique only. Cross-scenario aggregation lives on the
    # Conclusion page; the per-scenario tabs intentionally don't repeat it.
    # About now includes the vault-contents view (formerly the Anatomy tab).
    tab_names = ["📖 About", "🛠️ Build", "🔎 Query"]
    show_evolve = s.has_curation or s.has_meta_eval
    if show_evolve:
        tab_names.append("🎚️ Evolve")
    tab_names.append("📊 Results")

    tabs = st.tabs(tab_names)
    idx = 0
    with tabs[idx]: _tab_about(s, rung_index); idx += 1
    with tabs[idx]: _tab_build(s); idx += 1
    with tabs[idx]: _tab_query(s); idx += 1
    if show_evolve:
        with tabs[idx]: _tab_evolve(s); idx += 1
    with tabs[idx]: _tab_results(s); idx += 1


# ── Lineage visuals — one per evolution axis (chunks + agents) ──────────


# Chunk evolution: what the unit of memory IS at each rung.
_CHUNK_LINEAGE = [
    ("📄", "whole<br>PDF"),
    ("🔤", "text +<br>FTS5"),
    ("🧠", "text +<br>MiniLM"),
    ("⚛️", "atomic<br>idea"),
    ("🏷️", "+ typed<br>attrs"),
    ("🕸️", "+ graph<br>rels"),
    ("📐", "+ atom<br>embeds"),
    ("✋", "+ scholar<br>verdict"),
    ("◇", "(unchanged;<br>prompt evolves)"),
]

# Agent evolution: who the workforce IS at each rung. The *count* jumps at
# rungs 4 / 8 / 9; the answerer's tools grow at 4-7.
_AGENT_LINEAGE = [
    ("💬", "1 ag<br>Answerer"),
    ("💬", "1 ag<br>Answerer"),
    ("💬", "1 ag<br>Answerer"),
    ("💬🪓", "2 ag<br>+ Extractor"),
    ("💬🪓", "2 ag<br>(Ans+1 tool)"),
    ("💬🪓", "2 ag<br>(Ans+graph)"),
    ("💬🪓", "2 ag<br>(Ans+semantic)"),
    ("💬🪓🎯", "3 ag<br>+ Scorer"),
    ("💬🪓🎯🧬", "4 ag<br>+ Meta-Eval"),
]


def _lineage_bar(cells: list[tuple[str, str]], active_idx: int) -> str:
    """Render a 9-cell horizontal evolution bar with the active rung highlighted."""
    parts = []
    for i, (icon, label) in enumerate(cells):
        is_active = i == active_idx
        bg = "#1f2d4d" if is_active else "#161616"
        border = "2px solid #5b9aff" if is_active else "1px solid #2c2c2c"
        arrow = "▼" if is_active else "&nbsp;"
        arrow_color = "#5b9aff" if is_active else "transparent"
        parts.append(
            f"<div style='flex:1; text-align:center; min-width:64px;'>"
            f"<div style='color:{arrow_color}; height:14px; font-size:0.7em;'>{arrow}</div>"
            f"<div style='background:{bg}; border:{border}; border-radius:6px; "
            f"padding:8px 4px;'>"
            f"<div style='font-size:1.3em; line-height:1;'>{icon}</div>"
            f"<div style='font-size:0.7em; color:#a8a8a8; line-height:1.2; "
            f"margin-top:4px;'>{label}</div>"
            f"</div>"
            f"<div style='font-size:0.65em; color:#666; margin-top:3px;'>{i + 1}</div>"
            f"</div>"
        )
    return (
        "<div style='display:flex; gap:3px; align-items:flex-start; "
        "margin:8px 0 16px 0;'>" + "".join(parts) + "</div>"
    )


# ── tab 1: About ─────────────────────────────────────────────────────────

def _tab_about(s: Scenario, rung_index: int) -> None:
    active_idx = rung_index - 1

    # ── 1. Lineage — where am I on the chunk/agent evolution ──────────
    st.markdown("##### 🧬 Chunk evolution — what the unit of memory IS at each rung")
    st.markdown(_lineage_bar(_CHUNK_LINEAGE, active_idx), unsafe_allow_html=True)
    st.markdown("##### 🤖 Agent evolution — who the workforce IS at each rung")
    st.markdown(_lineage_bar(_AGENT_LINEAGE, active_idx), unsafe_allow_html=True)

    st.divider()

    # ── 2. Capability profile — what this rung has on/off (pills) ─────
    st.markdown("### 🎚️ Capability profile")
    st.markdown(_capability_pills_html(s), unsafe_allow_html=True)

    # ── 3. Agent roster — consolidated card + expander per agent ──────
    if s.agents:
        st.markdown("### 🤖 Agent roster")
        st.caption(
            f"This scenario wires **{len(s.agents)} agent(s)**. "
            "Each card shows the role + active prompt version + rubric criteria; "
            "expand for the full definition (model, output shape, tools, live prompt)."
        )
        for role in s.agents:
            _render_agent_definition(s, role)

    # ── 4. Live vault state — what's in the vault right now ───────────
    st.markdown("### 🧬 Live vault state")
    _render_vault_contents(s)


def _render_agent_definition(s: Scenario, role: AgentRole) -> None:
    """Per-agent expander: model · tools · output shape · system prompt body."""
    from openacad.runtime.settings import settings
    from openacad.runtime.scenario import active_scenario

    llm_role = AGENT_LLM_ROLE.get(role, "synthesis")
    model_name = (
        settings.extraction_model if llm_role == "extraction"
        else settings.synthesis_model
    )

    # Active prompt body — DB version-aware, falls back to per-scenario seed file.
    prompt_body: str = ""
    prompt_version: str = ""
    with use_scenario(s.key):
        try:
            actives = [p for p in db.list_prompts(name=role.value) if p.state == "active"]
            if actives:
                p = max(actives, key=lambda x: x.created_at)
                prompt_body = p.body
                prompt_version = p.version
        except Exception:
            pass
        if not prompt_body:
            try:
                fn = s.prompts_dir / f"{role.value}.v1.md"
                if fn.exists():
                    prompt_body = fn.read_text(encoding="utf-8")
                    prompt_version = f"{role.value}.v1 (from disk seed)"
            except Exception:
                pass

    rubric_str = ", ".join(s.rubric_criteria.get(role, [])) or "—"
    n_tools = len(_agent_tools_for(role, s))
    label = (
        f"{ROLE_EMOJI[role]} **{role.value}** — {model_name} · "
        f"{n_tools} tool{'s' if n_tools != 1 else ''} · rubric: {rubric_str}"
    )
    with st.expander(label, expanded=False):
        cols = st.columns(2)
        cols[0].markdown(f"**LLM role:** `{llm_role}`")
        cols[1].markdown(f"**Active prompt:** `{prompt_version or '—'}`")

        st.markdown(f"**Output type:** `{_agent_output_for(role, s)}`")

        tools = _agent_tools_for(role, s)
        if tools:
            st.markdown(f"**Tools the agent can call in this scenario ({len(tools)}):**")
            tool_rows = [{"signature": sig, "purpose": purpose} for sig, purpose in tools]
            st.dataframe(tool_rows, use_container_width=True, hide_index=True)
        elif role in (AgentRole.SCORER, AgentRole.META_EVAL):
            st.caption("This agent returns a structured output directly — no tools.")
        else:
            st.caption(
                "This agent has no tools in this scenario — it receives pre-retrieved "
                "context in the user prompt and writes a plain-text answer."
            )

        st.markdown("**System prompt:**")
        if prompt_body:
            st.code(prompt_body, language="markdown")
        else:
            st.caption("_(no prompt found; check seeding)_")


# ── Vault contents — used inline in the About tab ────────────────────────

def _render_vault_contents(s: Scenario) -> None:
    """Render the per-scenario vault. Pre-atom tiers have no per-scenario state
    (the corpus is shared) — those scenarios get a pointer to the **Build** tab
    instead of duplicating shared-corpus counts here.
    """
    if s.tier == Tier.COLD:
        st.info(
            "**No per-scenario vault.** Cold Read reads the shared corpus directly at "
            "query time — there's no extraction, no chunking step, no per-scenario "
            "index. See the source PDFs the answerer reads in the **🛠️ Build** tab."
        )
        return

    if s.tier == Tier.CHUNK:
        index_path = (
            "`data/shared.sqlite::chunks_fts` (FTS5 / BM25)"
            if s.key == "keyword-snippets"
            else "`data/embeddings/chunks.npz` (MiniLM 384-dim)"
        )
        st.info(
            "**No per-scenario vault.** Chunk-tier scenarios share the chunked corpus "
            f"in `data/shared.sqlite::chunks`. The only per-scenario thing here is the "
            f"retrieval index used at query time: **{index_path}**. The actual chunks "
            "the answerer can retrieve are shown in the **🛠️ Build** tab."
        )
        return

    # Atoms tier
    with use_scenario(s.key):
        atoms = vault_io.list_atoms()
        attrs = vault_io.list_attribute_defs() if s.has_attributes else []
        rels = vault_io.list_relation_defs() if s.has_relations else []
        types = vault_io.list_type_defs()
        npz_exists = s.atoms_npz_path.exists()

    cols = st.columns(5)
    cols[0].metric("📝 atoms", len(atoms))
    cols[1].metric("🏷️ attrs", len(attrs) if s.has_attributes else "—")
    cols[2].metric("🔗 rels", len(rels) if s.has_relations else "—")
    cols[3].metric("📦 types", len(types))
    cols[4].metric("📐 embeddings", "✅" if (s.has_atom_embeddings and npz_exists) else "—")

    inner = st.tabs(["📝 Notes", "🏷️ Attributes", "🔗 Relations", "📦 Types"])
    with inner[0]:
        if not atoms:
            st.info("No atoms yet — see the **Build** tab to populate this vault.")
        else:
            for a in atoms[:30]:
                with st.container(border=True):
                    c = st.columns([3, 1])
                    with c[0]:
                        st.markdown(f"**`{a.metas.id}`**")
                        st.caption(f"type: {a.metas.type} · tags: {', '.join(a.metas.tags) or '—'} · status: {a.metas.status}")
                        st.write(a.content[:280] + ("…" if len(a.content) > 280 else ""))
                    with c[1]:
                        st.caption(f"attrs: {len(a.attributes)}")
                        st.caption(f"rels: {len(a.relations)}")
            if len(atoms) > 30:
                st.caption(f"showing 30 of {len(atoms)}")
    with inner[1]:
        if not s.has_attributes:
            st.info("This scenario has `has_attributes=False` — typed attributes are disabled.")
        elif not attrs:
            st.info("No registered attribute defs yet.")
        else:
            st.dataframe(
                [{"key": a.key, "type": a.value_type, "usage": a.usage_count} for a in attrs],
                use_container_width=True, hide_index=True,
            )
    with inner[2]:
        if not s.has_relations:
            st.info("This scenario has `has_relations=False` — graph relations are disabled.")
        elif not rels:
            st.info("No registered relation defs yet.")
        else:
            st.dataframe(
                [{"key": r.key, "inverse": r.inverse, "usage": r.usage_count} for r in rels],
                use_container_width=True, hide_index=True,
            )
    with inner[3]:
        if types:
            st.dataframe(
                [{"key": t.key, "description": t.description} for t in types],
                use_container_width=True, hide_index=True,
            )
        else:
            st.info("No type defs.")


# ── tab 2: Build ─────────────────────────────────────────────────────────

def _tab_build(s: Scenario) -> None:
    st.subheader("Produce notes for this vault")
    sources = db.list_sources()

    # ── Cold tier: no chunks, no atoms; just sources ──────────────────
    if s.tier == Tier.COLD:
        st.markdown(
            "Cold Read has **no build step** — every query loads the full PDF text "
            "directly into the LLM prompt. The 'unit of memory' is the document itself."
        )
        st.markdown("##### PDFs the answerer reads at query time")
        if not sources:
            st.info("No PDFs ingested.")
        else:
            st.dataframe(
                [{
                    "source id": src.id,
                    "title": src.title or src.filename,
                    "pages": src.n_pages,
                    "uploaded": src.uploaded_at.strftime("%Y-%m-%d %H:%M"),
                } for src in sources],
                use_container_width=True, hide_index=True,
            )
        return

    # ── Chunk tier: shared chunks, scenario differs only in retrieval index ──
    if s.tier == Tier.CHUNK:
        index_used = (
            "**SQLite FTS5 / BM25** lexical index (`data/shared.sqlite::chunks_fts`)"
            if s.key == "keyword-snippets"
            else "**MiniLM cosine** semantic index (`data/embeddings/chunks.npz`)"
        )
        st.markdown(
            "Chunk-tier scenarios **share the same chunked corpus** in "
            "`data/shared.sqlite`. The difference between Keyword Snippets and "
            f"Semantic Snippets is the retrieval index, not the data: this scenario uses {index_used}."
        )
        st.caption(
            "⚠️ Keyword Snippets and Semantic Snippets show identical chunk "
            "tables — that's expected. The retrieval mechanism is what makes "
            "them different rungs."
        )
        chunks_total = sum(src.n_chunks for src in sources)
        cols = st.columns(2)
        cols[0].metric("📚 PDFs", len(sources))
        cols[1].metric("📑 chunks (shared)", chunks_total)

        st.markdown("##### Chunks (sample of 50 from the shared corpus)")
        rows = []
        try:
            for src in sources:
                for c in db.chunks_for_source(src.id)[:10]:
                    rows.append({
                        "chunk id": c.id,
                        "source": src.id.replace("paper-sdg-briefing-", ""),
                        "pages": f"{c.page_range[0]}–{c.page_range[1]}" if c.page_range else "—",
                        "tokens (approx)": len(c.text.split()),
                        "preview": (c.text[:100] + "…") if len(c.text) > 100 else c.text,
                    })
                if len(rows) >= 50:
                    break
        except Exception as e:
            st.error(f"Couldn't load chunks: {e}")
        if rows:
            st.dataframe(rows[:50], use_container_width=True, hide_index=True)
        return

    # ── Atom tier: two production paths, no duplicated atom listing ────
    # (the atom listing lives in About → Live vault state, single source)
    with use_scenario(s.key):
        n_atoms = len(db.list_atom_projections())

    st.markdown(
        f"Two ways to add notes to this vault. The current vault holds "
        f"**{n_atoms} atom{'s' if n_atoms != 1 else ''}** across **{len(sources)} PDF{'s' if len(sources) != 1 else ''}**. "
        "To browse what's already there, open the **About** tab → Live vault state."
    )

    path_a, path_b = st.columns(2)

    with path_a:
        with st.container(border=True):
            st.markdown("#### 🤖 AI extraction")
            st.caption(
                "Run the Extractor agent over every PDF and accept drafts per this "
                "scenario's policy. Applied flags:"
            )
            st.markdown(
                f"`attrs={s.has_attributes}` · `rels={s.has_relations}` · "
                f"`embeddings={s.has_atom_embeddings}` · `curation={s.has_curation}`"
            )
            if st.button("▶ Run extraction now", disabled=not sources, key=f"build-extract-{s.key}", use_container_width=True):
                st.info(
                    "Extraction takes ~5 min per scenario and costs LLM credits. "
                    "Use `scripts/seed_atom_decomposition.py <key>` from the CLI for "
                    "long-running seeds — Streamlit isn't the right place for a 5-min job."
                )

    with path_b:
        with st.container(border=True):
            st.markdown("#### ✍️ Author manually")
            if not s.has_curation:
                st.caption(
                    "ℹ️ This scenario has no curation gate — authored notes commit directly."
                )

            from openacad.notes.intake.authored import author_note
            from openacad.notes.schema import Relation

            with st.form(f"author-{s.key}", clear_on_submit=True):
                content = st.text_area("Note content", height=100,
                    placeholder="One self-contained claim, method, or finding…")
                kind = st.selectbox("Kind", options=["claim", "method", "finding"])
                tags_str = st.text_input("Tags (comma-sep)")
                if s.has_attributes:
                    attrs_str = st.text_input("Attributes (key=value, comma-sep)", placeholder="study.year=2024")
                else:
                    attrs_str = ""
                if s.has_relations:
                    rels_str = st.text_input("Relations (type target, semi-sep)", placeholder="supports atom-id")
                else:
                    rels_str = ""

                if st.form_submit_button("📝 Save", use_container_width=True):
                    if not content.strip():
                        st.error("Content required.")
                    else:
                        attrs = {}
                        for piece in attrs_str.split(","):
                            if "=" in piece:
                                k, v = piece.split("=", 1)
                                attrs[k.strip()] = v.strip()
                        rels = []
                        for piece in rels_str.split(";"):
                            parts = piece.strip().split(maxsplit=1)
                            if len(parts) == 2:
                                rels.append(Relation(type=parts[0], target=parts[1]))
                        tags = [t.strip() for t in tags_str.split(",") if t.strip()]
                        try:
                            with use_scenario(s.key):
                                atom = author_note(
                                    content=content, kind=kind, tags=tags,
                                    attributes=attrs, relations=rels,
                                )
                            st.success(f"Saved `{atom.metas.id}`")
                        except Exception as e:
                            st.error(f"Save failed: {e}")


# ── tab 3: Query ─────────────────────────────────────────────────────────

def _tab_query(s: Scenario) -> None:
    st.subheader(f"Ask {s.name}")
    st.markdown(
        "Pose a question; see the answer + cited units. **Every Ask is persisted** "
        "to this scenario's `comparisons` table — so the history below grows, and "
        "the Numbers / Conclusion pages pick up the new runs."
    )

    sources = db.list_sources()
    cols = st.columns([3, 2])
    question = cols[0].text_input(
        "Question",
        value="What are the main strategies for ending poverty (SDG 1)?",
        key=f"q-{s.key}",
    )
    paper_pick = cols[1].multiselect(
        "Restrict to sources",
        options=[src.id for src in sources],
        default=[],
        format_func=lambda sid: next(src.filename for src in sources if src.id == sid),
        key=f"pp-{s.key}",
    )

    if st.button("▶ Ask", type="primary", key=f"ask-{s.key}"):
        with st.spinner("Running…"):
            try:
                with use_scenario(s.key):
                    out = dispatcher.ask(question, paper_pick)
                    # Persist as a ComparisonResult so the run shows up in
                    # Numbers / Compare / Conclusion alongside head-to-head runs.
                    from openacad.feedback.schema import ComparisonResult
                    import uuid
                    from datetime import datetime, timezone
                    pipeline = {
                        "cold-read": "B0",
                        "semantic-snippets": "B1",
                        "keyword-snippets": "B2",
                    }.get(s.key, "A")
                    cr = ComparisonResult(
                        id=f"cmp-{uuid.uuid4().hex[:8]}",
                        question=question,
                        paper_ids=paper_pick,
                        pipeline=pipeline,
                        answer=out.answer,
                        citations=out.cited_units,
                        tokens_in=out.tokens_in,
                        tokens_out=out.tokens_out,
                        latency_ms=out.latency_ms,
                        n_units_retrieved=len(out.cited_units),
                        run_at=datetime.now(timezone.utc),
                    )
                    db.insert_comparison(cr)
                st.session_state[f"q-result-{s.key}"] = out.model_dump()
            except Exception as e:
                st.error(f"Query failed: {e}")

    res_key = f"q-result-{s.key}"
    if res_key in st.session_state:
        r = st.session_state[res_key]
        st.markdown("### Latest answer")
        st.write(r["answer"])
        c1, c2, c3 = st.columns(3)
        c1.metric("🪙 tokens in", r["tokens_in"])
        c2.metric("🪙 tokens out", r["tokens_out"])
        c3.metric("⚡ latency (ms)", r["latency_ms"])
        if r["cited_units"]:
            st.caption(
                "cited: "
                + ", ".join(f"`{c}`" for c in r["cited_units"][:8])
                + (f" +{len(r['cited_units'])-8} more" if len(r['cited_units']) > 8 else "")
            )

    # ── Past queries — persisted across browser sessions ─────────────
    st.divider()
    with use_scenario(s.key):
        past = db.list_comparisons()

    st.markdown(f"### 📜 Past queries on {s.name} ({len(past)})")
    if not past:
        st.info(
            "No past queries yet. Ask a question above, or seed all 9 scenarios "
            "with `python scripts/seed_query_history.py`."
        )
    else:
        past_sorted = sorted(past, key=lambda c: c.run_at, reverse=True)
        for c in past_sorted[:20]:
            with st.expander(
                f"❓ {c.question[:90]}{'…' if len(c.question) > 90 else ''}  ·  "
                f"{c.run_at.strftime('%Y-%m-%d %H:%M')}  ·  "
                f"{c.tokens_in + c.tokens_out:,} tokens  ·  "
                f"{c.latency_ms}ms  ·  {len(c.citations)} cited",
                expanded=False,
            ):
                st.markdown("**Question:**")
                st.markdown(f"> {c.question}")
                st.markdown("**Answer:**")
                st.write(c.answer)
                if c.citations:
                    st.caption(
                        "Cited units: "
                        + ", ".join(f"`{cit}`" for cit in c.citations[:12])
                        + (f" +{len(c.citations) - 12} more" if len(c.citations) > 12 else "")
                    )
                cols = st.columns(4)
                cols[0].metric("pipeline", c.pipeline)
                cols[1].metric("tokens in", c.tokens_in)
                cols[2].metric("tokens out", c.tokens_out)
                cols[3].metric("latency ms", c.latency_ms)
        if len(past) > 20:
            st.caption(f"showing 20 of {len(past)} past queries")


# ── tab 4: Evolve (gated by has_curation or has_meta_eval) ──────────────

def _tab_evolve(s: Scenario) -> None:
    st.subheader("Refine via scholar feedback")
    if s.has_curation:
        st.markdown("#### ✋ HITL queue")
        with use_scenario(s.key):
            sources = db.list_sources()
            pending = 0
            for src in sources:
                pending += len(db.drafts_for_source(src.id))
        st.metric("Drafts pending review", pending)
        if pending == 0:
            st.info("No drafts pending. Run extraction on the **Build** tab.")
        else:
            st.caption(
                f"Curation queue has {pending} drafts across {len(sources)} source(s). "
                "Use the CLI `python -m apps.cli.main curate ...` or scripts to process at scale."
            )

    if s.has_meta_eval:
        st.markdown("#### 🧬 Prompt versions")
        with use_scenario(s.key):
            rows = []
            for role in s.agents:
                prompts = db.list_prompts(name=role.value)
                active = next((p.version for p in prompts if p.state == "active"), "—")
                proposed = sum(1 for p in prompts if p.state == "proposed")
                rows.append({
                    "role": role.value,
                    "versions": len(prompts),
                    "active": active,
                    "proposed": proposed,
                })
        st.dataframe(rows, use_container_width=True, hide_index=True)

        st.caption(
            "Meta-Evaluator proposes hardened prompts once a role accumulates "
            "≥10 rubric ratings. Propose + promote actions live on the CLI today."
        )


# ── tab 5 (or 4): Results ────────────────────────────────────────────────


def _previous_scenario(s: Scenario):
    """The scenario one rung below this one, or None if this is rung 1."""
    keys = [sc.key for sc in SCENARIOS]
    idx = keys.index(s.key)
    return SCENARIOS[idx - 1] if idx > 0 else None


def _query_metrics(scenario_key: str) -> dict | None:
    """avg tokens / latency / citations / cost from persisted comparisons."""
    with use_scenario(scenario_key):
        cmps = db.list_comparisons()
    if not cmps:
        return None
    n = len(cmps)
    avg_tokens = sum(c.tokens_in + c.tokens_out for c in cmps) / n
    avg_latency = sum(c.latency_ms for c in cmps) / n
    avg_cites = sum(len(c.citations) for c in cmps) / n
    # gpt-4o-mini pricing (matches goodness page)
    avg_cost = sum(
        (c.tokens_in * 0.15 + c.tokens_out * 0.60) / 1_000_000
        for c in cmps
    ) / n
    return {
        "n": n,
        "avg_tokens": avg_tokens,
        "avg_latency": avg_latency,
        "avg_citations": avg_cites,
        "avg_cost": avg_cost,
    }


def _pct_delta(curr: float, prev: float) -> str:
    """Format a percentage delta like '+34%' or '-12%'."""
    if prev == 0:
        return "—" if curr == 0 else "new"
    pct = (curr - prev) / prev * 100
    return f"{pct:+.0f}%"


def _economics(s: Scenario, me: dict | None) -> dict | None:
    """Compute cost economics for THIS scenario vs the cold-read baseline.

    Returns a dict of pre-formatted strings keyed by metric, or None if no
    runs yet. Cold-read is the reference cost ceiling for the whole ladder.
    """
    if not me:
        return None
    baseline = _query_metrics("cold-read")
    cost_q = me["avg_cost"]
    total_spent = cost_q * me["n"]
    cite_q = me["avg_citations"]
    cost_per_cite = (cost_q / cite_q) if cite_q > 0 else None

    if baseline and baseline["avg_cost"] > 0 and s.key != "cold-read":
        ratio = cost_q / baseline["avg_cost"]
        if ratio >= 1:
            vs_baseline = f"{ratio:.1f}× more expensive"
        else:
            vs_baseline = f"{1/ratio:.1f}× cheaper"
    elif s.key == "cold-read":
        vs_baseline = "baseline"
    else:
        vs_baseline = "—"

    return {
        "cost_per_query": f"${cost_q:.4f}",
        "vs_baseline": vs_baseline,
        "cost_per_cite": f"${cost_per_cite:.4f}" if cost_per_cite else "—",
        "total_spent": f"${total_spent:.4f}",
        "_ratio": (cost_q / baseline["avg_cost"]) if (baseline and baseline["avg_cost"] > 0) else None,
    }


def _commentary(s: Scenario, atoms, comparisons, me: dict | None, them: dict | None) -> list[str]:
    """Return scenario-specific qualitative insights as a list of markdown bullets.

    Built dynamically — references live numbers (tokens, citations) when available
    so the commentary stays in lockstep with the data.
    """
    bullets: list[str] = []
    avg_tok = int(me["avg_tokens"]) if me else None
    avg_cite = me["avg_citations"] if me else None
    prev_tok = int(them["avg_tokens"]) if them else None
    prev_cite = them["avg_citations"] if them else None

    if s.key == "cold-read":
        return [
            "**Baseline.** Every query sends the full PDF text into the prompt; no retrieval, no memory, no chunking.",
            f"The **~{avg_tok or '?'} avg tokens/query** is what 'zero memory' looks like — there's nothing to cache, every query pays full price.",
            "Citation count hovers near zero because page-range citations rarely survive the LLM's prose.",
            "**Use Cold Read as the cost ceiling** the rest of the ladder is measured against.",
        ]

    if s.key == "keyword-snippets":
        delta = f"≈{int(prev_tok/avg_tok)}×" if (prev_tok and avg_tok) else "~"
        return [
            f"Tokens drop **{delta} cheaper** vs Cold Read — the headline cost win of any retrieval over full-doc dumping.",
            "FTS5 returns top-K=6 chunks; the answerer cites all 6 (chunk_ids). High citation count, but each chunk is anonymous text — no identity beyond its id.",
            "**Strength:** exact keyword matches, rare-term boosting via BM25 ranking.",
            "**Weakness:** misses semantic paraphrases — a question worded differently from the source won't hit. (The semantic rung fixes this without changing chunks.)",
        ]

    if s.key == "semantic-snippets":
        return [
            "Token cost roughly matches Keyword Snippets — same chunks, same top-K. What changes is **which** chunks come back, not how many.",
            "First rung where **meaning** enters the loop: MiniLM cosine catches paraphrases that BM25 misses.",
            "Citations stay at ~6 because top-K is unchanged. The win is **recall on conceptual questions**, not citation count.",
            "On a corpus of well-aligned text (like the SDG briefing), the keyword/semantic delta is small. On rephrased or jargon-heavy corpora it widens dramatically.",
        ]

    if s.key == "atoms-only":
        cite_drop = ""
        if prev_cite and avg_cite is not None and avg_cite < prev_cite:
            cite_drop = f" — from ~{prev_cite:.0f} chunks to ~{avg_cite:.1f} atoms per answer"
        return [
            f"**Tokens jump ~{int(avg_tok/(prev_tok or 1)) if prev_tok else '?'}×** vs the chunk tier — the answerer is now a tool-calling agent that loops (plan → query_atoms → get_atom_full → compose).",
            f"**Citation count drops{cite_drop}.** This is the KEY thesis insight: **atoms are denser than chunks.** One atom can carry the substance of 2-3 chunks.",
            "What you lose in citation COUNT, you gain in citation SPECIFICITY: each cited atom is an addressable claim with provenance, not an anonymous text window.",
            "First rung with **persistent memory** — atoms cited today are still cite-able tomorrow, by any future query.",
            "Quality up, count down. Don't read this as 'worse' — read it as 'sharper per cite'.",
        ]

    if s.key == "atoms-attrs":
        cite_jump = ""
        if prev_cite and avg_cite and avg_cite > prev_cite:
            cite_jump = f" from {prev_cite:.1f} → {avg_cite:.1f}"
        return [
            f"Token cost roughly matches atoms-only — typed attributes don't make the agent loop longer, just smarter.",
            f"**Citations grow{cite_jump}** because typed filters let the answerer find more relevant atoms (e.g. 'claims about SDG 5 with target.year=2030').",
            "The registry auto-promotes recurring attribute keys — this is the rung where the vault starts having a **schema**, not just content.",
            "Same accuracy story as atoms-only: each citation is more specific than a chunk cite. The added attrs make filtering precise.",
        ]

    if s.key == "atoms-attrs-rels":
        tok_k = avg_tok // 1000 if avg_tok else None
        return [
            f"**Token cost EXPLODES to ~{tok_k}k/q** — graph traversal opens multi-hop reasoning; one question can spawn 30-80 tool calls (plan → query → traverse → traverse → cite).",
            f"Citations climb modestly (~{avg_cite:.1f}/q) but the **traversal depth** is what matters: the agent now chains `supports`/`contradicts`/`extends` edges across atoms.",
            "**Production caveat:** bounded-depth traversal (max-hops=2) would cap this cost without losing most of the value. The demo runs unbounded to expose the ceiling.",
            "The thesis: the vault becomes a **knowledge graph**, not a flat list. Some multi-hop questions that were impossible at earlier rungs become natural here.",
        ]

    if s.key == "drafted-notes":
        return [
            "**Atom embeddings unlock `find_similar_atoms`** — the answerer now has semantic search at atom granularity, not just chunk granularity.",
            "Token cost similar to atoms-attrs-rels; the new capability is qualitative, not metric-defining.",
            "Still **auto-accept**: atoms enter the vault without scholar review. This is the 'all capabilities, no humans' baseline.",
            "Compare to the next rung (Curated): fewer atoms but each scholar-verified. Watch the citation count change there.",
        ]

    if s.key == "curated-notes":
        cite_str = f"{avg_cite:.1f}" if avg_cite is not None else "?"
        prev_cite_str = f"{prev_cite:.1f}" if prev_cite is not None else "?"
        tok_str = f"{avg_tok:,}" if avg_tok else "?"
        return [
            f"**Scholar enters the loop** — accept/edit/reject decides what reaches the vault. Atoms are immutable once accepted.",
            f"Citation count drops to **~{cite_str}** (vs {prev_cite_str} on Drafted) because the curated vault is smaller and each remaining atom is more selective — the answerer has fewer-but-better targets to cite.",
            f"Token cost actually **rises** to ~{tok_str}/q because the agent works harder against a smaller vault — more semantic search calls to find acceptable citations.",
            "**This is the accuracy tradeoff made visible:** lower citation count and higher cost is **not a regression**. Every cite carries scholar provenance, not LLM provenance.",
            "Production cost shifts from compute to human time. Scaling = multi-scholar accounts + per-domain queues — the demo collapses both into one operator.",
        ]

    if s.key == "evolving-notes":
        tok_str = f"{avg_tok:,}" if avg_tok else "?"
        cite_str = f"{avg_cite:.1f}" if avg_cite is not None else "?"
        return [
            f"**Same vault as Curated** — atoms are immutable. What evolves is the **agents' prompts**, driven by Meta-Evaluator reading scholar rubrics.",
            f"Token cost spikes to **~{tok_str}/q** because the evolved synthesis prompt is more thorough: deeper relation traversal, more careful citation selection, longer reasoning.",
            f"Citation count drops to **~{cite_str}/q** — surprisingly low. The evolved prompts are **more disciplined**: answers without strong atom evidence cite nothing rather than weakly grounding.",
            "**Half the cost moves to discipline, not retrieval.** You're paying for the agent's restraint, not its tool calls. That's the qualitative shift no other rung shows.",
            "**The compounding return isn't visible in one snapshot.** Over more rubric submissions, prompts continue to evolve — see the Evolve tab's version history (v1 → v2 → v3 per agent).",
            "Only rung where today's system ≠ yesterday's system — and the difference is **scholar-promoted, not auto-applied**.",
        ]

    return ["_(no commentary configured for this scenario)_"]


def _tab_results(s: Scenario) -> None:
    st.subheader(f"Results — {s.name}")

    with use_scenario(s.key):
        atoms = vault_io.list_atoms() if s.tier == Tier.ATOMS else []
        comparisons = db.list_comparisons()
        try:
            from openacad.feedback import rubric
            total_rubrics = sum(
                len(rubric.list_for_role(r)) for r in s.agents
            )
        except Exception:
            total_rubrics = 0
        try:
            sources = db.list_sources()
            total_drafts = sum(len(db.drafts_for_source(src.id)) for src in sources)
        except Exception:
            total_drafts = 0

    # ── 1. Signature metric ────────────────────────────────────────────
    sig_label, sig_value, sig_caption = _signature_metric(s, atoms, comparisons)
    with st.container(border=True):
        sig_cols = st.columns([1, 3])
        with sig_cols[0]:
            st.markdown(
                f"<div style='font-size:0.75em; color:#888; "
                f"text-transform:uppercase; letter-spacing:0.05em;'>"
                f"this scenario's signature</div>"
                f"<div style='font-size:2.4em; font-weight:700; line-height:1.1; "
                f"margin-top:6px;'>{sig_value}</div>"
                f"<div style='font-size:0.95em; color:#aaa; margin-top:4px;'>{sig_label}</div>",
                unsafe_allow_html=True,
            )
        with sig_cols[1]:
            st.markdown(f"<div style='margin-top:18px; padding-left:20px; "
                        f"border-left:2px solid #444;'>{sig_caption}</div>",
                        unsafe_allow_html=True)

    # ── 2. Δ vs the previous rung ──────────────────────────────────────
    prev = _previous_scenario(s)
    st.markdown("### 📈 Δ vs the previous rung")
    if prev is None:
        st.info(
            "**No previous rung.** Cold Read is rung 1 — the baseline the rest of "
            "the ladder is measured against."
        )
    else:
        me = _query_metrics(s.key)
        them = _query_metrics(prev.key)
        if not me:
            st.info(f"No query runs persisted for `{s.key}` yet. Run a question on the **Query** tab to populate.")
        elif not them:
            st.info(
                f"`{prev.name}` (the rung below) has no query runs yet — "
                f"no baseline to compare against."
            )
        else:
            st.caption(
                f"Compared head-to-head against **{TIER_EMOJI[prev.tier]} {prev.name}** "
                f"(rung {SCENARIOS.index(prev) + 1}). Lower tokens/latency/cost = better; "
                f"higher citations = better."
            )
            d_cols = st.columns(4)
            d_cols[0].metric(
                "avg tokens/q",
                f"{int(me['avg_tokens']):,}",
                delta=_pct_delta(me['avg_tokens'], them['avg_tokens']),
                delta_color="inverse",
            )
            d_cols[1].metric(
                "avg citations/q",
                f"{me['avg_citations']:.1f}",
                delta=_pct_delta(me['avg_citations'], them['avg_citations']),
            )
            d_cols[2].metric(
                "avg latency (ms)",
                f"{int(me['avg_latency'])}",
                delta=_pct_delta(me['avg_latency'], them['avg_latency']),
                delta_color="inverse",
            )
            d_cols[3].metric(
                "avg cost / q",
                f"${me['avg_cost']:.4f}",
                delta=_pct_delta(me['avg_cost'], them['avg_cost']),
                delta_color="inverse",
            )

            # One-line interpretation
            tok_pct = (me['avg_tokens'] - them['avg_tokens']) / them['avg_tokens'] * 100 if them['avg_tokens'] else 0
            cite_pct = (me['avg_citations'] - them['avg_citations']) / max(them['avg_citations'], 0.01) * 100
            interpretation = []
            if abs(tok_pct) >= 10:
                direction = "uses" if tok_pct > 0 else "saves"
                interpretation.append(f"{direction} {abs(tok_pct):.0f}% more tokens" if tok_pct > 0
                                      else f"saves {abs(tok_pct):.0f}% on tokens")
            if abs(cite_pct) >= 10 and them['avg_citations'] > 0.5:
                direction = "cites" if cite_pct > 0 else "cites"
                interpretation.append(f"{direction} {abs(cite_pct):.0f}% {'more' if cite_pct > 0 else 'fewer'} units")
            if interpretation:
                st.markdown(
                    f"**Net effect**: vs the previous rung, this scenario "
                    + " and ".join(interpretation) + "."
                )
            st.caption(
                f"Sample size: {me['n']} runs here vs {them['n']} runs in {prev.name}. "
                "Wider gaps in one or the other → treat the % delta as approximate."
            )

    # ── 3. Economics — vs cold-read baseline + cost-per-cite ───────────
    me_stats = _query_metrics(s.key)
    them_stats = _query_metrics(prev.key) if prev else None
    econ = _economics(s, me_stats)
    if econ:
        st.markdown("### 💰 Economics")
        st.caption(
            "Per-query cost and how it stacks against the Cold Read baseline. "
            "Cost = OpenRouter gpt-4o-mini pricing ($0.15/M in, $0.60/M out). "
            "**Cost / cite** is illustrative — chunk-cites and atom-cites carry different information density, so don't compare across tiers naively."
        )
        ec_cols = st.columns(4)
        ec_cols[0].metric("💵 cost / query", econ["cost_per_query"])
        ec_cols[1].metric(
            "📐 vs Cold Read",
            econ["vs_baseline"],
            help="How this rung's per-query cost compares to the Cold Read baseline (full-PDF dump, no retrieval).",
        )
        ec_cols[2].metric(
            "🎯 cost / citation",
            econ["cost_per_cite"],
            help="avg_cost ÷ avg_citations. Lower is better, BUT the cost-per-cite is misleading across tiers because chunk-cites and atom-cites are different units.",
        )
        ec_cols[3].metric(
            "💸 total spent (this rung)",
            econ["total_spent"],
            help=f"avg_cost × {me_stats['n']} runs.",
        )

    # ── 4. Commentary — qualitative interpretation of the numbers ──────
    st.markdown("### 💬 Commentary")
    st.caption(
        "What the numbers above mean, what they DON'T mean, and how to read the "
        "tradeoffs vs the previous rung."
    )
    bullets = _commentary(s, atoms, comparisons, me_stats, them_stats)
    for b in bullets:
        st.markdown(f"- {b}")

    # ── 4. Supporting metrics ──────────────────────────────────────────
    st.markdown("### Supporting metrics")
    cols = st.columns(4)
    cols[0].metric("📝 atoms", len(atoms) if s.tier == Tier.ATOMS else "—")
    cols[1].metric("📋 drafts pending", total_drafts if s.tier == Tier.ATOMS else "—")
    cols[2].metric("⭐ rubric ratings", total_rubrics)
    cols[3].metric("⚖️ comparison runs", len(comparisons))

    # ── 5. Atom information density (atom-tier only) ───────────────────
    if s.tier == Tier.ATOMS and atoms:
        st.markdown("### 🧠 Atom information density")
        st.caption(
            "How much information each atom carries on average. Denser atoms mean "
            "fewer-but-richer citations per answer — quality up, raw count down."
        )
        with_attrs = sum(1 for a in atoms if a.attributes)
        with_rels = sum(1 for a in atoms if a.relations)
        total_attr_count = sum(len(a.attributes) for a in atoms)
        total_rel_count = sum(len(a.relations) for a in atoms)
        total_content_chars = sum(len(a.content) for a in atoms)
        avg_content_chars = total_content_chars // max(len(atoms), 1)
        density_cols = st.columns(4)
        density_cols[0].metric("📝 atoms", len(atoms))
        density_cols[1].metric("📜 avg content chars / atom", f"{avg_content_chars:,}")
        density_cols[2].metric(
            "🏷️ avg attrs / atom",
            round(total_attr_count / max(len(atoms), 1), 2) if s.has_attributes else "—",
        )
        density_cols[3].metric(
            "🔗 avg rels / atom",
            round(total_rel_count / max(len(atoms), 1), 2) if s.has_relations else "—",
        )
        coverage_cols = st.columns(4)
        pct_attrs = (with_attrs * 100 // max(len(atoms), 1)) if s.has_attributes else 0
        pct_rels = (with_rels * 100 // max(len(atoms), 1)) if s.has_relations else 0
        coverage_cols[0].metric(
            "% with attrs",
            f"{pct_attrs}%" if s.has_attributes else "—",
        )
        coverage_cols[1].metric(
            "% with rels",
            f"{pct_rels}%" if s.has_relations else "—",
        )
        # A rough info-density score: chars + attrs*40 + rels*30 per atom
        density_score = avg_content_chars + (total_attr_count * 40 + total_rel_count * 30) / max(len(atoms), 1)
        coverage_cols[2].metric(
            "📊 density score",
            f"{int(density_score):,}",
            help="content_chars + attrs*40 + rels*30, averaged per atom. "
                 "Rough proxy for how much information one citation gives the reader.",
        )
        coverage_cols[3].metric(
            "🧾 total info",
            f"{int(total_content_chars + total_attr_count*40 + total_rel_count*30):,}",
            help="Sum across all atoms — the vault's total addressable knowledge.",
        )

    # ── 6. Per-question token cost ─────────────────────────────────────
    if comparisons:
        st.markdown("### Per-question performance")
        rows = []
        for c in comparisons:
            rows.append({
                "question": c.question[:60] + ("…" if len(c.question) > 60 else ""),
                "tokens_in": c.tokens_in,
                "tokens_out": c.tokens_out,
                "total": c.tokens_in + c.tokens_out,
                "latency_ms": c.latency_ms,
                "citations": len(c.citations),
            })
        st.dataframe(rows, use_container_width=True, hide_index=True)


# (Compare tab removed — cross-scenario aggregation lives on the Conclusion page.)


# ── Signature metric — single defining number per scenario ───────────────

def _signature_metric(s, atoms, comparisons) -> tuple[str, str, str]:
    """Return (label, big_value, caption) for the scenario's defining metric.

    Each scenario's signature is the ONE number that proves what it uniquely
    enables — the capability that makes it different from the rung below it.
    """
    # Cold Read — defined by token cost per query (no memory, every q pays full price)
    if s.key == "cold-read":
        if comparisons:
            avg = sum(c.tokens_in + c.tokens_out for c in comparisons) // len(comparisons)
            return (
                "avg tokens / query",
                f"{avg:,}",
                "Cold Read sends the whole PDF every query. No memory means every question "
                "pays the same price — the upper bound the whole ladder is compared against.",
            )
        return ("avg tokens / query", "—",
                "Run a head-to-head on the Conclusion page to populate this.")

    # Keyword Snippets — defined by lexical retrieval
    if s.key == "keyword-snippets":
        if comparisons:
            avg = sum(c.tokens_in + c.tokens_out for c in comparisons) // len(comparisons)
            return (
                "avg tokens / query (lexical retrieval)",
                f"{avg:,}",
                "Top-K chunks by SQLite FTS5/BM25. No semantics — just lexical match. "
                "Tokens drop sharply vs Cold Read because only the matching chunks reach the LLM.",
            )
        return ("avg tokens / query (lexical)", "—", "Run a head-to-head to populate.")

    # Semantic Snippets — defined by semantic retrieval
    if s.key == "semantic-snippets":
        if comparisons:
            avg = sum(c.tokens_in + c.tokens_out for c in comparisons) // len(comparisons)
            return (
                "avg tokens / query (semantic retrieval)",
                f"{avg:,}",
                "Top-K chunks by MiniLM cosine. Semantic match catches paraphrases keyword misses. "
                "Same token budget as keyword tier, better recall on conceptual questions.",
            )
        return ("avg tokens / query (semantic)", "—", "Run a head-to-head to populate.")

    # Atoms-only — defined by the existence of atomic memory units
    if s.key == "atoms-only":
        return (
            "atoms in vault",
            f"{len(atoms):,}",
            "This is where memory becomes addressable — each atom is one self-contained idea "
            "with its own id. No attributes, no relations, no embeddings yet; just units the "
            "answerer can cite individually.",
        )

    # +Attributes — defined by typed attribute coverage
    if s.key == "atoms-attrs":
        from openacad.notes.persistence import vault as vault_io
        with use_scenario(s.key):
            attr_defs = vault_io.list_attribute_defs()
        total_attrs = sum(len(a.attributes) for a in atoms)
        return (
            "typed attribute defs in registry",
            f"{len(attr_defs)}",
            f"{total_attrs} attribute values across {len(atoms)} atoms. Typed attributes make atoms "
            "relational-DB friendly: filters like `study.year > 2020` become possible. The registry "
            "promotes recurring keys so the schema grows from data.",
        )

    # +Relations — defined by graph structure
    if s.key == "atoms-attrs-rels":
        from openacad.notes.persistence import vault as vault_io
        with use_scenario(s.key):
            rel_defs = vault_io.list_relation_defs()
        total_rels = sum(len(a.relations) for a in atoms)
        return (
            "typed relation defs in registry",
            f"{len(rel_defs)}",
            f"{total_rels} relation edges across {len(atoms)} atoms. Atoms now form a graph: "
            "traversal queries like `supports`, `contradicts`, `extends` become possible. The "
            "answerer can chain hops instead of just filtering.",
        )

    # +Atom Embeddings (drafted-notes) — defined by semantic memory ops
    if s.key == "drafted-notes":
        npz_size_kb = 0
        try:
            if s.atoms_npz_path.exists():
                npz_size_kb = s.atoms_npz_path.stat().st_size // 1024
        except Exception:
            pass
        return (
            "atom embeddings (KB on disk)",
            f"{npz_size_kb}",
            f"{len(atoms)} atoms now have MiniLM vectors. `find_similar_atoms()` becomes a real "
            "tool. This is the first scenario with the FULL atom-tier capability bundle — "
            "auto-accept means humans aren't in the loop yet.",
        )

    # +HITL Curation (curated-notes) — defined by scholar verdicts
    if s.key == "curated-notes":
        touched = sum(
            1 for a in atoms
            if a.origin.scholar_action in ("accepted", "edited", "originated")
        )
        pct = (100 * touched / len(atoms)) if atoms else 0
        return (
            "% atoms touched by a scholar verdict",
            f"{pct:.0f}%",
            f"{touched} of {len(atoms)} atoms entered the vault via accept/edit/originated — not "
            "auto-acceptance. Every atom now carries the scholar's fingerprint. This is the first "
            "scenario where the memory is *trusted* in the human sense.",
        )

    # Self-Improving (evolving-notes) — defined by prompt evolution
    if s.key == "evolving-notes":
        with use_scenario(s.key):
            n_versions = 0
            for role in s.agents:
                try:
                    n_versions += len(db.list_prompts(name=role.value))
                except Exception:
                    pass
        return (
            "agent prompt versions on disk",
            f"{n_versions}",
            "Each version is a Meta-Evaluator proposal the scholar promoted, or a default seed. "
            "The atoms didn't change — the agents' INSTRUCTIONS did. This is the only scenario "
            "where today's system is structurally better than yesterday's.",
        )

    # Fallback (shouldn't hit)
    return ("—", "—", "No signature configured for this scenario.")
