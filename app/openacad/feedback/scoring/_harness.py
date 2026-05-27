"""pydantic-evals openacad.runtime over the 6 scenarios.

Each scenario has a `scoring/dataset.yaml` with Cases (question + expected_output).
`run_scoring(scenario_key)` answers every case via that scenario's pipeline,
applies scorers (LLMJudge for accuracy, CitationPrecision, TokenCost,
RubricAggregate), and writes a `EvaluationReport` to disk.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pydantic import BaseModel
from pydantic_evals import Case, Dataset
from pydantic_evals.evaluators import Evaluator, EvaluatorContext

from openacad.runtime.scenario import AgentRole, active_scenario, use_scenario
from openacad.runtime import db
from openacad.feedback import rubric
# ── inputs / outputs for cases ──────────────────────────────────────────


class QueryInputs(BaseModel):
    question: str
    paper_ids: list[str] = []


class AnswerOutput(BaseModel):
    answer: str
    cited_units: list[str] = []        # atom ids OR chunk ids OR paper ids depending on tier
    tokens_in: int = 0
    tokens_out: int = 0
    latency_ms: int = 0


# ── custom scorers ──────────────────────────────────────────────────────


@dataclass
class CitationPresent(Evaluator[QueryInputs, AnswerOutput]):
    """1.0 if the answer includes at least one citation; 0.0 otherwise."""

    def evaluate(self, ctx: EvaluatorContext[QueryInputs, AnswerOutput]) -> float:
        return 1.0 if ctx.output.cited_units else 0.0


@dataclass
class TokenCost(Evaluator[QueryInputs, AnswerOutput]):
    """Reports total tokens (input + output) as the score. Lower is better."""

    def evaluate(self, ctx: EvaluatorContext[QueryInputs, AnswerOutput]) -> int:
        return ctx.output.tokens_in + ctx.output.tokens_out


@dataclass
class LatencyMs(Evaluator[QueryInputs, AnswerOutput]):
    def evaluate(self, ctx: EvaluatorContext[QueryInputs, AnswerOutput]) -> int:
        return ctx.output.latency_ms


@dataclass
class CitationPrecision(Evaluator[QueryInputs, AnswerOutput]):
    """Fraction of cited atoms that actually exist in the active scenario's vault.
    Always 1.0 for chunk-tier scenarios (citations are chunk ids; we don't verify)."""

    def evaluate(self, ctx: EvaluatorContext[QueryInputs, AnswerOutput]) -> float:
        if not ctx.output.cited_units:
            return 1.0
        from openacad.notes.persistence import vault as vault_io
        present = 0
        total = 0
        for cid in ctx.output.cited_units:
            total += 1
            # Heuristic: atom ids start with "20" (date prefix) or are kebab-case
            # without leading "c-" (chunk) or "paper-" (source) prefix.
            if cid.startswith("c-") or cid.startswith("paper-"):
                present += 1  # not an atom; nothing to verify
                continue
            try:
                vault_io.read_atom(cid)
                present += 1
            except Exception:
                pass
        return present / total if total else 1.0


@dataclass
class RubricAggregate(Evaluator[QueryInputs, AnswerOutput]):
    """Latest rubric average for the Answerer in the active scenario.
    Reads from the rubrics table; if none yet, returns None (no score)."""

    role: AgentRole = AgentRole.ANSWERER

    def evaluate(self, ctx: EvaluatorContext[QueryInputs, AnswerOutput]) -> float | None:
        stats = rubric.role_average(self.role)
        return stats["overall_avg"]


# ── dataset I/O ─────────────────────────────────────────────────────────


def dataset_path() -> Path:
    return active_scenario().scoring_dir / "dataset.yaml"


def results_path() -> Path:
    return active_scenario().scoring_dir / "results.json"


def load_dataset() -> Dataset[QueryInputs, AnswerOutput]:
    path = dataset_path()
    if not path.exists():
        raise FileNotFoundError(
            f"no dataset at {path}; run scripts/seed_scoring_datasets.py first"
        )
    return Dataset[QueryInputs, AnswerOutput].from_file(
        path,
        custom_evaluator_types=[
            CitationPresent, TokenCost, LatencyMs,
            CitationPrecision, RubricAggregate,
        ],
    )


def save_dataset(ds: Dataset) -> None:
    path = dataset_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    ds.to_file(path)


# ── run scoring for the active scenario ─────────────────────────────────


def run_scoring(scenario_key: str) -> dict[str, Any]:
    """Answer every case via the scenario's pipeline; score; persist; return report dict."""
    from openacad.runtime import dispatcher as scenario_runtime

    with use_scenario(scenario_key):
        ds = load_dataset()

        async def task(inputs: QueryInputs) -> AnswerOutput:
            return await scenario_runtime.ask_async(inputs.question, inputs.paper_ids)

        report = ds.evaluate_sync(task)

        # Persist a JSON summary so the Streamlit page can render history.
        summary = _summarize_report(report)
        out = results_path()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
        return summary


def _summarize_report(report) -> dict[str, Any]:
    """Flatten pydantic-evals report into a JSON-serializable dict."""
    cases_out: list[dict] = []
    for c in report.cases:
        scores = {}
        # report case structure: c.scores is dict of {name: ScoreResult}
        if hasattr(c, "scores"):
            for name, sc in c.scores.items():
                val = getattr(sc, "value", sc)
                scores[name] = val
        cases_out.append({
            "name": c.name,
            "inputs": c.inputs.model_dump() if hasattr(c.inputs, "model_dump") else c.inputs,
            "output": c.output.model_dump() if hasattr(c.output, "model_dump") else c.output,
            "scores": scores,
        })
    return {"cases": cases_out, "n_cases": len(cases_out)}
