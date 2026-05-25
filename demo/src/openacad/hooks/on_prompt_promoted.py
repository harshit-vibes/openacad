"""Lifecycle hook fired after the scholar promotes a Meta-Evaluator proposal
to `state=active`.

Busts the agent_factory cache for that role so the next agent build in the
active scenario picks up the new prompt body. No service restart needed.
"""

from __future__ import annotations

from openacad.runtime.scenario import AgentRole


def fire(role: AgentRole) -> None:
    from openacad.runtime.agent_base import _bust_cache_for
    _bust_cache_for(role)
