"""Migrate the legacy ``state.sqlite`` atom store into the new markdown vault.

Source of truth: ``data/vaults/evolving-notes/state.sqlite`` (atoms +
relations) + ``data/shared.sqlite`` (chunks).

Output: ``data/vault/atom-<id>.md`` with reconstructed ``source:`` blocks,
plus ``data/vault/.openacad/chunks/<doc_id>.jsonl`` so ``vault.source_text``
can resolve spans.

Idempotent — running twice produces the same vault state. Prints a
summary at the end.

Strategy for source-span reconstruction
---------------------------------------

The legacy ``atoms_index`` row carries ``source_id`` + ``page_start`` +
``page_end`` + ``content`` (the atom's prose). The shared ``chunks``
table stores per-source chunks with character offsets *inside the
parent document text*.

For each migrated atom:

1. Filter chunks belonging to the source whose page range overlaps the
   atom's pages.
2. Search each chunk's text for the atom's ``content`` as a substring.
3. **Hit**: record an exact ``Source.span`` inside the chunk.
4. **Miss**: fall back to the first overlapping chunk and emit a
   ``span: [0, len(chunk.text))`` so ``source_text()`` returns the
   whole chunk. Log to the activity feed.

Multi-source atoms are not currently produced by the legacy store, so
we always emit singular ``source:``.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # ../app/
sys.path.insert(0, str(ROOT))

from openacad.vault import (  # noqa: E402
    AtomicNote,
    Chunk,
    Relation,
    Source,
    Span,
    Vault,
    WikiLinkMismatch,
)

DEFAULT_STATE_DB = ROOT / "data" / "vaults" / "evolving-notes" / "state.sqlite"
DEFAULT_SHARED_DB = ROOT / "data" / "shared.sqlite"
DEFAULT_VAULT_DIR = ROOT / "data" / "vault"


def _open_ro(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _load_chunks_for_source(shared: sqlite3.Connection, source_id: str) -> list[Chunk]:
    rows = shared.execute(
        "SELECT id, source_id, ordinal, text, page_start, page_end, char_start, char_end "
        "FROM chunks WHERE source_id = ? ORDER BY ordinal",
        (source_id,),
    ).fetchall()
    return [
        Chunk(
            id=r["id"],
            doc_id=r["source_id"],
            page=r["page_start"],
            page_end=r["page_end"] if r["page_end"] != r["page_start"] else None,
            char_start=r["char_start"],
            char_end=r["char_end"],
            text=r["text"],
        )
        for r in rows
    ]


def _pick_source_span(
    chunks: list[Chunk],
    *,
    content: str,
    page_start: int | None,
    page_end: int | None,
) -> tuple[Chunk, Span, bool]:
    """Return ``(chunk, span, exact_hit)`` for the migrated atom.

    Tries an exact substring match first; falls back to the first
    page-overlapping chunk with span ``[0, len(chunk.text))``.
    """
    # Filter by page overlap if information is available
    if page_start is not None and page_end is not None:
        overlapping = [
            c
            for c in chunks
            if c.page <= page_end and (c.page_end or c.page) >= page_start
        ]
        if not overlapping:
            overlapping = chunks
    else:
        overlapping = chunks

    # Exact substring search across overlapping chunks
    for chunk in overlapping:
        idx = chunk.text.find(content)
        if idx >= 0:
            return chunk, Span(start=idx, end=idx + len(content)), True

    # Fall back to the first overlapping chunk; span = whole chunk
    if not overlapping:
        raise RuntimeError("no chunks at all for source")
    fallback = overlapping[0]
    return fallback, Span(start=0, end=len(fallback.text)), False


def _build_atom(
    row: sqlite3.Row,
    *,
    source_doc_id: str | None,
    span_chunk: Chunk | None,
    span: Span | None,
    page: int | None,
    relations: list[Relation],
    relation_targets: list[str],
) -> AtomicNote:
    attrs_raw = json.loads(row["attributes_json"] or "{}")
    tags = json.loads(row["tags_json"] or "[]")
    content: str = row["content"]

    # Rename attribute keys that collide with reserved frontmatter names.
    # The legacy store carried "source" / "sources" / "tags" inside the
    # attributes JSON; the new schema reserves those at the top level.
    RESERVED_PREFIX = "legacy_"
    attrs: dict = {}
    for k, v in attrs_raw.items():
        if k in {"type", "aliases", "created_at", "updated_at", "status",
                  "tags", "source", "sources", "relations"}:
            attrs[f"{RESERVED_PREFIX}{k}"] = v
        else:
            attrs[k] = v

    body = content
    # Ensure body contains every relation target as a wiki-link.
    missing = [t for t in relation_targets if f"[[{t}]]" not in body]
    if missing:
        body = body.rstrip() + "\n\nSee also: " + " ".join(f"[[{t}]]" for t in missing)

    sources: list[Source] = []
    if source_doc_id is not None and span_chunk is not None and span is not None:
        sources.append(
            Source(
                document=source_doc_id,
                chunk=span_chunk.id,
                span=span,
                page=page,
            )
        )

    return AtomicNote(
        id=row["id"],
        type=row["type"],
        status=row["status"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        tags=tags,
        attributes=attrs,
        sources=sources,
        relations=relations,
        body=body,
    )


def _build_relation_targets(
    relation_types_json: str,
    relation_targets_json: str,
) -> tuple[list[Relation], list[str]]:
    """Return (relations, ordered_unique_targets).

    The target list preserves the source order and is deduplicated —
    used by the migration to produce a deterministic ``See also:``
    footer (and to guarantee idempotent re-runs).
    """
    types = json.loads(relation_types_json or "[]")
    targets = json.loads(relation_targets_json or "[]")
    if len(types) != len(targets):
        # Defensive: zip what we have.
        n = min(len(types), len(targets))
        types, targets = types[:n], targets[:n]
    rels: list[Relation] = []
    ordered: list[str] = []
    seen: set[str] = set()
    for t, tgt in zip(types, targets, strict=False):
        if not t or not tgt:
            continue
        rels.append(Relation(type=t, target=tgt))
        if tgt not in seen:
            seen.add(tgt)
            ordered.append(tgt)
    return rels, ordered


def migrate(
    *,
    state_db: Path,
    shared_db: Path,
    vault_dir: Path,
    verbose: bool = False,
) -> dict:
    state = _open_ro(state_db)
    shared = _open_ro(shared_db)

    vault_dir.mkdir(parents=True, exist_ok=True)
    vault = Vault(vault_dir)

    summary: dict[str, int | list[str]] = {
        "atoms_seen": 0,
        "atoms_written": 0,
        "exact_span_hits": 0,
        "fallback_span_used": 0,
        "atoms_without_source": 0,
        "skipped_errors": 0,
        "errors": [],
    }

    # Cache the per-source chunks we've already loaded into the vault
    loaded_source_chunks: dict[str, list[Chunk]] = {}

    try:
        for row in state.execute(
            "SELECT * FROM atoms_index ORDER BY id"
        ).fetchall():
            summary["atoms_seen"] += 1
            atom_id = row["id"]
            source_id = row["source_id"]

            try:
                relations, relation_targets = _build_relation_targets(
                    row["relation_types_json"],
                    row["relation_targets_json"],
                )

                if source_id:
                    if source_id not in loaded_source_chunks:
                        chunks = _load_chunks_for_source(shared, source_id)
                        loaded_source_chunks[source_id] = chunks
                        vault.import_chunks(source_id, chunks)
                    chunks = loaded_source_chunks[source_id]

                    if not chunks:
                        summary["atoms_without_source"] += 1
                        atom = _build_atom(
                            row,
                            source_doc_id=None,
                            span_chunk=None,
                            span=None,
                            page=None,
                            relations=relations,
                            relation_targets=relation_targets,
                        )
                    else:
                        chunk, span, exact = _pick_source_span(
                            chunks,
                            content=row["content"],
                            page_start=row["page_start"],
                            page_end=row["page_end"],
                        )
                        if exact:
                            summary["exact_span_hits"] += 1
                        else:
                            summary["fallback_span_used"] += 1
                            vault.store.append_activity(
                                "migration.fallback_span",
                                atom_id=atom_id,
                                source_id=source_id,
                                chunk_id=chunk.id,
                            )
                        atom = _build_atom(
                            row,
                            source_doc_id=source_id,
                            span_chunk=chunk,
                            span=span,
                            page=row["page_start"],
                            relations=relations,
                            relation_targets=relation_targets,
                        )
                else:
                    summary["atoms_without_source"] += 1
                    atom = _build_atom(
                        row,
                        source_doc_id=None,
                        span_chunk=None,
                        span=None,
                        page=None,
                        relations=relations,
                        relation_targets=relation_targets,
                    )

                # Write with stamp_updated_at=False so re-runs produce
                # byte-identical files (idempotent).
                vault.write(atom, stamp_updated_at=False, agent="migration")
                summary["atoms_written"] += 1
                if verbose:
                    print(f"  migrated {atom_id}")
            except WikiLinkMismatch as exc:
                summary["skipped_errors"] += 1
                summary["errors"].append(f"{atom_id}: wiki-link mismatch — {exc}")
            except Exception as exc:  # noqa: BLE001
                summary["skipped_errors"] += 1
                summary["errors"].append(f"{atom_id}: {type(exc).__name__}: {exc}")
    finally:
        vault.close()
        state.close()
        shared.close()

    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--state-db", type=Path, default=DEFAULT_STATE_DB)
    parser.add_argument("--shared-db", type=Path, default=DEFAULT_SHARED_DB)
    parser.add_argument("--vault", type=Path, default=DEFAULT_VAULT_DIR)
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    if not args.state_db.exists():
        print(f"state DB not found: {args.state_db}", file=sys.stderr)
        return 2
    if not args.shared_db.exists():
        print(f"shared DB not found: {args.shared_db}", file=sys.stderr)
        return 2

    started = datetime.now(tz=UTC).isoformat(timespec="seconds")
    print(f"[{started}] migrating {args.state_db} → {args.vault}")
    summary = migrate(
        state_db=args.state_db,
        shared_db=args.shared_db,
        vault_dir=args.vault,
        verbose=args.verbose,
    )

    print("=" * 60)
    print("Migration summary")
    print("=" * 60)
    print(f"  atoms seen          : {summary['atoms_seen']}")
    print(f"  atoms written       : {summary['atoms_written']}")
    print(f"  exact span hits     : {summary['exact_span_hits']}")
    print(f"  fallback spans used : {summary['fallback_span_used']}")
    print(f"  atoms w/o source    : {summary['atoms_without_source']}")
    print(f"  skipped (errors)    : {summary['skipped_errors']}")
    if summary["errors"]:
        print("\nFirst 5 errors:")
        for line in summary["errors"][:5]:
            print(f"  - {line}")
    return 0 if summary["skipped_errors"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
