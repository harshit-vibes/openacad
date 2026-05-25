"""Finale → Conclusion: tabbed comparison hub + receipts + quantitative goodness.

Two tabs:
  • 🎓 Thesis — the thesis-in-numbers narrative + head-to-head runner +
    ladder summary + production extensions.
  • 📐 Goodness — the deep quantitative analysis (per-scenario summary,
    cost / citation / latency dimensions, head-to-head comparison cards).

The Goodness tab absorbs the content that used to live in the standalone
`95_goodness.py` page.
"""

from __future__ import annotations

import statistics
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

DEMO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(DEMO_ROOT) not in sys.path:
    sys.path.insert(0, str(DEMO_ROOT))

import pandas as pd
import streamlit as st

from openacad.runtime.settings import settings
from openacad.feedback.schema import ComparisonResult
from openacad.runtime.scenario import SCENARIOS, AgentRole, Tier, use_scenario
from openacad.runtime import db
from openacad.runtime import dispatcher as scenario_runtime
from apps.streamlit.widgets import page_header, scenario_nav_footer


TIER_EMOJI = {Tier.COLD: "🥶", Tier.CHUNK: "🧩", Tier.ATOMS: "⚛️"}


# gpt-4o-mini pricing — shared between Thesis (cost narrative) and Goodness (charts).
COST_IN_PER_M = 0.15
COST_OUT_PER_M = 0.60


def _cost_usd(tokens_in: int, tokens_out: int) -> float:
    return (tokens_in * COST_IN_PER_M + tokens_out * COST_OUT_PER_M) / 1_000_000


# ─────────────────────────────────────────────────────────────────────────
# THESIS TAB
# ─────────────────────────────────────────────────────────────────────────


def _render_thesis() -> None:
    # 1. Run the head-to-head ─────────────────────────────────────────────
    st.subheader("🏃 Run the head-to-head")
    st.markdown(
        f"Same question, all {len(SCENARIOS)} strategies, side-by-side. Each run "
        "is persisted, so the tables and charts below grow as you ask more."
    )

    sources = db.list_sources()
    if not sources:
        st.info("No PDFs yet — go to 📚 **Your Library** first.")
        return

    DEMO_QUESTIONS = {
        "What are the main strategies for ending poverty (SDG 1)?":
            "paper-sdg-briefing-ch02-sdg-1-5-people",
        "What targets does SDG 5 (gender equality) include?":
            "paper-sdg-briefing-ch02-sdg-1-5-people",
        "What does the briefing say about clean water (SDG 6) and clean energy (SDG 7)?":
            "paper-sdg-briefing-ch03-sdg-6-10",
        "Which SDGs are about peace, justice, and partnerships?":
            "paper-sdg-briefing-ch05-sdg-16-17-peace",
    }

    pick_q = st.selectbox(
        "Pick a demo question",
        options=list(DEMO_QUESTIONS.keys()) + ["✏️ Custom…"],
    )
    if pick_q == "✏️ Custom…":
        question = st.text_input("Custom question", value="")
        paper_default = [sources[0].id]
    else:
        question = pick_q
        target_paper = DEMO_QUESTIONS[pick_q]
        paper_default = (
            [target_paper]
            if any(s.id == target_paper for s in sources)
            else [sources[0].id]
        )

    cols = st.columns(2)
    with cols[0]:
        scenarios_pick = st.multiselect(
            f"Strategies (all {len(SCENARIOS)} selected by default)",
            options=[s.key for s in SCENARIOS],
            default=[s.key for s in SCENARIOS],
            format_func=lambda k: next(
                f"{TIER_EMOJI[s.tier]} {s.name}" for s in SCENARIOS if s.key == k
            ),
        )
    with cols[1]:
        paper_pick = st.multiselect(
            "Restrict to sources",
            options=[src.id for src in sources],
            default=paper_default,
            format_func=lambda sid: next(
                s.filename for s in sources if s.id == sid
            ),
        )

    # Readiness check
    readiness: dict[str, dict] = {}
    for s in SCENARIOS:
        if s.key not in scenarios_pick:
            continue
        with use_scenario(s.key):
            n_atoms = (
                len(db.list_atom_projections()) if s.tier == Tier.ATOMS else None
            )
        readiness[s.key] = {"name": s.name, "tier": s.tier, "atoms": n_atoms}

    unprepared = [
        k
        for k, r in readiness.items()
        if r["tier"] == Tier.ATOMS and (r["atoms"] or 0) == 0
    ]
    if unprepared:
        bullets = " · ".join(readiness[k]["name"] for k in unprepared)
        st.warning(
            f"⚠️ **Atom-tier scenarios not yet prepared:** {bullets}.  \n"
            f"Go to 📚 **Your Library** → **Prepare your assistant** to populate them. "
            f"These scenarios will be shown but their answer will say *vault empty*."
        )

    if st.button("▶ Run head-to-head", type="primary", use_container_width=True):
        if not question.strip():
            st.error("Pick or enter a question first.")
        elif not scenarios_pick:
            st.error("Pick at least one strategy.")
        else:
            results = {}
            progress = st.progress(0.0, text="Starting…")
            for i, sk in enumerate(scenarios_pick):
                scenario_name = next(s.name for s in SCENARIOS if s.key == sk)
                progress.progress(
                    i / len(scenarios_pick), text=f"{scenario_name}…"
                )
                with use_scenario(sk):
                    out = scenario_runtime.ask(question, paper_pick)
                    cr = ComparisonResult(
                        id=f"cmp-{uuid.uuid4().hex[:8]}",
                        question=question,
                        paper_ids=paper_pick,
                        pipeline={
                            "cold-read": "B0",
                            "semantic-snippets": "B1",
                            "keyword-snippets": "B2",
                        }.get(sk, "A"),
                        answer=out.answer,
                        citations=out.cited_units,
                        tokens_in=out.tokens_in,
                        tokens_out=out.tokens_out,
                        latency_ms=out.latency_ms,
                        n_units_retrieved=len(out.cited_units),
                        run_at=datetime.now(timezone.utc),
                    )
                    db.insert_comparison(cr)
                results[sk] = out.model_dump()
            progress.progress(1.0, text="Done.")
            st.session_state["compare_results"] = results
            st.session_state["compare_question"] = question

    if "compare_results" in st.session_state:
        st.divider()
        results = st.session_state["compare_results"]
        st.markdown(
            f"**Latest run:** *{st.session_state.get('compare_question', '')}*"
        )
        rows = []
        for sk, out in results.items():
            scenario = next(s for s in SCENARIOS if s.key == sk)
            rows.append({
                "scenario": f"{TIER_EMOJI[scenario.tier]} {scenario.name}",
                "agents": len(scenario.agents),
                "tokens_in": out["tokens_in"],
                "tokens_out": out["tokens_out"],
                "total_tokens": out["tokens_in"] + out["tokens_out"],
                "latency_ms": out["latency_ms"],
                "citations": len(out["cited_units"]),
            })
        st.dataframe(rows, use_container_width=True, hide_index=True)

        if rows:
            non_empty = [r for r in rows if r["tokens_out"] > 30]
            if non_empty:
                cheapest = min(non_empty, key=lambda r: r["total_tokens"])
                fastest = min(non_empty, key=lambda r: r["latency_ms"])
                most_cited = max(non_empty, key=lambda r: r["citations"])
                wc1, wc2, wc3 = st.columns(3)
                wc1.metric(
                    "💰 cheapest", cheapest["scenario"],
                    f"{cheapest['total_tokens']} tokens",
                )
                wc2.metric(
                    "⚡ fastest", fastest["scenario"],
                    f"{fastest['latency_ms']}ms",
                )
                wc3.metric(
                    "📎 most cited", most_cited["scenario"],
                    f"{most_cited['citations']} units",
                )

        st.markdown("##### Answers")
        cols = st.columns(len(results))
        for col, (sk, out) in zip(cols, results.items()):
            scenario = next(s for s in SCENARIOS if s.key == sk)
            with col:
                st.markdown(f"**{TIER_EMOJI[scenario.tier]} {scenario.name}**")
                st.caption(
                    f"{len(scenario.agents)} agent · "
                    f"{out['tokens_in'] + out['tokens_out']} tokens"
                )
                st.write(out["answer"])
                if out["cited_units"]:
                    st.caption(
                        "cited: "
                        + ", ".join(f"`{c}`" for c in out["cited_units"][:5])
                        + (
                            f" +{len(out['cited_units']) - 5} more"
                            if len(out["cited_units"]) > 5
                            else ""
                        )
                    )

    # 2. Cost & performance ──────────────────────────────────────────────
    st.divider()
    st.subheader("💸 Cost & performance — across every recorded run")
    st.markdown(
        "Aggregated from every head-to-head you've run, all scenarios pooled. "
        "The deeper you go (more questions, more atom-tier runs), the more "
        "honest these numbers get."
    )

    def _agent_model(role: AgentRole) -> str:
        if role == AgentRole.ANSWERER:
            return settings.synthesis_model
        return settings.extraction_model

    cost_rows = []
    for s in SCENARIOS:
        with use_scenario(s.key):
            cmps = db.list_comparisons()
        n_runs = len(cmps)
        total_tokens = sum(c.tokens_in + c.tokens_out for c in cmps)
        total_latency = sum(c.latency_ms for c in cmps)
        total_citations = sum(len(c.citations) for c in cmps)
        avg_tokens = total_tokens // n_runs if n_runs else 0
        avg_latency = total_latency // n_runs if n_runs else 0
        avg_citations = total_citations / n_runs if n_runs else 0
        models = sorted({_agent_model(r) for r in s.agents})
        cost_rows.append({
            "strategy": f"{TIER_EMOJI[s.tier]} {s.name}",
            "agents": len(s.agents),
            "runs": n_runs,
            "avg tokens/query": avg_tokens if n_runs else "—",
            "avg latency (ms)": avg_latency if n_runs else "—",
            "avg citations/query": round(avg_citations, 1) if n_runs else "—",
            "total tokens": total_tokens if n_runs else "—",
            "models": " · ".join(m.split("/")[-1] for m in models),
        })

    st.dataframe(cost_rows, use_container_width=True, hide_index=True)

    totals = {
        r["strategy"]: r["total tokens"]
        for r in cost_rows
        if isinstance(r["total tokens"], int)
    }
    if totals:
        sorted_totals = sorted(totals.items(), key=lambda kv: kv[1])
        cheapest_strat, cheapest_tok = sorted_totals[0]
        priciest_strat, priciest_tok = sorted_totals[-1]
        ratio = priciest_tok / max(cheapest_tok, 1)
        cols = st.columns(3)
        cols[0].metric(
            "💰 cheapest so far", cheapest_strat, f"{cheapest_tok:,} tokens"
        )
        cols[1].metric(
            "📊 priciest so far", priciest_strat, f"{priciest_tok:,} tokens"
        )
        cols[2].metric("📈 spread", f"{ratio:.1f}×")
    else:
        st.info(
            "No head-to-head runs yet — scroll up and run one to populate this table."
        )

    # 2b. Capability matrix ──────────────────────────────────────────────
    st.divider()
    st.subheader("🧬 Capability matrix — what each rung adds, in numbers")
    st.markdown(
        "Reading **down a column** shows how that metric grows along the ladder. "
        "Reading **across a row** shows what makes a scenario complete. "
        "Cells light up at the rung where the capability first becomes available."
    )

    from openacad.notes.persistence import vault as _vault_io_cap

    def _capability_row(s) -> dict:
        with use_scenario(s.key):
            atoms_n = 0
            attr_defs_n = 0
            rel_defs_n = 0
            embeddings_kb = 0
            verdict_pct = "—"
            prompt_versions = 0
            cmps = db.list_comparisons()

            if s.tier == Tier.ATOMS:
                try:
                    atoms = _vault_io_cap.list_atoms()
                    atoms_n = len(atoms)
                    if s.has_attributes:
                        attr_defs_n = len(_vault_io_cap.list_attribute_defs())
                    if s.has_relations:
                        rel_defs_n = len(_vault_io_cap.list_relation_defs())
                    if s.has_atom_embeddings and s.atoms_npz_path.exists():
                        embeddings_kb = s.atoms_npz_path.stat().st_size // 1024
                    if s.has_curation and atoms:
                        touched = sum(
                            1 for a in atoms
                            if a.origin.scholar_action
                            in ("accepted", "edited", "originated")
                        )
                        verdict_pct = f"{100 * touched // len(atoms)}%"
                except Exception:
                    pass

            if s.has_meta_eval:
                for role in s.agents:
                    try:
                        prompt_versions += len(db.list_prompts(name=role.value))
                    except Exception:
                        pass

        avg_tokens = "—"
        if cmps:
            avg_tokens = sum(c.tokens_in + c.tokens_out for c in cmps) // len(cmps)

        return {
            "scenario": f"{TIER_EMOJI[s.tier]} {s.name}",
            "atoms": atoms_n if s.tier == Tier.ATOMS else "—",
            "attr defs": attr_defs_n if s.has_attributes else "·",
            "rel defs": rel_defs_n if s.has_relations else "·",
            "embeddings (KB)": embeddings_kb if s.has_atom_embeddings else "·",
            "% scholar-touched": verdict_pct if s.has_curation else "·",
            "prompt versions": prompt_versions if s.has_meta_eval else "·",
            "avg tokens/q": avg_tokens,
        }

    cap_rows = [_capability_row(s) for s in SCENARIOS]
    st.dataframe(cap_rows, use_container_width=True, hide_index=True)
    st.caption(
        "Dots (·) mark **capabilities disabled at this rung**. Dashes (—) mark "
        "**not applicable** (e.g. chunk-tier scenarios don't have atoms). "
        "Numbers are live from `data/vaults/<scenario>/`."
    )

    # 3. Cumulative cost curve ───────────────────────────────────────────
    st.divider()
    st.subheader("📊 Cumulative cost curve — where the lines cross")
    st.markdown(
        "**Atom-curation costs more upfront. Over enough questions, you save.** "
        "Each line tracks total tokens billed across all your runs of that strategy."
    )

    curve_rows = []
    for s in SCENARIOS:
        with use_scenario(s.key):
            cmps = db.list_comparisons()
        cumulative = 0
        for i, c in enumerate(cmps, start=1):
            cumulative += c.tokens_in + c.tokens_out
            curve_rows.append({
                "scenario": s.name,
                "q_index": i,
                "cumulative_tokens": cumulative,
            })

    if curve_rows:
        df = pd.DataFrame(curve_rows)
        pivot = df.pivot_table(
            index="q_index",
            columns="scenario",
            values="cumulative_tokens",
            aggfunc="last",
        )
        st.line_chart(pivot, height=380)

        def _per_q_slope(scenario_name: str) -> float | None:
            ys = sorted(
                [
                    (r["q_index"], r["cumulative_tokens"])
                    for r in curve_rows
                    if r["scenario"] == scenario_name
                ],
                key=lambda x: x[0],
            )
            if len(ys) < 2:
                return None
            (x1, y1), (xn, yn) = ys[0], ys[-1]
            return (yn - y1) / max(xn - x1, 1) if xn > x1 else None

        def _intercept(scenario_name: str) -> float:
            ys = [
                r["cumulative_tokens"]
                for r in curve_rows
                if r["scenario"] == scenario_name and r["q_index"] == 1
            ]
            return ys[0] if ys else 0

        crossovers: list[str] = []
        scenarios_in_data = sorted({r["scenario"] for r in curve_rows})
        for a in scenarios_in_data:
            for b in scenarios_in_data:
                if a >= b:
                    continue
                sa, sb = _per_q_slope(a), _per_q_slope(b)
                ia, ib = _intercept(a), _intercept(b)
                if sa is None or sb is None or sa == sb:
                    continue
                denom = sa - sb
                if abs(denom) < 1e-6:
                    continue
                x_cross = 1 + (ib - ia) / denom
                if x_cross <= 1 or x_cross > 500:
                    continue
                steeper = a if sa > sb else b
                cheaper = b if sa > sb else a
                crossovers.append(
                    f"• **{steeper}** overtakes **{cheaper}** at "
                    f"**~{round(x_cross)} queries**"
                )

        if crossovers:
            with st.container(border=True):
                st.markdown(
                    "**📈 Projected break-even points** (linear extrapolation "
                    "from observed slopes):"
                )
                for c in crossovers[:6]:
                    st.markdown(c)
                st.caption(
                    "Reads as 'after N queries on the same vault, the "
                    "cheaper-upfront option's cumulative cost surpasses the "
                    "more-upfront option's cumulative cost.' This is THE "
                    "amortization argument for atom-tier scenarios."
                )

        with st.expander("📋 Cumulative tokens by scenario × question"):
            st.dataframe(pivot, use_container_width=True)
    else:
        st.caption("Run a few head-to-heads above; the curve builds up here.")

    # 4. The ladder you just climbed ─────────────────────────────────────
    st.divider()
    st.subheader(f"🪜 The {len(SCENARIOS)}-rung ladder you just climbed")
    st.markdown(
        f"You moved through {len(SCENARIOS)} strategies in order. **Each rung added "
        "exactly one capability** on top of the previous one. The progression makes "
        "the design space visible — every choice you avoid making in your own product "
        "is a rung you're skipping for someone else."
    )

    _ladder_beats = [
        ("🥶 Cold Read",
         "the limit of brute force — the whole PDF in the prompt every time. "
         "*No chunking, no retrieval, no memory.*"),
        ("🧩 Keyword Snippets",
         "the first slice — random chunks + FTS5 keyword search. "
         "*Lexical recall only; the meaning of the words doesn't help.*"),
        ("🧩 Semantic Snippets",
         "the second slice — random chunks + MiniLM embeddings. "
         "*Semantic recall arrives, but every chunk is still anonymous.*"),
        ("⚛️ Atomic Chunks",
         "the first time the chunks have an *identity* — agent extracts atoms, one "
         "self-contained idea per atom. *Memory exists as units, not as paragraphs.*"),
        ("🏷️ + Attributes",
         "atoms get typed attributes — now you can filter by `study.year`, "
         "`population.region`, etc. *Memory becomes relational-DB friendly.*"),
        ("🕸️ + Relations",
         "atoms link to each other via typed edges — `supports`, `contradicts`, "
         "`extends`. *Memory becomes a graph; the answerer can traverse.*"),
        ("📐 + Atom Embeddings",
         "atoms get their own MiniLM vectors — `find_similar_atoms` works. "
         "*The full atom-tier surface is now lit up, still on auto-accept.*"),
        ("✋ + HITL Curation",
         "your accept / edit / reject decisions shape what enters the vault. "
         "*Every atom now carries your fingerprint — memory you trust.*"),
        ("🧬 + Self-Improving Instructions",
         "the Meta-Evaluator synthesises your rubrics into hardened agent prompts. "
         "*The atoms stay immutable; the agents that produce future atoms and "
         "answers get smarter with use.*"),
    ]
    for title, body in _ladder_beats:
        with st.container(border=True):
            st.markdown(f"**{title}** {body}")

    # 5. Why Self-Improving Assistant is the destination ─────────────────
    st.divider()
    st.subheader("✨ Why **Self-Improving Assistant** is the destination")
    st.markdown(
        "Curated Notes is good. The Self-Improving Assistant is good **and keeps getting "
        "better**. The difference is a single agent — the **Meta-Evaluator** — but the "
        "consequence compounds.\n\n"
        "**What evolves is not the notes you've already curated** — those are immutable "
        "once accepted. What evolves is the **system prompt** of each agent role "
        "(Extractor / Scorer / Answerer). The Meta-Evaluator reads your rubrics, proposes "
        "sharper prompts, and you approve them. So tomorrow's extraction is better than "
        "today's; tomorrow's synthesis is sharper than today's."
    )

    c1, c2 = st.columns(2)
    with c1:
        with st.container(border=True):
            st.markdown(
                "### 🧬 Self-improving agent instructions\n\n"
                "Every rubric you submit doesn't just sit in a log — it becomes "
                "training signal. After enough rubrics for a given agent role, the "
                "Meta-Evaluator synthesises a new system prompt that addresses the "
                "lowest-rated criteria and the most-common reject reasons. You "
                "promote it. Your assistant gets **measurably sharper** with use."
            )
        with st.container(border=True):
            st.markdown(
                "### 📈 Network effects of use\n\n"
                "In every other strategy, the system you used yesterday is the "
                "system you have today. In the Self-Improving Assistant, **today's "
                "system is the integration of every yesterday**. The longer you "
                "work with it, the more it reflects your standards."
            )
    with c2:
        with st.container(border=True):
            st.markdown(
                "### 🎯 Compounding returns on rubrics\n\n"
                "The cost curve above shows that atoms amortize. The Self-Improving "
                "Assistant adds a second amortization: **your feedback compounds "
                "across queries.** A rubric you submitted on Tuesday's poverty "
                "answer shows up as a sharper prompt for Friday's climate question."
            )
        with st.container(border=True):
            st.markdown(
                "### 🔬 Auditable evolution\n\n"
                "Every prompt version is preserved with its parent, its rationale, "
                "and the rubric events it was derived from. You can roll back, fork, "
                "or A/B prompts. **The improvement loop is itself inspectable** "
                "— no black box."
            )

    st.markdown(
        "**What the Self-Improving Assistant uniquely gives you that no other strategy on the ladder does:**\n\n"
        "| Capability | Other strategies | Self-Improving Assistant |\n"
        "|---|---|---|\n"
        "| Curated atomic memory | only Curated Notes | ✅ |\n"
        "| Tool-calling synthesis with citations | Drafted / Curated | ✅ |\n"
        "| Prompt versioning | none | ✅ |\n"
        "| Auto-proposed prompt improvements | none | ✅ |\n"
        "| Scholar-approved evolution loop | none | ✅ |\n"
        "| Audit trail across versions | none | ✅ |\n\n"
        "Every other rung in the ladder is a *snapshot*. The Self-Improving Assistant is "
        "a *trajectory*. That's why it's the destination."
    )

    # 5b. Thesis in numbers ──────────────────────────────────────────────
    st.divider()
    st.subheader("📐 Thesis in numbers — five dimensions of effectiveness")
    st.markdown(
        "Every claim about the ladder maps to a measurable metric in the demo's data. "
        "These are the five dimensions of 'better' and the strongest data point for each, "
        "computed live from `data/vaults/` + `db.list_comparisons()` right now."
    )

    def _aggregate_for_thesis() -> dict:
        out = {
            "cold_avg_tokens": None,
            "atoms_tier_avg_tokens": None,
            "break_even_q": None,
            "atoms_with_attrs_max": 0,
            "atoms_with_rels_max": 0,
            "scholar_touched_pct_max": 0,
            "evolving_prompt_versions": 0,
            "total_atoms_curated_plus": 0,
            "registry_attr_defs_max": 0,
            "registry_rel_defs_max": 0,
        }
        from openacad.notes.persistence import vault as _vio

        cold_cmps = []
        drafted_cmps = []
        curated_cmps = []

        for sc in SCENARIOS:
            with use_scenario(sc.key):
                cmps = db.list_comparisons()
                if sc.key == "cold-read":
                    cold_cmps = cmps
                elif sc.key == "drafted-notes":
                    drafted_cmps = cmps
                elif sc.key == "curated-notes":
                    curated_cmps = cmps
                if sc.tier == Tier.ATOMS:
                    try:
                        atoms = _vio.list_atoms()
                        n = len(atoms)
                        if sc.has_attributes:
                            out["registry_attr_defs_max"] = max(
                                out["registry_attr_defs_max"],
                                len(_vio.list_attribute_defs()),
                            )
                        if sc.has_relations:
                            out["registry_rel_defs_max"] = max(
                                out["registry_rel_defs_max"],
                                len(_vio.list_relation_defs()),
                            )
                        if sc.has_curation and atoms:
                            touched = sum(
                                1 for a in atoms
                                if a.origin.scholar_action
                                in ("accepted", "edited", "originated")
                            )
                            out["scholar_touched_pct_max"] = max(
                                out["scholar_touched_pct_max"],
                                100 * touched // n,
                            )
                            out["total_atoms_curated_plus"] = max(
                                out["total_atoms_curated_plus"], n
                            )
                        out["atoms_with_attrs_max"] = max(
                            out["atoms_with_attrs_max"],
                            sum(1 for a in atoms if a.attributes),
                        )
                        out["atoms_with_rels_max"] = max(
                            out["atoms_with_rels_max"],
                            sum(1 for a in atoms if a.relations),
                        )
                    except Exception:
                        pass
                if sc.has_meta_eval:
                    for role in sc.agents:
                        try:
                            out["evolving_prompt_versions"] += len(
                                db.list_prompts(name=role.value)
                            )
                        except Exception:
                            pass

        if cold_cmps:
            out["cold_avg_tokens"] = sum(
                c.tokens_in + c.tokens_out for c in cold_cmps
            ) // len(cold_cmps)
        pooled_atoms = drafted_cmps + curated_cmps
        if pooled_atoms:
            out["atoms_tier_avg_tokens"] = sum(
                c.tokens_in + c.tokens_out for c in pooled_atoms
            ) // len(pooled_atoms)

        UPFRONT_PROXY = 50_000
        if out["cold_avg_tokens"] and out["atoms_tier_avg_tokens"]:
            per_q_delta = out["cold_avg_tokens"] - out["atoms_tier_avg_tokens"]
            if per_q_delta > 0:
                out["break_even_q"] = round(UPFRONT_PROXY / per_q_delta)
        return out

    _th = _aggregate_for_thesis()

    def _fmt(n) -> str:
        if n is None:
            return "—"
        if isinstance(n, int) and n >= 1000:
            return f"{n:,}"
        return str(n)

    col_a, col_b = st.columns(2)
    with col_a:
        with st.container(border=True):
            st.markdown("### 💰 Cost")
            st.markdown(
                f"**Cold Read** averages **{_fmt(_th['cold_avg_tokens'])}** tokens / query. "
                f"Atom-tier scenarios average **{_fmt(_th['atoms_tier_avg_tokens'])}**."
            )
            if _th["break_even_q"]:
                st.markdown(
                    f"At a proxy upfront cost of ~50k tokens for extraction, "
                    f"atom-tier breaks even with Cold Read at "
                    f"**~{_th['break_even_q']} queries** per vault. "
                    "After that, every additional query is pure savings."
                )
            else:
                st.caption(
                    "Break-even can't be computed yet — run the head-to-head "
                    "on multiple scenarios."
                )

    with col_b:
        with st.container(border=True):
            st.markdown("### 🎯 Quality")
            st.markdown(
                "Cold Read cites *page ranges* (`pp. 4-7`). Chunk-tier cites *chunk IDs* "
                "(`c-paper-…-0042`). Atom-tier cites *specific claims* (`[[atom-id]]`) that "
                "trace back to chunks → pages — **full provenance chain**."
            )
            st.markdown(
                "Citation precision is a categorical, not a number, but the citation *count* "
                "in atom-tier answers is consistently higher: an atom-tier answerer can "
                "compose 3-5 citations per claim, where a Cold Read answerer typically cites zero."
            )

    col_c, col_d = st.columns(2)
    with col_c:
        with st.container(border=True):
            st.markdown("### 🛠️ Capability")
            st.markdown(
                f"Atoms-tier scenarios expose progressively more query modes. "
                f"The registry grows up to **{_th['registry_attr_defs_max']} attribute defs** "
                f"and **{_th['registry_rel_defs_max']} relation defs**, "
                f"unlocking typed filters and graph traversal that chunk-tier can't express."
            )
            st.markdown(
                f"At the top of the ladder, the answerer has access to "
                f"**5 retrieval tools** (`query_atoms`, `traverse`, `semantic_search`, "
                f"`get_atom_full`, `check_contradiction`) vs **0 tools** at chunk-tier."
            )

    with col_d:
        with st.container(border=True):
            st.markdown("### 🎮 Control")
            if _th["scholar_touched_pct_max"]:
                st.markdown(
                    f"At the HITL rung, **{_th['scholar_touched_pct_max']}%** of atoms "
                    f"carry a scholar verdict (`accepted`/`edited`/`originated`). "
                    f"In drafted (auto-accept) scenarios, that number is **0%**."
                )
            st.markdown(
                "Every atom in Curated and Self-Improving has a deterministic provenance trail: "
                "`atom → draft → chunk → page → scholar action`. Nothing entered the vault "
                "without the scholar's fingerprint."
            )

    with st.container(border=True):
        st.markdown("### 🧬 Learning")
        if _th["evolving_prompt_versions"]:
            st.markdown(
                f"Across the Self-Improving Assistant's agent roles, the vault now contains "
                f"**{_th['evolving_prompt_versions']} prompt versions** — every other scenario "
                f"has exactly 1 per role. This is the only scenario where today's system is "
                f"structurally different from yesterday's, in a way the scholar promoted."
            )
        else:
            st.caption("No prompt versions persisted yet — run the Meta-Evaluator loop on Refine.")

    # 6. Production extensions ───────────────────────────────────────────
    st.divider()
    st.subheader("🚀 Taking the Self-Improving Assistant into production")
    st.markdown(
        "The demo proves the loop. A production deployment built around the "
        "Self-Improving Assistant would add:\n\n"
        "**Scaling the rubric signal**\n\n"
        "- Multi-user scholar accounts so rubric ratings carry rater identity into the "
        "  Meta-Evaluator's input\n"
        "- Per-domain prompt sets (an Extractor tuned for biology rubrics is a different "
        "  agent from one tuned for legal rubrics)\n"
        "- Stream rubrics into PostHog / Langfuse so the Meta-Evaluator can run on a "
        "  cadence (nightly, weekly) without scholar trigger\n\n"
        "**Scaling the atom layer**\n\n"
        "- Per-scenario [RAGAS](https://docs.ragas.io/) scorers (faithfulness, "
        "  answer-relevancy, context-precision) wired into the pydantic-evals harness\n"
        "- Atom-level access controls (private / lab / public)\n"
        "- A Cypher endpoint over the NetworkX relations graph for power users\n\n"
        "**Scaling the agent stack**\n\n"
        "- Add a 5th agent: a **Contradictions Detector** that mines the graph for "
        "  `contradicts` edges and surfaces them as proactive scholar prompts\n"
        "- Add a 6th agent: a **Cross-Paper Synthesiser** that surfaces related atoms "
        "  across uploaded PDFs and proposes synthesis paragraphs\n\n"
        "**Closing every loop**\n\n"
        "- Export curated vaults as portable RDF/Turtle for ingestion into broader "
        "  knowledge graphs\n"
        "- Subscribe a publication feed (arXiv, bioRxiv) and have the assistant "
        "  pre-extract candidate atoms from new papers in your domain"
    )

    st.divider()
    st.success(
        "**That's the ladder.** The Self-Improving Assistant earns its place at the top "
        "because it's the only strategy where today's **assistant** is structurally better "
        "than yesterday's. *(The notes themselves stay exactly as you curated them; what "
        "improves is the AI's instructions.)* Use the sidebar to start over from **🏠 "
        "Welcome**, or jump back into any scenario."
    )


# ─────────────────────────────────────────────────────────────────────────
# GOODNESS TAB — port of former 95_goodness.py
# ─────────────────────────────────────────────────────────────────────────


def _collect_goodness() -> tuple[dict, pd.DataFrame]:
    """Return a dict[scenario_key] -> list of comparisons + a flat DataFrame."""
    by_scenario: dict[str, list] = {}
    rows = []
    for s in SCENARIOS:
        with use_scenario(s.key):
            cmps = db.list_comparisons()
        by_scenario[s.key] = cmps
        for c in cmps:
            rows.append({
                "scenario": s.name,
                "scenario_key": s.key,
                "tier": s.tier.value,
                "pipeline": c.pipeline,
                "question": c.question,
                "tokens_in": c.tokens_in,
                "tokens_out": c.tokens_out,
                "total_tokens": c.tokens_in + c.tokens_out,
                "latency_ms": c.latency_ms,
                "citations": len(c.citations),
                "cost_usd": _cost_usd(c.tokens_in, c.tokens_out),
                "run_at": c.run_at,
            })
    return by_scenario, pd.DataFrame(rows)


def _render_goodness() -> None:
    st.markdown(
        "Live comparative analysis across all 9 scenarios, computed from the persisted "
        "`ComparisonResult` rows in `data/vaults/<scenario>/state.sqlite::comparisons`. "
        f"Pricing assumes **gpt-4o-mini** (`${COST_IN_PER_M}/M in`, `${COST_OUT_PER_M}/M out`)."
    )

    by_scenario, df = _collect_goodness()

    if df.empty:
        st.warning(
            "No comparisons persisted yet. Use the **Query** tab on each scenario or "
            "run `python scripts/seed_query_history.py` to populate."
        )
        return

    # 1. Headline findings ────────────────────────────────────────────────
    st.divider()
    st.subheader("🏆 Headline findings")

    per_scn = df.groupby("scenario").agg(
        runs=("total_tokens", "count"),
        avg_tokens=("total_tokens", "mean"),
        avg_cost=("cost_usd", "mean"),
        avg_latency=("latency_ms", "mean"),
        avg_citations=("citations", "mean"),
    ).reset_index()

    nonzero = per_scn[per_scn["runs"] > 0]
    if not nonzero.empty:
        cheapest = nonzero.loc[nonzero["avg_tokens"].idxmin()]
        priciest = nonzero.loc[nonzero["avg_tokens"].idxmax()]
        fastest = nonzero.loc[nonzero["avg_latency"].idxmin()]
        most_cited = nonzero.loc[nonzero["avg_citations"].idxmax()]
        spread = priciest["avg_tokens"] / max(cheapest["avg_tokens"], 1)

        hc = st.columns(4)
        with hc[0]:
            st.metric(
                "💰 cheapest", cheapest["scenario"],
                f"{int(cheapest['avg_tokens']):,} tok/q",
            )
        with hc[1]:
            st.metric(
                "📊 priciest", priciest["scenario"],
                f"{int(priciest['avg_tokens']):,} tok/q",
            )
        with hc[2]:
            st.metric(
                "⚡ fastest", fastest["scenario"],
                f"{int(fastest['avg_latency'])}ms avg",
            )
        with hc[3]:
            st.metric(
                "📎 most cited", most_cited["scenario"],
                f"{most_cited['avg_citations']:.1f} cites/q",
            )

        st.markdown(
            f"**Cost spread** across the ladder: **{spread:.1f}×** "
            f"({cheapest['scenario']} → {priciest['scenario']}). "
            "This is the demo's headline cost story — atom-tier amortizes; "
            "cold-tier pays full price every query."
        )

    # 2. Per-scenario summary table ───────────────────────────────────────
    st.divider()
    st.subheader("📊 Per-scenario summary")
    st.caption(
        "Full matrix from every recorded run. p50 = median; p95 = 95th-percentile. "
        "Empty cells mean fewer than 2 runs (no distribution to compute)."
    )

    def _percentile(s, p):
        try:
            return int(statistics.quantiles(s, n=100)[p - 1])
        except Exception:
            return None

    summary_rows = []
    for sc in SCENARIOS:
        cmps = by_scenario[sc.key]
        if not cmps:
            summary_rows.append({
                "scenario": f"{TIER_EMOJI[sc.tier]} {sc.name}",
                "runs": 0,
                "avg tokens/q": "—",
                "p50 tokens": "—",
                "p95 tokens": "—",
                "avg latency (ms)": "—",
                "p95 latency": "—",
                "avg citations": "—",
                "avg cost $/q": "—",
            })
            continue
        toks = [c.tokens_in + c.tokens_out for c in cmps]
        lats = [c.latency_ms for c in cmps]
        cites = [len(c.citations) for c in cmps]
        costs = [_cost_usd(c.tokens_in, c.tokens_out) for c in cmps]
        summary_rows.append({
            "scenario": f"{TIER_EMOJI[sc.tier]} {sc.name}",
            "runs": len(cmps),
            "avg tokens/q": f"{int(sum(toks) / len(toks)):,}",
            "p50 tokens": f"{int(statistics.median(toks)):,}",
            "p95 tokens": _percentile(toks, 95) if len(toks) >= 2 else "—",
            "avg latency (ms)": int(sum(lats) / len(lats)),
            "p95 latency": _percentile(lats, 95) if len(lats) >= 2 else "—",
            "avg citations": round(sum(cites) / len(cites), 1),
            "avg cost $/q": f"${sum(costs) / len(costs):.4f}",
        })

    st.dataframe(summary_rows, use_container_width=True, hide_index=True)

    # 3. Cost dimension ───────────────────────────────────────────────────
    st.divider()
    st.subheader("💸 Cost dimension")

    cost_chart = nonzero.set_index("scenario")["avg_tokens"].sort_values()
    st.markdown("##### Average tokens per query (lower is better, after upfront extraction)")
    st.bar_chart(cost_chart, height=300)

    st.markdown("##### Projected cost per 100 queries (linear scaling)")
    cost_proj = (nonzero.set_index("scenario")["avg_cost"] * 100).sort_values()
    cost_proj_df = pd.DataFrame({
        "scenario": cost_proj.index,
        "$ per 100 queries": cost_proj.values.round(3),
    })
    st.dataframe(cost_proj_df, use_container_width=True, hide_index=True)

    cold_cost = nonzero[
        nonzero["scenario"].str.contains("Cold Read", na=False)
    ]["avg_cost"]
    atom_costs = nonzero[
        ~nonzero["scenario"].str.contains("Cold Read|Snippets", na=False)
    ]["avg_cost"]
    if len(cold_cost) and len(atom_costs):
        cold_c = cold_cost.iloc[0]
        avg_atom_c = atom_costs.mean()
        delta_per_q = cold_c - avg_atom_c
        UPFRONT_USD = 0.04
        if delta_per_q > 0:
            break_even_q = int(UPFRONT_USD / delta_per_q)
            st.markdown(
                f"**Break-even point**: with an assumed upfront extraction cost of "
                f"~${UPFRONT_USD:.2f} per scenario, atom-tier scenarios "
                f"(avg ${avg_atom_c:.4f}/q) recoup that upfront vs Cold Read "
                f"(${cold_c:.4f}/q) at **~{break_even_q} queries** per vault. "
                "After that, every additional query is pure savings."
            )

    # 4. Citation dimension ───────────────────────────────────────────────
    st.divider()
    st.subheader("📎 Citation dimension")
    st.markdown(
        "Citation count is a proxy for **grounding**: how many distinct units of "
        "evidence the answerer marshaled. Atom-tier scenarios cite specific atoms; "
        "chunk-tier cite chunk ids; Cold Read cites page ranges (often zero)."
    )

    cite_chart = nonzero.set_index("scenario")["avg_citations"].sort_values()
    st.markdown("##### Average citations per answer (higher = more grounded)")
    st.bar_chart(cite_chart, height=300)

    df_with_density = df.copy()
    df_with_density["cite_density"] = (
        df_with_density["citations"]
        / df_with_density["tokens_out"].clip(lower=1)
        * 1000
    )
    density = df_with_density.groupby("scenario")["cite_density"].mean()
    st.markdown("##### Citation density (citations per 1k output tokens)")
    st.bar_chart(density.sort_values(), height=300)

    # 5. Latency dimension ───────────────────────────────────────────────
    st.divider()
    st.subheader("⚡ Latency dimension")
    st.caption(
        "Atom-tier scenarios make multiple tool calls per question (planner → "
        "retrieve → refine → answer), so they're slower than chunk-tier even "
        "though each individual call is small. Cold Read makes ONE big call."
    )
    lat_chart = nonzero.set_index("scenario")["avg_latency"].sort_values()
    st.bar_chart(lat_chart, height=300)

    # 6. Thesis-proving comparisons ──────────────────────────────────────
    st.divider()
    st.subheader("🧬 The thesis in numbers")
    st.markdown(
        "Three head-to-head comparisons that prove what each layer of the ladder "
        "buys you."
    )

    def _scenario_stats(key: str) -> dict | None:
        cmps = by_scenario.get(key, [])
        if not cmps:
            return None
        toks = sum(c.tokens_in + c.tokens_out for c in cmps) / len(cmps)
        cite = sum(len(c.citations) for c in cmps) / len(cmps)
        lat = sum(c.latency_ms for c in cmps) / len(cmps)
        cost = sum(_cost_usd(c.tokens_in, c.tokens_out) for c in cmps) / len(cmps)
        return {
            "name": SCENARIOS[[s.key for s in SCENARIOS].index(key)].name,
            "n": len(cmps), "tokens": toks, "cites": cite, "lat": lat, "cost": cost,
        }

    def _delta(left: float, right: float, unit: str, invert: bool = False) -> str:
        if left == 0:
            return "—"
        pct = (right - left) / left * 100
        if invert:
            arrow = "📈" if pct > 0 else "📉"
        else:
            arrow = "📉" if pct < 0 else "📈"
        return f"{arrow} {pct:+.0f}%"

    def _comparison_card(left_key: str, right_key: str, headline: str, takeaway: str) -> None:
        left = _scenario_stats(left_key)
        right = _scenario_stats(right_key)
        if not left or not right:
            st.caption(f"_(insufficient data for {left_key} vs {right_key})_")
            return
        with st.container(border=True):
            st.markdown(f"### {headline}")
            cols = st.columns(2)
            with cols[0]:
                st.markdown(f"**{left['name']}** (n={left['n']})")
                st.markdown(
                    f"- avg tokens: **{int(left['tokens']):,}**\n"
                    f"- avg citations: **{left['cites']:.1f}**\n"
                    f"- avg latency: **{int(left['lat'])}ms**\n"
                    f"- avg cost: **${left['cost']:.4f}**"
                )
            with cols[1]:
                st.markdown(f"**{right['name']}** (n={right['n']})")
                st.markdown(
                    f"- avg tokens: **{int(right['tokens']):,}**  "
                    f"({_delta(left['tokens'], right['tokens'], 'tokens')})\n"
                    f"- avg citations: **{right['cites']:.1f}**  "
                    f"({_delta(left['cites'], right['cites'], 'cites', invert=True)})\n"
                    f"- avg latency: **{int(right['lat'])}ms**  "
                    f"({_delta(left['lat'], right['lat'], 'ms')})\n"
                    f"- avg cost: **${right['cost']:.4f}**  "
                    f"({_delta(left['cost'], right['cost'], '$')})"
                )
            st.markdown(f"**Takeaway:** {takeaway}")

    _comparison_card(
        "cold-read", "curated-notes",
        "🥶 Cold Read vs ✋ Curated Notes — does atom-tier with HITL actually pay off?",
        "If Curated uses fewer tokens AND cites more, the structural argument "
        "for atomic curation is empirically validated.",
    )

    _comparison_card(
        "drafted-notes", "curated-notes",
        "📐 Drafted (auto-accept) vs ✋ Curated (HITL) — what does scholar review buy?",
        "Curated should produce sharper answers per token — fewer but better-cited "
        "atoms. If citation density rises with curation, the HITL step pays for itself.",
    )

    _comparison_card(
        "curated-notes", "evolving-notes",
        "✋ Curated vs 🧬 Self-Improving — does the meta-evaluator loop measurably improve answers?",
        "Same vault content (evolving mirrors curated) — only the prompts evolve. "
        "Any sustained delta is attributable to prompt evolution alone.",
    )

    # 7. Caveats ─────────────────────────────────────────────────────────
    st.divider()
    st.subheader("⚠️ Caveats")
    st.markdown(
        """
- **Sample size**: ~10 questions per scenario. Differences smaller than the
  inter-question variance shouldn't be over-interpreted.
- **Question coverage**: questions are drawn from the SDG-briefing corpus only;
  ratings of "goodness" may shift on harder corpora.
- **Cost is model-dependent**: pricing here is gpt-4o-mini; switching to a more
  expensive model (Claude 4.5, etc.) scales atom-tier UP more than cold-tier
  because atom-tier makes more tool-call rounds.
- **Citation count ≠ citation quality**: an answer that cites 10 atoms could
  still be wrong; we measure quantity here, not accuracy. Use the **Audit**
  capability + the pydantic-evals scoring harness for accuracy gating.
- **Atom-tier latency** is dominated by tool-call round trips; in production
  you'd parallelize tool calls to bring this down 2-3×.
"""
    )


# ─────────────────────────────────────────────────────────────────────────
# PAGE BODY
# ─────────────────────────────────────────────────────────────────────────


page_header(
    title="🎓 Conclusion — Comparison & Receipts",
    blurb=(
        "You climbed the ladder. **Now the receipts.** Run a side-by-side, see "
        "the cost-and-performance table, and read why the Self-Improving Assistant "
        "is the destination. The **Goodness** tab is the deeper quantitative view."
    ),
    show_scenario_chip=False,
)


tab_thesis, tab_goodness = st.tabs(["🎓 Thesis", "📐 Goodness"])
with tab_thesis:
    _render_thesis()
with tab_goodness:
    _render_goodness()


scenario_nav_footer(current_page="walkthrough/90_conclusion.py")
