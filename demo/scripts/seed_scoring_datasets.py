"""Write a pydantic-evals Dataset YAML for every scenario with the same 5 questions.

The same dataset across scenarios means every scenario answers the same Cases
and can be compared head-to-head on the same scorers.
"""

import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from openacad.runtime.scenario import SCENARIOS, use_scenario


SHARED_CASES = [
    {
        "name": "q-001-poverty-strategies",
        "inputs": {
            "question": "What are the main strategies the briefing recommends for ending poverty (SDG 1)?",
            "paper_ids": ["paper-sdg-briefing-ch02-sdg-1-5-people"],
        },
        "expected_output": {
            "answer": (
                "The briefing recommends a multidimensional approach: enhance economic "
                "opportunities, improve education, extend social protection. Specifically: "
                "eradicate extreme poverty (<$1.25/day), halve proportional poverty, build "
                "nationally appropriate social protection systems, equalize rights to "
                "economic resources, build resilience to disasters, mobilize resources, "
                "and create sound policy frameworks."
            ),
            "cited_units": [],
            "tokens_in": 0, "tokens_out": 0, "latency_ms": 0,
        },
        "metadata": {"category": "policy-summary", "difficulty": "easy"},
    },
    {
        "name": "q-002-gender-targets",
        "inputs": {
            "question": "What targets does SDG 5 (gender equality) include?",
            "paper_ids": ["paper-sdg-briefing-ch02-sdg-1-5-people"],
        },
        "expected_output": {
            "answer": (
                "SDG 5 targets include: ending discrimination against women and girls; "
                "eliminating violence in public and private spheres; eliminating harmful "
                "practices such as child marriage and FGM; recognizing unpaid care/domestic "
                "work; ensuring women's full participation in decision-making and leadership; "
                "universal access to reproductive health rights; and ensuring equal economic "
                "rights and access to resources."
            ),
            "cited_units": [],
            "tokens_in": 0, "tokens_out": 0, "latency_ms": 0,
        },
        "metadata": {"category": "policy-summary", "difficulty": "easy"},
    },
    {
        "name": "q-003-malnutrition-cases",
        "inputs": {
            "question": "What case studies are mentioned for reducing malnutrition or wasting in children?",
            "paper_ids": ["paper-sdg-briefing-ch02-sdg-1-5-people"],
        },
        "expected_output": {
            "answer": (
                "The briefing highlights training parents as the easiest way to monitor "
                "wasting, plus local initiatives that have widespread impacts on hunger "
                "and child nutrition outcomes."
            ),
            "cited_units": [],
            "tokens_in": 0, "tokens_out": 0, "latency_ms": 0,
        },
        "metadata": {"category": "case-study", "difficulty": "medium"},
    },
    {
        "name": "q-004-education-and-health",
        "inputs": {
            "question": "Which SDGs are about education and health?",
            "paper_ids": ["paper-sdg-briefing-ch02-sdg-1-5-people"],
        },
        "expected_output": {
            "answer": "SDG 3 covers good health and well-being; SDG 4 covers quality education.",
            "cited_units": [],
            "tokens_in": 0, "tokens_out": 0, "latency_ms": 0,
        },
        "metadata": {"category": "fact-retrieval", "difficulty": "easy"},
    },
    {
        "name": "q-005-clean-water-energy",
        "inputs": {
            "question": "What does the briefing say about clean water (SDG 6) and clean energy (SDG 7)?",
            "paper_ids": ["paper-sdg-briefing-ch03-sdg-6-10"],
        },
        "expected_output": {
            "answer": (
                "SDG 6 calls for universal access to safe and affordable drinking water "
                "and sanitation. SDG 7 calls for affordable, reliable, sustainable, and "
                "modern energy for all. The briefing includes case studies on solutions in "
                "non-electrified communities and small-country policy approaches."
            ),
            "cited_units": [],
            "tokens_in": 0, "tokens_out": 0, "latency_ms": 0,
        },
        "metadata": {"category": "policy-summary", "difficulty": "medium"},
    },
]


SCORERS_BLOCK = [
    {"CitationPresent": {}},
    {"TokenCost": {}},
    {"LatencyMs": {}},
    {"CitationPrecision": {}},
    {"RubricAggregate": {"role": "answerer"}},
]


def main() -> None:
    payload = {
        "cases": SHARED_CASES,
        "evaluators": SCORERS_BLOCK,
    }
    for s in SCENARIOS:
        s.scoring_dir.mkdir(parents=True, exist_ok=True)
        target = s.scoring_dir / "dataset.yaml"
        target.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
        print(f"  wrote {target.relative_to(s.vault_dir.parent.parent)}")
    print("done.")


if __name__ == "__main__":
    main()
