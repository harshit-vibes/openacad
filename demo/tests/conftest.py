"""Shared fixtures for the e2e tests.

- Skips LLM-touching tests when no API key is set
- Ensures the scenario vaults are seeded
- Cleans up rubrics/comparisons inserted by the test session (best-effort)
"""

import os
import sys
from pathlib import Path

import pytest

# Make `api`, `app`, `scripts` importable.
DEMO_ROOT = Path(__file__).resolve().parent.parent
if str(DEMO_ROOT) not in sys.path:
    sys.path.insert(0, str(DEMO_ROOT))


def have_llm_key() -> bool:
    from openacad.runtime.llm import have_api_key
    return have_api_key()


@pytest.fixture(scope="session", autouse=True)
def seed_scenarios() -> None:
    """Ensure all 6 scenario vaults exist (idempotent)."""
    from openacad.runtime.scenario import SCENARIOS
    missing = [s for s in SCENARIOS if not s.prompts_dir.exists()]
    if missing:
        import scripts.seed_scenarios as seed
        seed.main()
        import scripts.seed_scoring_datasets as seed_ds
        seed_ds.main()


@pytest.fixture
def llm_required() -> None:
    """Skip a test if no LLM API key is configured."""
    if not have_llm_key():
        pytest.skip("LLM_PROVIDER has no API key — skipping LLM-touching test")


@pytest.fixture
def sample_question() -> str:
    return "What is the asymptotic complexity of standard attention?"


@pytest.fixture
def sample_paper_ids() -> list[str]:
    # Use the SDG paper that all atom-tier scenarios can answer about
    return []  # empty = no source filter
