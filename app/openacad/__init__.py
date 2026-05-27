"""openacad — a scholarly research AI agent harness.

Public API surface. Downstream consumers (apps, scripts, tests, future packages)
should import from here rather than reaching into the internal layout.
"""

# Scenario context
from openacad.runtime.scenario import (
    AgentRole,
    Scenario,
    SCENARIOS,
    SCENARIOS_BY_KEY,
    Step,
    Tier,
    active_scenario,
    active_scenario_key,
    use_scenario,
)

# Top-level product surface (M1-M3).
from openacad.runtime import AgentRunner, RunResult
from openacad.vault import (
    AtomicNote,
    Chunk,
    Relation,
    Source,
    Span,
    Vault,
)

__all__ = [
    # scenarios
    "AgentRole", "Scenario", "SCENARIOS", "SCENARIOS_BY_KEY",
    "Step", "Tier",
    "active_scenario", "active_scenario_key", "use_scenario",
    # product
    "Vault", "AtomicNote", "Chunk", "Source", "Span", "Relation",
    "AgentRunner", "RunResult",
]
