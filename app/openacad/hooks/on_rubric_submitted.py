"""Lifecycle hook fired after the scholar submits a rubric rating.

Today it's a no-op placeholder — `openacad.feedback.rubric.record()` already writes the
rubric row to the per-scenario eval log directly. Phase 2+ can wire this hook
to trigger automatic prompt-regen proposals once the rubric-count threshold
is reached, push aggregates into PostHog/Langfuse, etc.
"""

from __future__ import annotations

from openacad.runtime.scenario import AgentRole


def fire(role: AgentRole, target_id: str, overall: int) -> None:
    """Currently a no-op. Reserved for future cadence-based meta-eval triggers."""
    return None
