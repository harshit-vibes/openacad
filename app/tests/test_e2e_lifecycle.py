"""End-to-end tests over the full Streamlit walkthrough surface.

Real data + real LLM calls (when key is set). Exercises:

1. Shared sources are visible from any scenario
2. Atom-tier scenarios have seeded atoms
3. Each scenario can answer a question via its pipeline
4. Rubrics are recorded
5. Comparisons are persisted (used by the Amortization page)
6. Scoring runs over the dataset and persists a report
7. Meta-Evaluator proposes a new prompt after ≥N rubrics; promote works

Run with:
    cd ~/Documents/openacad/demo
    .venv/bin/python -m pytest tests/test_e2e_lifecycle.py -v
"""

from __future__ import annotations

import json
import uuid

import pytest

from openacad.runtime.scenario import SCENARIOS, AgentRole, Tier, use_scenario
from openacad.runtime import db
from openacad.feedback import rubric
# ── 1. Sources are SHARED across scenarios ──────────────────────────────


def test_sources_shared_across_scenarios():
    sources_seen = {}
    for s in SCENARIOS:
        with use_scenario(s.key):
            sources_seen[s.key] = [src.id for src in db.list_sources()]
    # Every scenario sees the same set
    first = sorted(next(iter(sources_seen.values())))
    for sk, srcs in sources_seen.items():
        assert sorted(srcs) == first, f"{sk} sees different sources"
    assert len(first) >= 1, "no sources ingested — run scripts/seed_scenarios.py first"


# ── 2. Atom-tier scenarios have seeded atoms ────────────────────────────


def test_atom_scenarios_have_seeded_atoms():
    """curated-notes and evolving-notes should have ≥7 seeded atoms after seed_scenarios."""
    for key in ("curated-notes", "evolving-notes"):
        with use_scenario(key):
            n = len(db.list_atom_projections())
        assert n >= 7, f"{key} has {n} atoms; expected ≥7"


def test_atoms_reference_real_sources():
    """Every atom's `origin.source_id` must be either None (hand-seeded with no source)
    OR match an actually-ingested PaperSource. Guards against the class of bug where
    atom seeds drift away from the live PDF corpus.
    """
    from openacad.notes.persistence import vault as vault_io
    sources = {src.id for src in db.list_sources()}
    for key in ("curated-notes", "evolving-notes"):
        with use_scenario(key):
            atoms = vault_io.list_atoms()
            orphans = []
            for a in atoms:
                sid = a.origin.source_id
                if sid is None:
                    continue  # explicit "no source" is fine
                if sid not in sources:
                    orphans.append((a.metas.id, sid))
            assert not orphans, (
                f"{key} has atoms with origin.source_id pointing at non-ingested PDFs:\n"
                + "\n".join(f"  {aid}  →  {sid!r}" for aid, sid in orphans)
                + f"\nAvailable source ids: {sorted(sources)}"
            )


# ── 3. Each scenario can answer a question via its pipeline ─────────────


@pytest.mark.parametrize("scenario_key", [s.key for s in SCENARIOS])
def test_each_scenario_answers(scenario_key, llm_required, sample_question):
    """Real LLM call; verify the pipeline returns an AnswerOutput shape."""
    from openacad.runtime.dispatcher import ask
    with use_scenario(scenario_key):
        s = next(s for s in SCENARIOS if s.key == scenario_key)
        # Skip drafted-notes if it has no atoms yet (extraction-dependent)
        if s.tier == Tier.ATOMS and not db.list_atom_projections():
            pytest.skip(f"{scenario_key} has no atoms yet (run prepare)")
        out = ask(sample_question, paper_ids=[])
    assert out.answer and len(out.answer) > 20, f"{scenario_key} returned empty answer"
    assert out.tokens_in > 0, f"{scenario_key} reported zero tokens_in"


# ── 4. Rubrics are recorded and aggregate correctly ─────────────────────


def test_rubric_record_and_aggregate():
    """Independent of LLM — just verifies the rubric persistence layer."""
    with use_scenario("curated-notes"):
        before = rubric.role_average(AgentRole.ANSWERER)
        r = rubric.Rubric(
            role=AgentRole.ANSWERER,
            target_id=f"test-{uuid.uuid4().hex[:6]}",
            overall=5,
            criteria={"accuracy": 5, "citation_quality": 5, "conciseness": 4},
            free_text="Test rubric from pytest.",
        )
        rubric.record(r)
        after = rubric.role_average(AgentRole.ANSWERER)
    assert after["count"] == before["count"] + 1
    assert after["overall_avg"] is not None


# ── 5. compare_service persists a ComparisonResult ──────────────────────


def test_compare_persists_per_scenario(llm_required, sample_question):
    """Run cold-read + semantic-snippets on one question; both write a comparison row."""
    from openacad.runtime.dispatcher import ask
    from openacad.feedback.schema import ComparisonResult
    from datetime import datetime, timezone

    sources = []
    # Use only the SDG ch02 paper to keep token cost low
    with use_scenario("cold-read"):
        sources = [s.id for s in db.list_sources() if "ch02" in s.id]
    if not sources:
        pytest.skip("no SDG ch02 source ingested")

    for key in ("cold-read", "semantic-snippets"):
        with use_scenario(key):
            out = ask(sample_question, paper_ids=sources)
            cr = ComparisonResult(
                id=f"cmp-test-{uuid.uuid4().hex[:6]}",
                question=sample_question,
                paper_ids=sources,
                pipeline={"cold-read": "B0", "semantic-snippets": "B1"}[key],
                answer=out.answer,
                citations=out.cited_units,
                tokens_in=out.tokens_in,
                tokens_out=out.tokens_out,
                latency_ms=out.latency_ms,
                n_units_retrieved=len(out.cited_units),
                run_at=datetime.now(timezone.utc),
            )
            db.insert_comparison(cr)
            assert any(c.id == cr.id for c in db.list_comparisons())


# ── 6. Scoring openacad.runtime runs over a tiny subset and persists results ─────


def test_scoring_runs_minimal(llm_required):
    """Run pydantic-evals on cold-read with the first case only (to keep cost low)."""
    from openacad.feedback import scoring as scoring_harness
    import yaml
    with use_scenario("cold-read"):
        ds_path = scoring_harness.dataset_path()
        results_path = scoring_harness.results_path()
        if not ds_path.exists():
            pytest.skip("no scoring dataset; run scripts/seed_scoring_datasets.py")

        # Trim the dataset to a single case for the test
        raw = yaml.safe_load(ds_path.read_text())
        original = list(raw["cases"])
        raw["cases"] = original[:1]
        ds_path.write_text(yaml.safe_dump(raw, sort_keys=False))
        try:
            report = scoring_harness.run_scoring("cold-read")
        finally:
            # restore
            raw["cases"] = original
            ds_path.write_text(yaml.safe_dump(raw, sort_keys=False))

    assert report["n_cases"] == 1
    res = json.loads(results_path.read_text())
    assert res["n_cases"] == 1
    assert "scores" in res["cases"][0]


# ── 7. Meta-Evaluator: log N rubrics → propose → promote ────────────────


def test_meta_eval_propose_and_promote(llm_required):
    """Insert enough rubrics so the Meta-Evaluator triggers; verify proposal + promote."""
    from openacad.runtime.settings import settings
    from openacad.agents.meta_evaluator import agent as meta_evaluator
    from openacad.runtime import agent_base as agent_factory

    with use_scenario("evolving-notes"):
        # Pad rubrics up to threshold
        current = rubric.role_average(AgentRole.ANSWERER)["count"]
        needed = max(0, settings.prompt_regen_threshold - current)
        for i in range(needed):
            rubric.record(rubric.Rubric(
                role=AgentRole.ANSWERER,
                target_id=f"pad-{i}-{uuid.uuid4().hex[:4]}",
                overall=3 if i % 2 == 0 else 4,
                criteria={"accuracy": 3, "citation_quality": 3, "conciseness": 4},
                free_text=f"Padded rubric #{i} for meta-eval test.",
            ))

        proposal = meta_evaluator.propose_new_prompt(AgentRole.ANSWERER)
        assert proposal is not None, "Meta-Evaluator should have produced a proposal"
        assert proposal.new_version.startswith("answerer.v")
        assert len(proposal.body) > 30
        assert proposal.rationale

        # The proposal is persisted as state=proposed
        prompts = db.list_prompts(name="answerer")
        proposed = [p for p in prompts if p.version == proposal.new_version]
        assert proposed and proposed[0].state == "proposed"

        # Promote it
        result = meta_evaluator.promote_prompt(proposal.new_version)
        assert result["ok"] is True

        # Active prompt is now the new one
        active = [p for p in db.list_prompts(name="answerer") if p.state == "active"]
        assert any(p.version == proposal.new_version for p in active), \
            f"expected {proposal.new_version} active; got {[p.version for p in active]}"

        # Cache busted — next agent build picks up the new prompt
        agent = agent_factory.build_answerer()
        assert agent is not None
