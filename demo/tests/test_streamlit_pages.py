"""Smoke tests: every Streamlit page (overview + per-scenario + cross-cutting)
loads cleanly.

After the Ops Console restructure (2026-05-25):
  • 2 overview pages live under apps/streamlit/walkthrough/
    (welcome, conclusion — conclusion has Goodness as a tab)
  • 9 per-scenario pages live under apps/streamlit/scenarios/
    each delegates to apps.streamlit.scenario_view.render_scenario()
  • 3 workflows pages live under apps/streamlit/workflows/
    (ingest, compose, assess — all hard-pinned to evolving-notes)
  • 4 operations pages live under apps/streamlit/operations/
    (notes_registry, curate, evals_prompt_hardening, observability —
    all hard-pinned to evolving-notes)
"""

from __future__ import annotations

from pathlib import Path

import pytest

DEMO_ROOT = Path(__file__).resolve().parent.parent
GLOBAL_PAGES_DIR = DEMO_ROOT / "apps" / "streamlit" / "walkthrough"
SCENARIO_PAGES_DIR = DEMO_ROOT / "apps" / "streamlit" / "scenarios"
WORKFLOWS_PAGES_DIR = DEMO_ROOT / "apps" / "streamlit" / "workflows"
OPERATIONS_PAGES_DIR = DEMO_ROOT / "apps" / "streamlit" / "operations"


def _pages_in(dir_path: Path) -> list[Path]:
    return sorted(p for p in dir_path.glob("*.py") if p.name != "__init__.py")


def _all_pages() -> list[Path]:
    """Every Streamlit page in the demo across all sidebar sections."""
    return (
        _pages_in(GLOBAL_PAGES_DIR)
        + _pages_in(SCENARIO_PAGES_DIR)
        + _pages_in(WORKFLOWS_PAGES_DIR)
        + _pages_in(OPERATIONS_PAGES_DIR)
    )


def test_pages_exist():
    pages = _all_pages()
    # 2 overview (welcome, conclusion)
    # + 9 per-scenario
    # + 3 workflows (ingest, compose, assess)
    # + 4 operations (notes_registry, curate, evals_prompt_hardening, observability)
    # = 18
    assert len(pages) == 18, (
        f"expected 18 pages, found {len(pages)}: {[p.name for p in pages]}"
    )


@pytest.mark.parametrize("page_path", _all_pages(), ids=lambda p: p.name)
def test_page_loads(page_path):
    """Import + render each page; assert no uncaught exception."""
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(page_path), default_timeout=30)
    at.run()
    assert not at.exception, (
        f"Page {page_path.name} raised: "
        + " | ".join(str(e) for e in at.exception)
    )


def test_main_app_loads():
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(DEMO_ROOT / "apps" / "streamlit" / "streamlit_app.py"), default_timeout=30)
    at.run()
    assert not at.exception, "streamlit_app.py raised: " + " | ".join(str(e) for e in at.exception)
