"""The ``Vault`` class — single mutation point for the openacad atom graph.

A vault is a directory of ``.md`` files (atoms) plus a ``.openacad/``
sidecar holding indices, chunks, registry, and the activity log.

The Vault provides:

- **Read API** — ``atoms``, ``atom(id)``, ``search``, ``semantic``,
  ``incoming``, ``outgoing``, ``source_text``
- **Write API** — ``write``, ``delete``, ``split``, ``merge`` — every
  mutation funnels through these. They validate, reconcile wiki-links,
  update indices, and append an activity entry.
- **Ingestion** — ``ingest(pdf_path)`` copies a PDF into the sidecar,
  ``chunk(doc_id)`` extracts chunks into ``.openacad/chunks/``.
- **Reindex / verify** — ``reindex()`` rebuilds the FTS + embeddings
  caches from disk.

Single-process semantics: the Vault keeps an open SQLite connection
and the in-memory ChunkStore. Use ``with Vault(...) as v:`` or call
``close()`` to release the connection when done.
"""

from __future__ import annotations

import shutil
from collections.abc import Iterable, Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .atoms import AtomicNote, Source
from .chunks import Chunk, ChunkStore, chunk_pdf, read_chunks, write_chunks
from .indices import EmbeddingIndex, FTSIndex
from .markdown import (
    WikiLinkMismatch,
    check_wiki_link_invariant,
    extract_wiki_link_targets,
)
from .registry import Registry
from .store import Store

if TYPE_CHECKING:
    pass


SIDECAR_DIR = ".openacad"


def _utcnow_iso() -> str:
    return datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


class Vault:
    """Markdown-on-disk atomic-note vault with FTS + embeddings sidecar."""

    def __init__(
        self,
        path: str | Path,
        *,
        encoder=None,  # Optional[Encoder] — see indices.embeddings
        create: bool = True,
    ) -> None:
        self.path = Path(path).expanduser().resolve()
        if create:
            self._ensure_dirs()
        elif not self.path.exists():
            raise FileNotFoundError(f"vault directory does not exist: {self.path}")

        # Sidecar paths
        self._sidecar = self.path / SIDECAR_DIR
        self._index_dir = self._sidecar / "index"
        self._chunks_dir = self._sidecar / "chunks"
        self._docs_dir = self._sidecar / "documents"
        self._drafts_dir = self._sidecar / "drafts"
        self._agents_dir = self._sidecar / "agents"
        self._skills_dir = self._sidecar / "skills"
        self._activity_path = self._sidecar / "activity.jsonl"
        self._registry_path = self._index_dir / "registry.yaml"
        self._cache_db_path = self._index_dir / "cache.sqlite"
        self._embeddings_path = self._index_dir / "embeddings.npz"

        # Backends — lazy where helpful.
        self._store = Store(
            self._cache_db_path,
            activity_path=self._activity_path,
        )
        self._fts = FTSIndex(self._store)
        self._embeddings = EmbeddingIndex(self._embeddings_path, encoder=encoder)
        self._registry = Registry.load(self._registry_path)
        self._chunks = ChunkStore()
        self._chunks_loaded = False

        # Atom cache. The disk is the source of truth — this is a
        # lookup-by-id convenience populated on first access.
        self._atom_cache: dict[str, AtomicNote] = {}
        self._cache_loaded = False

    # ------------------------------------------------------------------
    # lifecycle
    # ------------------------------------------------------------------

    def _ensure_dirs(self) -> None:
        self.path.mkdir(parents=True, exist_ok=True)
        for sub in ("index", "chunks", "documents", "drafts", "agents", "skills"):
            (self.path / SIDECAR_DIR / sub).mkdir(parents=True, exist_ok=True)

    def close(self) -> None:
        try:
            self._embeddings.save()
        except Exception:  # noqa: BLE001 — best-effort close
            pass
        try:
            self._registry.save(self._registry_path)
        except Exception:
            pass
        self._store.close()

    def __enter__(self) -> Vault:
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    # ------------------------------------------------------------------
    # introspection / paths (used by M2)
    # ------------------------------------------------------------------

    @property
    def sidecar(self) -> Path:
        return self._sidecar

    @property
    def agents_dir(self) -> Path:
        return self._agents_dir

    @property
    def skills_dir(self) -> Path:
        return self._skills_dir

    @property
    def drafts_dir(self) -> Path:
        return self._drafts_dir

    @property
    def documents_dir(self) -> Path:
        return self._docs_dir

    @property
    def chunks_dir(self) -> Path:
        return self._chunks_dir

    @property
    def registry(self) -> Registry:
        return self._registry

    @property
    def store(self) -> Store:
        return self._store

    @property
    def embeddings(self) -> EmbeddingIndex:
        return self._embeddings

    # ------------------------------------------------------------------
    # atom read API
    # ------------------------------------------------------------------

    def _atom_path(self, atom_id: str) -> Path:
        return self.path / f"{atom_id}.md"

    def _iter_atom_files(self) -> Iterator[Path]:
        for p in sorted(self.path.glob("*.md")):
            # Skip hidden files; tutorial / readme files prefixed with
            # underscore are also excluded.
            if p.name.startswith((".", "_")):
                continue
            yield p

    def _load_atom_from_disk(self, atom_id: str) -> AtomicNote | None:
        p = self._atom_path(atom_id)
        if not p.exists():
            return None
        text = p.read_text(encoding="utf-8")
        return AtomicNote.from_markdown(text, id=atom_id)

    def _ensure_cache(self) -> None:
        if self._cache_loaded:
            return
        for p in self._iter_atom_files():
            atom_id = p.stem
            text = p.read_text(encoding="utf-8")
            self._atom_cache[atom_id] = AtomicNote.from_markdown(text, id=atom_id)
        self._cache_loaded = True

    @property
    def atoms(self) -> list[AtomicNote]:
        """All atoms in the vault, in atom-id order."""
        self._ensure_cache()
        return [self._atom_cache[k] for k in sorted(self._atom_cache.keys())]

    def atom(self, atom_id: str) -> AtomicNote | None:
        """Return atom by id (loads from disk on miss)."""
        if atom_id in self._atom_cache:
            return self._atom_cache[atom_id]
        atom = self._load_atom_from_disk(atom_id)
        if atom is not None:
            self._atom_cache[atom_id] = atom
        return atom

    # ------------------------------------------------------------------
    # search
    # ------------------------------------------------------------------

    def search(self, query: str, *, top_k: int = 10) -> list[AtomicNote]:
        """Full-text search via SQLite FTS5."""
        ids = self._fts.search(query, top_k=top_k)
        return [a for a in (self.atom(i) for i in ids) if a is not None]

    def semantic(self, query: str, *, top_k: int = 10) -> list[AtomicNote]:
        """Semantic search via MiniLM cosine similarity."""
        hits = self._embeddings.search(query, top_k=top_k)
        out: list[AtomicNote] = []
        for atom_id, _score in hits:
            atom = self.atom(atom_id)
            if atom is not None:
                out.append(atom)
        return out

    # ------------------------------------------------------------------
    # graph traversal
    # ------------------------------------------------------------------

    def incoming(self, atom_id: str) -> list[AtomicNote]:
        """Atoms whose body wiki-links (or relation targets) point at ``atom_id``."""
        self._ensure_cache()
        out: list[AtomicNote] = []
        for atom in self._atom_cache.values():
            if atom.id == atom_id:
                continue
            if any(r.target == atom_id for r in atom.relations):
                out.append(atom)
                continue
            if atom_id in extract_wiki_link_targets(atom.body):
                out.append(atom)
        return sorted(out, key=lambda a: a.id)

    def outgoing(
        self,
        atom_id: str,
        *,
        type: str | None = None,
    ) -> list[AtomicNote]:
        """Atoms targeted by ``atom_id``'s relations (optionally filtered by type)."""
        atom = self.atom(atom_id)
        if atom is None:
            return []
        out: list[AtomicNote] = []
        for rel in atom.relations:
            if type is not None and rel.type != type:
                continue
            target = self.atom(rel.target)
            if target is not None:
                out.append(target)
        return out

    # ------------------------------------------------------------------
    # source-text lookup (the "trust test")
    # ------------------------------------------------------------------

    def _ensure_chunks_loaded(self) -> None:
        if self._chunks_loaded:
            return
        if self._chunks_dir.exists():
            for jsonl in sorted(self._chunks_dir.glob("*.jsonl")):
                for chunk in read_chunks(jsonl):
                    self._chunks.add(chunk)
        self._chunks_loaded = True

    def chunk_by_id(self, chunk_id: str) -> Chunk | None:
        self._ensure_chunks_loaded()
        return self._chunks.get(chunk_id)

    def source_text(self, atom: AtomicNote) -> str:
        """Return the exact substring referenced by the atom's source.

        For single-sourced atoms: ``chunk.text[span.start:span.end]``.
        For multi-sourced atoms (post-merge): the substrings joined by
        ``"\\n\\n---\\n\\n"``. Raises if a referenced chunk is missing.
        """
        if not atom.sources:
            return ""
        parts: list[str] = []
        for src in atom.sources:
            chunk = self.chunk_by_id(src.chunk)
            if chunk is None:
                raise LookupError(
                    f"chunk {src.chunk!r} referenced by atom {atom.id!r} not found"
                )
            parts.append(chunk.text[src.span.start : src.span.end])
        return "\n\n---\n\n".join(parts)

    # ------------------------------------------------------------------
    # write — the single mutation point
    # ------------------------------------------------------------------

    def write(
        self,
        atom: AtomicNote,
        *,
        reconcile: bool = False,
        stamp_updated_at: bool = True,
        agent: str | None = None,
    ) -> AtomicNote:
        """Persist ``atom`` to disk, atomically refresh indices, log activity.

        Returns the written atom (with stamped ``updated_at``).

        Parameters
        ----------
        reconcile : bool
            If True and the wiki-link invariant fails, append a
            ``See also: [[...]]`` footer to the body so it matches the
            frontmatter relations. If False (default), raise
            :class:`openacad.vault.markdown.WikiLinkMismatch`.
        stamp_updated_at : bool
            If True (default), set ``updated_at`` to the current UTC
            time. Disable for migrations or replay scenarios.
        """
        if not atom.id:
            raise ValueError("atom.id is required for write")

        # 1) Reconcile / check the wiki-link invariant.
        if reconcile:
            atom = atom.with_reconciled_body()
        try:
            check_wiki_link_invariant(atom.body, atom.relation_targets())
        except WikiLinkMismatch as exc:
            raise WikiLinkMismatch(
                only_in_body=exc.only_in_body,
                only_in_relations=exc.only_in_relations,
            ) from None

        # 2) Stamp timestamps.
        if stamp_updated_at:
            atom = atom.model_copy(update={"updated_at": _utcnow_iso()})

        # 3) Was this atom previously on disk? Forget its old contribution
        #    to the registry so updates don't double-count.
        previous = self.atom(atom.id) if (self.path / f"{atom.id}.md").exists() else None
        if previous is not None:
            self._registry.forget(previous)

        # 4) Validate against the registry (warnings only, surfaced via
        #    activity log).
        validation_warnings = self._registry.validate(atom, known_atom_ids=self._atom_cache.keys())

        # 5) Observe usage in the registry.
        observe_warnings = self._registry.observe(atom)

        # 6) Persist markdown to disk. We write the file first because
        #    the file IS the source of truth; index rebuilds from disk.
        text = atom.to_markdown()
        target = self._atom_path(atom.id)
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_suffix(target.suffix + ".tmp")
        tmp.write_text(text, encoding="utf-8")
        tmp.replace(target)

        # 7) Update indices.
        self._store.upsert_atom(
            id=atom.id,
            type=atom.type,
            status=atom.status,
            body=atom.body,
            aliases=list(atom.aliases),
            tags=list(atom.tags),
            updated_at=atom.updated_at,
        )
        self._embeddings.add(atom.id, atom.body)
        self._embeddings.save()
        self._registry.save(self._registry_path)

        # 8) Refresh the in-memory atom cache.
        self._atom_cache[atom.id] = atom

        # 9) Activity log.
        self._store.append_activity(
            "atom.write",
            atom_id=atom.id,
            agent=agent,
            type=atom.type,
            status=atom.status,
            warnings=validation_warnings + observe_warnings,
            was_update=previous is not None,
        )
        return atom

    def delete(self, atom_id: str, *, agent: str | None = None) -> None:
        """Remove an atom from disk + indices."""
        atom = self.atom(atom_id)
        target = self._atom_path(atom_id)
        if target.exists():
            target.unlink()
        if atom is not None:
            self._registry.forget(atom)
            self._registry.save(self._registry_path)
        self._store.delete_atom(atom_id)
        self._embeddings.remove(atom_id)
        self._embeddings.save()
        self._atom_cache.pop(atom_id, None)
        self._store.append_activity("atom.delete", atom_id=atom_id, agent=agent)

    # ------------------------------------------------------------------
    # split / merge
    # ------------------------------------------------------------------

    def split(
        self,
        atom_id: str,
        parts: list[AtomicNote],
        *,
        agent: str | None = None,
    ) -> list[AtomicNote]:
        """Split ``atom_id`` into ``parts``.

        Invariants enforced:
          - The original atom is marked ``status=superseded`` (kept on
            disk for provenance).
          - Each new part inherits the parent's source(s) **unless** it
            specifies its own. Spans on inherited sources may be
            narrower than the parent's but must lie within the parent's
            span (we check that).
          - Activity log captures the parent → children mapping.
        """
        parent = self.atom(atom_id)
        if parent is None:
            raise LookupError(f"cannot split unknown atom {atom_id!r}")
        if not parts:
            raise ValueError("split requires at least one part")

        # Inherit + validate sources on each part.
        materialised: list[AtomicNote] = []
        for child in parts:
            if not child.sources and parent.sources:
                child = child.model_copy(update={"sources": list(parent.sources)})
            # Validate narrowed-span constraint (only when both parent
            # and child reference the same chunk).
            for csrc in child.sources:
                psrc = _find_matching_source(parent.sources, csrc.chunk)
                if psrc is None:
                    continue
                if csrc.span.start < psrc.span.start or csrc.span.end > psrc.span.end:
                    raise ValueError(
                        f"split part {child.id!r} source span "
                        f"[{csrc.span.start}, {csrc.span.end}) is outside parent "
                        f"[{psrc.span.start}, {psrc.span.end}) on chunk {csrc.chunk!r}"
                    )
            materialised.append(child)

        # Persist children.
        written: list[AtomicNote] = []
        for child in materialised:
            written.append(self.write(child, agent=agent))

        # Mark parent superseded.
        superseded = parent.model_copy(update={"status": "superseded"})
        self.write(superseded, agent=agent, stamp_updated_at=True)

        self._store.append_activity(
            "atom.split",
            parent_id=atom_id,
            child_ids=[c.id for c in written],
            agent=agent,
        )
        return written

    def merge(
        self,
        atom_ids: list[str],
        *,
        body: str,
        type: str = "claim",
        merged_id: str | None = None,
        attributes: dict[str, Any] | None = None,
        tags: list[str] | None = None,
        relations: list[Any] | None = None,
        agent: str | None = None,
    ) -> AtomicNote:
        """Merge ``atom_ids`` into a new atom; archive the originals."""
        if not atom_ids:
            raise ValueError("merge requires at least one atom id")
        if merged_id is None:
            merged_id = "merged-" + "-".join(atom_ids)[:60]

        parents: list[AtomicNote] = []
        for pid in atom_ids:
            parent = self.atom(pid)
            if parent is None:
                raise LookupError(f"cannot merge unknown atom {pid!r}")
            parents.append(parent)

        # Union of sources (preserve order, dedup by (chunk, span)).
        seen: set[tuple[str, int, int]] = set()
        merged_sources: list[Source] = []
        merged_tags: list[str] = []
        seen_tags: set[str] = set()
        for parent in parents:
            for src in parent.sources:
                key = (src.chunk, src.span.start, src.span.end)
                if key not in seen:
                    seen.add(key)
                    merged_sources.append(src)
            for t in parent.tags:
                if t not in seen_tags:
                    seen_tags.add(t)
                    merged_tags.append(t)

        if tags:
            for t in tags:
                if t not in seen_tags:
                    seen_tags.add(t)
                    merged_tags.append(t)

        merged = AtomicNote(
            id=merged_id,
            type=type,
            status="active",
            tags=merged_tags,
            attributes=attributes or {},
            sources=merged_sources,
            force_plural_sources=len(merged_sources) > 1,
            relations=list(relations or []),
            body=body,
        )
        written = self.write(merged, agent=agent)

        # Archive parents.
        for parent in parents:
            archived = parent.model_copy(update={"status": "archived"})
            self.write(archived, agent=agent)

        self._store.append_activity(
            "atom.merge",
            parent_ids=atom_ids,
            merged_id=merged.id,
            agent=agent,
        )
        return written

    # ------------------------------------------------------------------
    # ingestion
    # ------------------------------------------------------------------

    def ingest(self, pdf_path: str | Path, *, doc_id: str | None = None) -> str:
        """Copy a PDF into the sidecar and return its ``doc_id``."""
        src = Path(pdf_path)
        if not src.exists():
            raise FileNotFoundError(f"PDF not found: {src}")
        if doc_id is None:
            doc_id = src.stem
        dest = self._docs_dir / f"{doc_id}.pdf"
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        self._store.append_activity(
            "document.ingest",
            doc_id=doc_id,
            source_path=str(src),
        )
        return doc_id

    def chunk(self, doc_id: str, *, target_tokens: int = 400, overlap: int = 50) -> list[Chunk]:
        """Extract chunks from an ingested PDF and persist them."""
        pdf = self._docs_dir / f"{doc_id}.pdf"
        if not pdf.exists():
            raise FileNotFoundError(f"ingest the PDF first: {pdf}")
        chunks = chunk_pdf(
            pdf,
            doc_id=doc_id,
            target_tokens=target_tokens,
            overlap=overlap,
        )
        out_path = self._chunks_dir / f"{doc_id}.jsonl"
        write_chunks(out_path, chunks)
        # Refresh in-memory chunk store.
        for c in chunks:
            self._chunks.add(c)
        self._store.append_activity(
            "document.chunk",
            doc_id=doc_id,
            n_chunks=len(chunks),
        )
        return chunks

    def import_chunks(self, doc_id: str, chunks: Iterable[Chunk]) -> None:
        """Inject pre-computed chunks (used by the SQLite migration script)."""
        chunks = list(chunks)
        out_path = self._chunks_dir / f"{doc_id}.jsonl"
        write_chunks(out_path, chunks)
        for c in chunks:
            self._chunks.add(c)

    # ------------------------------------------------------------------
    # reindex
    # ------------------------------------------------------------------

    def reindex(self) -> None:
        """Rebuild FTS + embeddings + registry from atoms on disk."""
        self._atom_cache.clear()
        self._cache_loaded = False
        self._embeddings.clear()
        # Reset registry — observation rebuilds it.
        self._registry = Registry(path=self._registry_path)
        self._ensure_cache()
        self._store.rebuild_from(self._atom_cache.values())
        for atom in self._atom_cache.values():
            self._embeddings.add(atom.id, atom.body)
            self._registry.observe(atom)
        self._embeddings.save()
        self._registry.save(self._registry_path)


def _find_matching_source(sources: list[Source], chunk_id: str) -> Source | None:
    for s in sources:
        if s.chunk == chunk_id:
            return s
    return None


__all__ = ["Vault", "SIDECAR_DIR"]
