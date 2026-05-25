"""Hard-pin every Workflows / Operations page to the evolving-notes scenario.

These pages are intentionally NOT scenario-aware — they document the
production system, which is rung 9. The `pinned()` context manager wraps a
page body so all DB calls + projection calls see the pinned scenario.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from openacad.runtime.scenario import Scenario, use_scenario

PINNED_SCENARIO = "evolving-notes"


@contextmanager
def pinned() -> Iterator[Scenario]:
    """Activate the pinned scenario for the duration of a `with` block."""
    with use_scenario(PINNED_SCENARIO) as scenario:
        yield scenario
