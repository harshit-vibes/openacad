"""Phase-2 sanity: assert the progressive-ladder capability shape per scenario.

Each rung must add EXACTLY one capability on top of the previous one. This test
locks the ladder so nobody accidentally re-bundles capabilities by editing
`scenarios/definitions.py` without thinking through the demo narrative.
"""

from __future__ import annotations

import pytest

from openacad.runtime.scenario import SCENARIOS, SCENARIOS_BY_KEY, Tier


EXPECTED_LADDER = [
    # (key, tier, has_extraction, has_curation, has_meta_eval,
    #  has_attributes, has_relations, has_atom_embeddings)
    # Cold and chunk tiers have NO atoms — atom-level capability flags
    # must be False for them (atoms attributes / relations / embeddings
    # are not applicable when there's no atom to attach them to).
    ("cold-read",         Tier.COLD,  False, False, False, False, False, False),
    ("keyword-snippets",  Tier.CHUNK, False, False, False, False, False, False),
    ("semantic-snippets", Tier.CHUNK, False, False, False, False, False, False),
    ("atoms-only",        Tier.ATOMS, True,  False, False, False, False, False),
    ("atoms-attrs",       Tier.ATOMS, True,  False, False, True,  False, False),
    ("atoms-attrs-rels",  Tier.ATOMS, True,  False, False, True,  True,  False),
    ("drafted-notes",     Tier.ATOMS, True,  False, False, True,  True,  True),
    ("curated-notes",     Tier.ATOMS, True,  True,  False, True,  True,  True),
    ("evolving-notes",    Tier.ATOMS, True,  True,  True,  True,  True,  True),
]


def test_scenario_count_matches_ladder():
    assert len(SCENARIOS) == len(EXPECTED_LADDER), (
        f"expected {len(EXPECTED_LADDER)} scenarios, got {len(SCENARIOS)}"
    )


def test_scenario_order_and_flags():
    """Scenarios must appear in ladder order with the expected flag combo each rung."""
    for i, (key, tier, has_ext, has_cur, has_meta, has_attrs, has_rels, has_emb) in enumerate(EXPECTED_LADDER):
        s = SCENARIOS[i]
        assert s.key == key, f"rung {i}: expected key={key}, got {s.key}"
        assert s.tier == tier, f"{key}: expected tier={tier}, got {s.tier}"
        assert s.has_extraction == has_ext, f"{key}: has_extraction"
        assert s.has_curation == has_cur, f"{key}: has_curation"
        assert s.has_meta_eval == has_meta, f"{key}: has_meta_eval"
        assert s.has_attributes == has_attrs, f"{key}: has_attributes"
        assert s.has_relations == has_rels, f"{key}: has_relations"
        assert s.has_atom_embeddings == has_emb, f"{key}: has_atom_embeddings"


def _delta_count(prev, curr) -> int:
    """How many capability flags differ between prev and curr."""
    flags = ("has_extraction", "has_curation", "has_meta_eval",
             "has_attributes", "has_relations", "has_atom_embeddings")
    return sum(1 for f in flags if getattr(prev, f) != getattr(curr, f))


@pytest.mark.parametrize("i", range(1, len(EXPECTED_LADDER)))
def test_each_rung_adds_at_most_one_capability_among_atom_tier(i):
    """Within the atom tier, each consecutive rung must add ≤ 1 capability flag."""
    prev = SCENARIOS[i - 1]
    curr = SCENARIOS[i]
    # Skip the first atom-tier rung — it crosses the chunk→atoms tier boundary
    # so multiple flags flip at once (extraction toggles, etc.).
    if prev.tier != Tier.ATOMS or curr.tier != Tier.ATOMS:
        return
    delta = _delta_count(prev, curr)
    assert delta <= 1, (
        f"rung {curr.key} flips {delta} capability flags vs {prev.key}; "
        f"the progressive ladder requires exactly 1"
    )


def test_steps_adapt_to_flags():
    """Cold/chunk tiers show 2 steps; atoms-only/no-curation skip 'Read & Take Notes';
    Self-Improving alone shows 'Refine Your Assistant'."""
    cold = SCENARIOS_BY_KEY["cold-read"]
    assert len(cold.steps) == 2
    assert all("Library" in st.title or "Ask" in st.title for st in cold.steps)

    atoms_only = SCENARIOS_BY_KEY["atoms-only"]
    assert not any("Read & Take Notes" in st.title for st in atoms_only.steps), (
        "atoms-only has no curation, so 'Read & Take Notes' should NOT be a step"
    )

    curated = SCENARIOS_BY_KEY["curated-notes"]
    assert any("Read & Take Notes" in st.title for st in curated.steps)
    assert not any("Refine" in st.title for st in curated.steps)

    evolving = SCENARIOS_BY_KEY["evolving-notes"]
    assert any("Refine" in st.title for st in evolving.steps), (
        "Self-Improving Assistant should show 'Refine Your Assistant' step"
    )


def test_vault_dirs_exist_for_all_scenarios():
    """After seeding, every scenario should have its vault dir created."""
    for s in SCENARIOS:
        assert s.vault_dir.exists(), f"{s.key} vault dir missing — run scripts/seed_scenarios.py"
        assert s.prompts_dir.exists(), f"{s.key} prompts dir missing"
