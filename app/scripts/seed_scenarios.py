"""Create the 6 per-scenario vault directories and seed each with its starter state.

After this runs:
    data/
    ├── shared.sqlite               sources + chunks migrated here from legacy state.sqlite
    ├── embeddings/chunks.npz       (existing; unchanged)
    └── vaults/
        ├── cold-read/              prompts/answerer.v1.md + empty state.sqlite
        ├── semantic-snippets/      same shape as cold-read
        ├── keyword-snippets/       same shape
        ├── drafted-notes/          + notes/ + registry/ + atoms.npz copied from legacy
        ├── curated-notes/          same as drafted-notes
        └── evolving-notes/         same + meta_evaluator.v1.md

Idempotent. Safe to re-run. Existing data is migrated, not duplicated.
"""

import shutil
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

# Make api importable when run as a script.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from openacad.runtime.settings import settings
from openacad.runtime.scenario import SCENARIOS, AgentRole, Tier, use_scenario

DEMO_ROOT = Path(__file__).resolve().parent.parent
LEGACY_DB = settings.data_dir / "state.sqlite"
LEGACY_VAULT = DEMO_ROOT / "vault"
LEGACY_ATOMS_NPZ = settings.embeddings_dir / "atoms.npz"


# ── prompt templates copied into each scenario ──────────────────────────
#
# Starter prompts live as markdown files under `scenarios/prompts/`:
#   - scenarios/prompts/<key>/<role>.md   (per-scenario override, if present)
#   - scenarios/prompts/<role>.md         (default; for answerer also -<tier>)
#
# Lookup order: per-scenario override → role-default. This lets P2 scenarios
# (atoms-only, atoms-attrs, atoms-attrs-rels) ship their own extractor prompt
# without forking the base.


PROMPTS_DIR = DEMO_ROOT / "scenarios" / "prompts"


def _prompt_body_for(scenario_key: str, role: AgentRole) -> str:
    """Pick the right starter prompt for (scenario, role).

    Resolution:
      1. scenarios/prompts/<key>/<role>.md   (per-scenario override)
      2. For ANSWERER: scenarios/prompts/answerer-<tier>.md  (cold | chunks | atoms)
         For others:   scenarios/prompts/<role>.md           (default)
    """
    from openacad.runtime.scenario import SCENARIOS_BY_KEY
    s = SCENARIOS_BY_KEY[scenario_key]

    override = PROMPTS_DIR / scenario_key / f"{role.value}.md"
    if override.exists():
        return override.read_text(encoding="utf-8")

    if role == AgentRole.ANSWERER:
        tier_suffix = {Tier.COLD: "cold", Tier.CHUNK: "chunks", Tier.ATOMS: "atoms"}[s.tier]
        return (PROMPTS_DIR / f"answerer-{tier_suffix}.md").read_text(encoding="utf-8")

    return (PROMPTS_DIR / f"{role.value}.md").read_text(encoding="utf-8")


# ── migration helpers ───────────────────────────────────────────────────


def migrate_sources_chunks_to_shared() -> None:
    """Copy sources + chunks from legacy data/state.sqlite into the new
    data/shared.sqlite. Idempotent."""
    if not LEGACY_DB.exists():
        print("  (no legacy state.sqlite to migrate)")
        return

    from openacad.runtime import db as new_db
    shared = new_db._shared()  # initializes schema

    legacy = sqlite3.connect(LEGACY_DB)
    legacy.row_factory = sqlite3.Row
    try:
        # sources
        try:
            srcs = legacy.execute("SELECT * FROM sources").fetchall()
        except sqlite3.OperationalError:
            srcs = []
        for r in srcs:
            shared.execute(
                """INSERT INTO sources (id, filename, title, uploaded_at, n_pages, n_chunks)
                   VALUES (?,?,?,?,?,?)
                   ON CONFLICT(id) DO UPDATE SET
                     filename=excluded.filename, title=excluded.title,
                     uploaded_at=excluded.uploaded_at, n_pages=excluded.n_pages,
                     n_chunks=excluded.n_chunks""",
                (r["id"], r["filename"], r["title"], r["uploaded_at"],
                 r["n_pages"], r["n_chunks"]),
            )
        # chunks
        try:
            chs = legacy.execute("SELECT * FROM chunks").fetchall()
        except sqlite3.OperationalError:
            chs = []
        for r in chs:
            shared.execute(
                """INSERT INTO chunks (id, source_id, ordinal, text, page_start, page_end,
                                       char_start, char_end, metadata_json)
                   VALUES (?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(id) DO UPDATE SET
                     source_id=excluded.source_id, ordinal=excluded.ordinal, text=excluded.text,
                     page_start=excluded.page_start, page_end=excluded.page_end,
                     char_start=excluded.char_start, char_end=excluded.char_end,
                     metadata_json=excluded.metadata_json""",
                (r["id"], r["source_id"], r["ordinal"], r["text"],
                 r["page_start"], r["page_end"], r["char_start"], r["char_end"],
                 r["metadata_json"]),
            )
            # mirror to chunks_fts
            shared.execute("DELETE FROM chunks_fts WHERE chunk_id=?", (r["id"],))
            shared.execute(
                "INSERT INTO chunks_fts (chunk_id, source_id, text) VALUES (?,?,?)",
                (r["id"], r["source_id"], r["text"]),
            )
        print(f"  migrated {len(srcs)} sources, {len(chs)} chunks → data/shared.sqlite")
    finally:
        legacy.close()


def copy_legacy_atoms_to_scenarios() -> None:
    """Copy the existing vault/notes + vault/registry into the seeded atom-tier
    scenarios (curated-notes, evolving-notes). Drafted-notes starts empty (it
    will be populated by re-running extraction with auto-accept)."""
    legacy_vault = Path(__file__).resolve().parent.parent / "vault"
    if not legacy_vault.exists():
        print("  (no legacy vault/ to copy)")
        return

    seed_targets = ["curated-notes", "evolving-notes"]
    legacy_notes = legacy_vault / "notes"
    legacy_registry = legacy_vault / "registry"

    for key in seed_targets:
        from openacad.runtime.scenario import SCENARIOS_BY_KEY
        s = SCENARIOS_BY_KEY[key]
        if legacy_notes.exists():
            tgt = s.vault_dir / "notes"
            tgt.mkdir(parents=True, exist_ok=True)
            for md in legacy_notes.glob("*.md"):
                shutil.copy2(md, tgt / md.name)
        if legacy_registry.exists():
            tgt = s.vault_dir / "registry"
            if tgt.exists():
                # don't blow away prior; merge file-by-file
                for src in legacy_registry.rglob("*"):
                    if src.is_file():
                        rel = src.relative_to(legacy_registry)
                        dst = tgt / rel
                        dst.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(src, dst)
            else:
                shutil.copytree(legacy_registry, tgt)
        # Also copy atom embeddings if they exist
        if LEGACY_ATOMS_NPZ.exists():
            tgt = s.atoms_npz_path
            tgt.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(LEGACY_ATOMS_NPZ, tgt)
        print(f"  seeded {key}: notes + registry + atoms.npz from legacy vault")


def reproject_atoms_per_scenario() -> None:
    """For each scenario that received seeded atoms, rebuild atoms_index + atoms_fts
    in its state.sqlite by re-reading the markdown files."""
    from openacad.runtime import db
    from openacad.notes.persistence import vault as vault_io
    for key in ("curated-notes", "evolving-notes"):
        with use_scenario(key):
            atoms = vault_io.list_atoms()
            for a in atoms:
                db.upsert_atom_projection(a)
            print(f"  reprojected {len(atoms)} atoms into {key}/state.sqlite")


def write_starter_prompts() -> None:
    """Write the v1 system prompt for each agent role into each scenario's prompts/."""
    from openacad.runtime import db
    from openacad.feedback.schema import PromptVersion

    now = datetime.now(timezone.utc)
    for scenario in SCENARIOS:
        scenario.prompts_dir.mkdir(parents=True, exist_ok=True)
        with use_scenario(scenario.key):
            for role in scenario.agents:
                body = _prompt_body_for(scenario.key, role)
                version = f"{role.value}.v1"
                # On disk
                fn = scenario.prompts_dir / f"{role.value}.v1.md"
                fn.write_text(body, encoding="utf-8")
                # In state.sqlite (active by default for v1)
                existing = [p for p in db.list_prompts(name=role.value) if p.version == version]
                if not existing:
                    db.upsert_prompt(PromptVersion(
                        name=role.value, version=version, created_at=now, body=body,
                        parent_version=None, state="active",
                    ))
        print(f"  wrote starter prompts for {scenario.key} ({len(scenario.agents)} agents)")


# ── runner ──────────────────────────────────────────────────────────────


def main() -> None:
    print("== seed scenarios ==")
    print("step 1: create vault directories")
    for s in SCENARIOS:
        s.vault_dir.mkdir(parents=True, exist_ok=True)
        s.prompts_dir.mkdir(parents=True, exist_ok=True)
        s.scoring_dir.mkdir(parents=True, exist_ok=True)
        if s.tier == Tier.ATOMS:
            s.notes_dir.mkdir(parents=True, exist_ok=True)
            s.registry_dir.mkdir(parents=True, exist_ok=True)
            (s.vault_dir / "embeddings").mkdir(parents=True, exist_ok=True)
        print(f"  ✓ data/vaults/{s.key}/")

    print("step 2: migrate sources + chunks → data/shared.sqlite")
    migrate_sources_chunks_to_shared()

    print("step 3: copy legacy seeded atoms into curated-notes + evolving-notes")
    copy_legacy_atoms_to_scenarios()

    print("step 4: reproject atoms into per-scenario state.sqlite")
    reproject_atoms_per_scenario()

    print("step 5: write starter prompts for every agent in every scenario")
    write_starter_prompts()

    print("done.")


if __name__ == "__main__":
    main()
