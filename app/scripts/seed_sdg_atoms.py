"""Replace the legacy attention-mechanism seeded atoms with SDG-relevant atoms
that actually reference the ingested SDG briefing PDFs.

Run AFTER `scripts/seed_scenarios.py` and AFTER the SDG PDFs have been ingested.

Wipes existing atoms from curated-notes and evolving-notes vaults (notes/*.md +
atoms_index + atoms_fts + atoms.npz), then writes 12 hand-curated atoms with
proper `origin.source_id` references and a small graph of relations.
"""

from __future__ import annotations

import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from openacad.notes.schema import AtomicNote, Metas, Origin, Relation
from openacad.runtime.scenario import SCENARIOS_BY_KEY, use_scenario
from openacad.runtime import db
from openacad.notes.query import semantic as semantic_service
from openacad.notes.persistence import vault as vault_io
SEED_TARGETS = ["curated-notes", "evolving-notes"]


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


# ── SDG atoms, each grounded in a specific ingested chapter PDF ─────────


def build_atoms() -> list[AtomicNote]:
    n = _now()

    SDG_CH02 = "paper-sdg-briefing-ch02-sdg-1-5-people"
    SDG_CH03 = "paper-sdg-briefing-ch03-sdg-6-10"
    SDG_CH04 = "paper-sdg-briefing-ch04-sdg-11-15"
    SDG_CH05 = "paper-sdg-briefing-ch05-sdg-16-17-peace"

    def claim(id_, source_id, page_range, content, attrs=None, rels=None, tags=None):
        return AtomicNote(
            metas=Metas(id=id_, type="claim", created_at=n, updated_at=n,
                         tags=tags or ["claim"]),
            origin=Origin(source_id=source_id, chunk_ids=[],
                          page_range=page_range, scholar_action="seeded"),
            attributes=attrs or {},
            relations=rels or [],
            content=content,
        )

    def finding(id_, source_id, page_range, content, attrs=None, rels=None, tags=None):
        return AtomicNote(
            metas=Metas(id=id_, type="finding", created_at=n, updated_at=n,
                         tags=tags or ["finding"]),
            origin=Origin(source_id=source_id, chunk_ids=[],
                          page_range=page_range, scholar_action="seeded"),
            attributes=attrs or {},
            relations=rels or [],
            content=content,
        )

    def method(id_, source_id, page_range, content, attrs=None, rels=None, tags=None):
        return AtomicNote(
            metas=Metas(id=id_, type="method", created_at=n, updated_at=n,
                         tags=tags or ["method"]),
            origin=Origin(source_id=source_id, chunk_ids=[],
                          page_range=page_range, scholar_action="seeded"),
            attributes=attrs or {},
            relations=rels or [],
            content=content,
        )

    atoms: list[AtomicNote] = []

    # ── SDG 1 — Poverty (ch02) ───────────────────────────────────────────
    atoms.append(claim(
        id_="sdg-1-poverty-multidimensional",
        source_id=SDG_CH02, page_range=(3, 4),
        tags=["claim", "sdg-1", "poverty"],
        attrs={"domain.primary": "policy", "domain.sub": "poverty",
               "evidence.type": "theoretical", "evidence.confidence": "high",
               "temporal.year": 2023},
        content=(
            "To reduce poverty, governments and stakeholders must target underlying "
            "factors and develop strategies to alleviate deprivations across multiple "
            "dimensions — a multidimensional approach beyond income alone."
        ),
    ))
    atoms.append(claim(
        id_="sdg-1-poverty-three-components",
        source_id=SDG_CH02, page_range=(3, 4),
        tags=["claim", "sdg-1", "poverty", "strategy"],
        attrs={"domain.primary": "policy", "domain.sub": "poverty",
               "evidence.type": "theoretical", "evidence.confidence": "high"},
        rels=[Relation(type="extends", target="sdg-1-poverty-multidimensional")],
        content=(
            "Three crucial components for delivering on the poverty commitment: "
            "enhancing economic opportunities, improving education, and extending "
            "social protection systems."
        ),
    ))
    atoms.append(finding(
        id_="sdg-1-poverty-global-figure",
        source_id=SDG_CH02, page_range=(3, 3),
        tags=["finding", "sdg-1", "poverty"],
        attrs={"domain.primary": "policy", "domain.sub": "poverty",
               "evidence.type": "empirical", "evidence.confidence": "high",
               "evidence.sample-size": 575_000_000,
               "temporal.year": 2023},
        content=(
            "An estimated 7% of the global population — approximately 575 million people "
            "— still live in extreme poverty as of the most recent reporting period."
        ),
    ))

    # ── SDG 5 — Gender Equality (ch02) ───────────────────────────────────
    atoms.append(claim(
        id_="sdg-5-gender-end-discrimination",
        source_id=SDG_CH02, page_range=(7, 9),
        tags=["claim", "sdg-5", "gender"],
        attrs={"domain.primary": "policy", "domain.sub": "gender",
               "evidence.type": "theoretical", "evidence.confidence": "high"},
        content=(
            "SDG 5 targets ending all forms of discrimination against women and girls "
            "everywhere — covering legal frameworks, social norms, and economic access."
        ),
    ))
    atoms.append(claim(
        id_="sdg-5-gender-unpaid-care",
        source_id=SDG_CH02, page_range=(7, 9),
        tags=["claim", "sdg-5", "gender", "labour"],
        attrs={"domain.primary": "policy", "domain.sub": "gender",
               "evidence.type": "theoretical", "evidence.confidence": "high"},
        content=(
            "Recognising and valuing unpaid care and domestic work through public "
            "services, infrastructure, and social-protection policies is a named "
            "SDG 5 target."
        ),
    ))
    atoms.append(finding(
        id_="sdg-5-gender-parliament-share",
        source_id=SDG_CH02, page_range=(7, 9),
        tags=["finding", "sdg-5", "gender", "representation"],
        attrs={"domain.primary": "policy", "domain.sub": "gender",
               "evidence.type": "empirical", "evidence.confidence": "high",
               "temporal.year": 2023},
        content=(
            "Women's representation in national parliaments globally remains far below "
            "parity; the briefing cites this as one of the slowest-moving SDG 5 indicators."
        ),
    ))

    # ── SDG 6/7 — Clean Water + Energy (ch03) ────────────────────────────
    atoms.append(claim(
        id_="sdg-6-water-universal-access",
        source_id=SDG_CH03, page_range=(1, 3),
        tags=["claim", "sdg-6", "water"],
        attrs={"domain.primary": "policy", "domain.sub": "water-sanitation",
               "evidence.type": "theoretical", "evidence.confidence": "high"},
        content=(
            "SDG 6 calls for universal and equitable access to safe and affordable "
            "drinking water, sanitation, and hygiene for all by 2030."
        ),
    ))
    atoms.append(claim(
        id_="sdg-7-clean-energy-affordable",
        source_id=SDG_CH03, page_range=(3, 5),
        tags=["claim", "sdg-7", "energy"],
        attrs={"domain.primary": "policy", "domain.sub": "energy",
               "evidence.type": "theoretical", "evidence.confidence": "high"},
        content=(
            "SDG 7 calls for affordable, reliable, sustainable, and modern energy for "
            "all — including a substantial increase in the share of renewable energy "
            "in the global mix."
        ),
    ))
    atoms.append(method(
        id_="sdg-7-method-off-grid-solar",
        source_id=SDG_CH03, page_range=(6, 7),
        tags=["method", "sdg-7", "energy", "implementation"],
        attrs={"domain.primary": "implementation", "domain.sub": "energy",
               "method.class": "off-grid-electrification"},
        rels=[Relation(type="applied-to", target="sdg-7-clean-energy-affordable")],
        content=(
            "Off-grid solar lanterns and pico-grids deployed by NGOs in non-electrified "
            "rural communities are highlighted as a scalable implementation lever for "
            "SDG 7 in low-income regions."
        ),
    ))

    # ── SDG 13 — Climate (ch04) ──────────────────────────────────────────
    atoms.append(claim(
        id_="sdg-13-climate-urgent-action",
        source_id=SDG_CH04, page_range=(3, 5),
        tags=["claim", "sdg-13", "climate"],
        attrs={"domain.primary": "policy", "domain.sub": "climate",
               "evidence.type": "theoretical", "evidence.confidence": "high"},
        content=(
            "SDG 13 frames climate change as the defining issue of our time, calling for "
            "urgent action to combat impacts via mitigation, adaptation, and resilience-building."
        ),
    ))
    atoms.append(finding(
        id_="sdg-13-climate-horticulture-case",
        source_id=SDG_CH04, page_range=(6, 6),
        tags=["finding", "sdg-13", "climate", "implementation"],
        attrs={"domain.primary": "implementation", "domain.sub": "agriculture",
               "evidence.type": "anecdotal", "evidence.confidence": "medium"},
        rels=[Relation(type="supported-by",
                       target="sdg-13-climate-horticulture-case")] if False else [],
        content=(
            "Climate-friendly horticulture practices have produced measurable yield "
            "gains alongside lower emissions intensity in cited regional case studies — "
            "an SDG 13 implementation pattern."
        ),
    ))

    # ── SDG 16/17 — Peace + Partnerships (ch05) ──────────────────────────
    atoms.append(claim(
        id_="sdg-16-peace-strong-institutions",
        source_id=SDG_CH05, page_range=(1, 3),
        tags=["claim", "sdg-16", "peace", "justice"],
        attrs={"domain.primary": "policy", "domain.sub": "governance",
               "evidence.type": "theoretical", "evidence.confidence": "high"},
        content=(
            "SDG 16 promotes peaceful and inclusive societies for sustainable "
            "development, providing access to justice for all and building effective, "
            "accountable, and inclusive institutions at all levels."
        ),
    ))
    atoms.append(claim(
        id_="sdg-17-partnerships-mobilize-resources",
        source_id=SDG_CH05, page_range=(2, 5),
        tags=["claim", "sdg-17", "partnerships"],
        attrs={"domain.primary": "policy", "domain.sub": "partnerships",
               "evidence.type": "theoretical", "evidence.confidence": "high"},
        rels=[Relation(type="supported-by", target="sdg-1-poverty-global-figure")],
        content=(
            "SDG 17 calls for strengthening the means of implementation and revitalising "
            "the Global Partnership for Sustainable Development — mobilising additional "
            "financial resources for developing countries from multiple sources."
        ),
    ))
    atoms.append(finding(
        id_="sdg-16-method-anti-trafficking-truckers",
        source_id=SDG_CH05, page_range=(4, 5),
        tags=["finding", "sdg-16", "anti-trafficking", "implementation"],
        attrs={"domain.primary": "implementation", "domain.sub": "anti-trafficking",
               "evidence.type": "anecdotal", "evidence.confidence": "medium"},
        content=(
            "An initiative training long-haul truck drivers as anti-trafficking allies "
            "is cited as a creative SDG 16 implementation: the workforce most exposed "
            "to trafficking routes becomes the early-warning network."
        ),
    ))

    return atoms


# ── wipe + write ────────────────────────────────────────────────────────


def _wipe_existing(scenario_key: str) -> int:
    """Delete all existing notes + projections + embeddings for the scenario."""
    s = SCENARIOS_BY_KEY[scenario_key]
    n_deleted = 0
    with use_scenario(scenario_key):
        atoms = vault_io.list_atoms()
        for a in atoms:
            try:
                vault_io.atom_path(a.metas.id).unlink()
                db.remove_atom_projection(a.metas.id)
                semantic_service.atoms_store().remove(a.metas.id)
                n_deleted += 1
            except Exception as e:
                print(f"  ! couldn't remove {a.metas.id}: {e}")
    return n_deleted


def _write_atoms(scenario_key: str, atoms: list[AtomicNote]) -> None:
    with use_scenario(scenario_key):
        embeds = []
        for a in atoms:
            vault_io.write_atom(a)
            db.upsert_atom_projection(a)
            embeds.append((a.metas.id, a.content))
        semantic_service.atoms_store().upsert_many(embeds)


def main() -> None:
    print("== seed SDG-relevant atoms ==")

    # Sanity: do the SDG PDFs exist?
    sources = db.list_sources()
    sdg_sources = {s.id for s in sources if "sdg-briefing" in s.id}
    if not sdg_sources:
        print("ERROR: no SDG briefing PDFs ingested. Run scripts/seed_scenarios.py and "
              "ingest the bundled PDFs first.", file=sys.stderr)
        sys.exit(1)
    print(f"  found {len(sdg_sources)} SDG PDF sources")

    atoms = build_atoms()
    print(f"  prepared {len(atoms)} SDG atoms")

    for key in SEED_TARGETS:
        print(f"\n— {key} —")
        n_del = _wipe_existing(key)
        print(f"  wiped {n_del} legacy atoms")
        _write_atoms(key, atoms)
        print(f"  wrote {len(atoms)} new SDG atoms + projections + embeddings")

    print("\ndone.")


if __name__ == "__main__":
    main()
