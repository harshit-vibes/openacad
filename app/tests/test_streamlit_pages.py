"""Smoke tests for the frozen museum Streamlit tour.

The museum preserves the 9-rung capability ladder demo at git tag `thesis-v1`.
It's installed via the optional `[museum]` extra (`pip install -e '.[museum]'`).
When streamlit isn't installed, these tests skip cleanly.

After M5 trim (2026-05-27):
  • 2 overview pages: walkthrough/00_welcome.py, walkthrough/90_conclusion.py
  • 9 per-scenario pages: scenarios/*.py (each delegates to scenario_view.py)
"""

from __future__ import annotations

from pathlib import Path

import pytest

streamlit = pytest.importorskip("streamlit", reason="museum extra not installed")

DEMO_ROOT = Path(__file__).resolve().parent.parent
GLOBAL_PAGES_DIR = DEMO_ROOT / "museum" / "streamlit" / "walkthrough"
SCENARIO_PAGES_DIR = DEMO_ROOT / "museum" / "streamlit" / "scenarios"


def _pages_in(dir_path: Path) -> list[Path]:
    return sorted(p for p in dir_path.glob("*.py") if p.name != "__init__.py")


def _all_pages() -> list[Path]:
    """Every Streamlit page in the museum tour."""
    return _pages_in(GLOBAL_PAGES_DIR) + _pages_in(SCENARIO_PAGES_DIR)


def test_pages_exist():
    pages = _all_pages()
    # 2 overview (welcome, conclusion) + 9 per-scenario = 11
    assert len(pages) == 11, (
        f"expected 11 pages, found {len(pages)}: {[p.name for p in pages]}"
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

    at = AppTest.from_file(str(DEMO_ROOT / "museum" / "streamlit" / "streamlit_app.py"), default_timeout=30)
    at.run()
    assert not at.exception, "streamlit_app.py raised: " + " | ".join(str(e) for e in at.exception)
