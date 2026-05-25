"""pydantic-evals scoring openacad.runtime over gold datasets."""

from openacad.feedback.scoring._harness import (
    QueryInputs,
    AnswerOutput,
    CitationPresent,
    TokenCost,
    LatencyMs,
    CitationPrecision,
    RubricAggregate,
    dataset_path,
    results_path,
    load_dataset,
    save_dataset,
    run_scoring,
)

__all__ = [
    "QueryInputs", "AnswerOutput",
    "CitationPresent", "TokenCost", "LatencyMs", "CitationPrecision", "RubricAggregate",
    "dataset_path", "results_path", "load_dataset", "save_dataset", "run_scoring",
]
