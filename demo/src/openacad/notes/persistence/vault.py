"""Read/write atoms and registry entries as Obsidian-compatible markdown.

Scenario-aware: every path resolves against `active_scenario().vault_dir`.
This is the *only* module that touches vault files. Atomic writes (tmp + rename).
"""

from datetime import datetime
from pathlib import Path

import frontmatter

from openacad.notes.schema import AtomicNote, Metas, Origin, Relation

from openacad.notes.registry.schema import AttributeDef, RelationDef, TypeDef
from openacad.runtime.scenario import active_scenario

# ── paths ───────────────────────────────────────────────────────────────


def notes_dir() -> Path:
    p = active_scenario().vault_dir / "notes"
    p.mkdir(parents=True, exist_ok=True)
    return p


def attributes_dir() -> Path:
    p = active_scenario().vault_dir / "registry" / "attributes"
    p.mkdir(parents=True, exist_ok=True)
    return p


def relations_dir() -> Path:
    p = active_scenario().vault_dir / "registry" / "relations"
    p.mkdir(parents=True, exist_ok=True)
    return p


def types_dir() -> Path:
    p = active_scenario().vault_dir / "registry" / "types"
    p.mkdir(parents=True, exist_ok=True)
    return p


def schema_evolution_path() -> Path:
    p = active_scenario().vault_dir / "registry" / "schema-evolution.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def atom_path(atom_id: str) -> Path:
    return notes_dir() / f"{atom_id}.md"


# ── atomic write helper ─────────────────────────────────────────────────


def _atomic_write(path: Path, text: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def _dump_post(metadata: dict, content: str) -> str:
    post = frontmatter.Post(content=content)
    post.metadata = metadata
    return frontmatter.dumps(post)


# ── atoms ───────────────────────────────────────────────────────────────


def read_atom(atom_id: str) -> AtomicNote:
    path = atom_path(atom_id)
    post = frontmatter.load(str(path))
    md = post.metadata
    return AtomicNote(
        metas=Metas(**md["metas"]),
        origin=Origin(**md["origin"]),
        attributes=md.get("attributes") or {},
        relations=[Relation(**r) for r in (md.get("relations") or [])],
        content=post.content,
    )


def write_atom(atom: AtomicNote) -> Path:
    path = atom_path(atom.metas.id)
    metadata = {
        "metas": atom.metas.model_dump(mode="json"),
        "origin": atom.origin.model_dump(mode="json"),
        "attributes": atom.attributes,
        "relations": [r.model_dump(mode="json") for r in atom.relations],
    }
    _atomic_write(path, _dump_post(metadata, atom.content))
    return path


def list_atoms() -> list[AtomicNote]:
    out: list[AtomicNote] = []
    for p in sorted(notes_dir().glob("*.md")):
        try:
            out.append(read_atom(p.stem))
        except Exception:
            # skip malformed files (caller can decide how to surface)
            continue
    return out


def atom_exists(atom_id: str) -> bool:
    return atom_path(atom_id).exists()


# ── registry: attributes ────────────────────────────────────────────────


def write_attribute_def(d: AttributeDef) -> Path:
    path = attributes_dir() / f"attr-{d.key}.md"
    metadata = d.model_dump(mode="json")
    _atomic_write(path, _dump_post(metadata, ""))
    return path


def read_attribute_def(key: str) -> AttributeDef:
    post = frontmatter.load(str(attributes_dir() / f"attr-{key}.md"))
    return AttributeDef(**post.metadata)


def list_attribute_defs() -> list[AttributeDef]:
    return [AttributeDef(**frontmatter.load(str(p)).metadata) for p in attributes_dir().glob("attr-*.md")]


# ── registry: relations ─────────────────────────────────────────────────


def write_relation_def(d: RelationDef) -> Path:
    path = relations_dir() / f"rel-{d.key}.md"
    _atomic_write(path, _dump_post(d.model_dump(mode="json"), ""))
    return path


def read_relation_def(key: str) -> RelationDef:
    post = frontmatter.load(str(relations_dir() / f"rel-{key}.md"))
    return RelationDef(**post.metadata)


def list_relation_defs() -> list[RelationDef]:
    return [RelationDef(**frontmatter.load(str(p)).metadata) for p in relations_dir().glob("rel-*.md")]


# ── registry: types ─────────────────────────────────────────────────────


def write_type_def(d: TypeDef) -> Path:
    path = types_dir() / f"type-{d.key}.md"
    _atomic_write(path, _dump_post(d.model_dump(mode="json"), ""))
    return path


def read_type_def(key: str) -> TypeDef:
    post = frontmatter.load(str(types_dir() / f"type-{key}.md"))
    return TypeDef(**post.metadata)


def list_type_defs() -> list[TypeDef]:
    return [TypeDef(**frontmatter.load(str(p)).metadata) for p in types_dir().glob("type-*.md")]


# ── schema evolution audit log (append-only) ────────────────────────────


def append_schema_evolution(entry: dict) -> None:
    """Append a markdown block to schema-evolution.md. Never edits prior entries."""
    path = schema_evolution_path()
    ts = entry.get("timestamp") or datetime.utcnow().isoformat() + "Z"
    lines = [f"\n## {ts} — {entry.get('action', 'change')}"]
    for k, v in entry.items():
        if k in {"action", "timestamp"}:
            continue
        lines.append(f"- {k}: {v}")
    block = "\n".join(lines) + "\n"
    with path.open("a", encoding="utf-8") as f:
        f.write(block)
