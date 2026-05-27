"""The ``AtomicNote`` pydantic model and markdown serializer.

Atoms are the unit of scholar-blessed knowledge in openacad. Each atom
lives in one ``.md`` file on disk:

    ---
    type: claim
    aliases: ["halving extreme poverty"]
    created_at: 2026-05-27T10:00:00Z
    updated_at: 2026-05-27T10:00:00Z
    status: active
    tags: [poverty, sdg-1]
    domain: poverty                      # ← open-vocab attribute
    evidence: strong                     # ← open-vocab attribute
    source:
      document: doi-10-xxxx-abc
      chunk: chunk-fa72
      span: { start: 1234, end: 1456 }
      page: 5
    relations:
      - type: supports
        target: "[[atom-fa72]]"
    ---

    Body markdown with [[wiki-links]] that must match the frontmatter
    relations targets set.

The reserved keys are: ``type``, ``aliases``, ``created_at``,
``updated_at``, ``status``, ``tags``, ``source``, ``sources``,
``relations``. Everything else in the frontmatter is an open-vocab
attribute and lives in ``AtomicNote.attributes``.

Multi-source atoms (created by merge) use ``sources: list[...]`` instead
of singular ``source:``. On serialize, we pick which form to emit based
on cardinality and an explicit ``force_plural`` hint.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .markdown import (
    RESERVED_KEYS,
    WikiLinkMismatch,
    append_missing_wiki_links,
    assemble_markdown,
    check_wiki_link_invariant,
    normalize_relation_target,
    parse_markdown,
    wrap_relation_target,
)

# Atom type taxonomy. We keep it open (str) but recommend these values.
# The plan calls out: claim | concept | definition | finding | indicator |
# target | method | activity. We don't enforce — the registry can warn.

AtomStatus = str  # pending | active | archived | superseded


class Span(BaseModel):
    """Character span inside a chunk text. Half-open: ``[start, end)``."""

    model_config = ConfigDict(extra="forbid")

    start: int = Field(ge=0)
    end: int = Field(ge=0)

    def __init__(self, **data: Any) -> None:  # noqa: D401 — simple constructor validation
        super().__init__(**data)
        if self.end < self.start:
            raise ValueError(f"Span end ({self.end}) must be >= start ({self.start})")

    def length(self) -> int:
        return self.end - self.start


class Source(BaseModel):
    """Reference from an atom to an exact substring inside a chunk.

    ``span`` is character offsets inside ``chunk.text`` (not the
    original document). ``page`` is for human display; not authoritative.
    """

    model_config = ConfigDict(extra="forbid")

    document: str
    chunk: str
    span: Span
    page: int | None = None

    def to_yaml_dict(self) -> dict[str, Any]:
        """Render as the YAML-friendly mapping used in atom frontmatter."""
        d: dict[str, Any] = {
            "document": self.document,
            "chunk": self.chunk,
            "span": {"start": self.span.start, "end": self.span.end},
        }
        if self.page is not None:
            d["page"] = self.page
        return d

    @classmethod
    def from_yaml_dict(cls, data: dict[str, Any]) -> Source:
        span_data = data.get("span")
        if span_data is None:
            raise ValueError("source.span is required")
        if isinstance(span_data, list) and len(span_data) == 2:
            span = Span(start=int(span_data[0]), end=int(span_data[1]))
        elif isinstance(span_data, dict):
            span = Span(start=int(span_data["start"]), end=int(span_data["end"]))
        else:
            raise ValueError(f"source.span must be a mapping or 2-list, got {span_data!r}")
        return cls(
            document=str(data["document"]),
            chunk=str(data["chunk"]),
            span=span,
            page=data.get("page"),
        )


class Relation(BaseModel):
    """A typed edge to another atom (by atom id / filename stem).

    The ``target`` is always normalised to the bare id at construction
    time. ``Relation(target="[[atom-x]]")``, ``Relation(target="atom-x")``,
    and ``Relation(target="[[atom-x|display]]")`` are all equivalent.
    """

    model_config = ConfigDict(extra="forbid")

    type: str
    target: str  # always stored as a bare id (no [[...]] envelope)

    def __init__(self, **data: Any) -> None:
        if "target" in data and data["target"] is not None:
            data["target"] = normalize_relation_target(str(data["target"]))
        super().__init__(**data)

    def to_yaml_dict(self) -> dict[str, Any]:
        return {"type": self.type, "target": wrap_relation_target(self.target)}

    @classmethod
    def from_yaml_dict(cls, data: dict[str, Any]) -> Relation:
        return cls(
            type=str(data["type"]),
            target=normalize_relation_target(str(data["target"])),
        )


def _utcnow_iso() -> str:
    """ISO-8601 UTC timestamp with trailing ``Z`` (Obsidian-friendly)."""
    return datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _coerce_timestamp(value: Any) -> str:
    """Accept either a string or a ``datetime`` and return an ISO-8601 string."""
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    return str(value)


class AtomicNote(BaseModel):
    """A scholar-blessed atomic note.

    Round-trip invariant: ``from_markdown(to_markdown(a)) == a`` modulo
    ``updated_at`` (which the Vault stamps on write).
    """

    model_config = ConfigDict(extra="forbid")

    id: str
    type: str = "claim"
    status: AtomStatus = "active"
    created_at: str = Field(default_factory=_utcnow_iso)
    updated_at: str = Field(default_factory=_utcnow_iso)
    aliases: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    attributes: dict[str, Any] = Field(default_factory=dict)
    sources: list[Source] = Field(default_factory=list)
    relations: list[Relation] = Field(default_factory=list)
    body: str = ""

    # Persistence hint: when True, serialise as ``sources: [..]`` even if
    # only one source exists. Used by merge to make multi-source intent
    # explicit. Default: emit singular when len == 1, plural otherwise.
    force_plural_sources: bool = False

    def __init__(self, **data: Any) -> None:
        # Legacy convenience: accept a singular ``source`` keyword.
        if "source" in data:
            if "sources" in data:
                raise ValueError("provide either source= or sources=, not both")
            src = data.pop("source")
            if src is not None:
                data["sources"] = [src]
        # Normalise timestamps coming in as datetime objects (PyYAML does
        # this for unquoted ISO strings).
        for ts_field in ("created_at", "updated_at"):
            if ts_field in data and data[ts_field] is not None:
                data[ts_field] = _coerce_timestamp(data[ts_field])
        super().__init__(**data)

    # ------------------------------------------------------------------
    # convenience accessors
    # ------------------------------------------------------------------

    @property
    def source(self) -> Source | None:
        """The lone source for single-sourced atoms (or ``None``)."""
        if len(self.sources) == 1 and not self.force_plural_sources:
            return self.sources[0]
        return None

    def relation_targets(self) -> list[str]:
        """Return relation target ids (no ``[[...]]`` envelope)."""
        return [r.target for r in self.relations]

    # ------------------------------------------------------------------
    # markdown serialization
    # ------------------------------------------------------------------

    def to_markdown(self, *, check_invariant: bool = True) -> str:
        """Serialize the atom to its on-disk markdown form.

        If ``check_invariant`` is True (default), raises
        :class:`WikiLinkMismatch` when body wiki-links and frontmatter
        relations diverge. Pass ``False`` only when intentionally
        producing an intermediate form (e.g. inside :meth:`reconcile`).
        """
        fm: dict[str, Any] = {}

        # reserved preamble — only emit what's set
        fm["type"] = self.type
        if self.aliases:
            fm["aliases"] = list(self.aliases)
        fm["created_at"] = self.created_at
        fm["updated_at"] = self.updated_at
        fm["status"] = self.status
        if self.tags:
            fm["tags"] = list(self.tags)

        # attributes — splat at top level, after preamble (markdown.py
        # handles canonical alphabetical ordering on serialize).
        for k, v in self.attributes.items():
            if k in RESERVED_KEYS:
                raise ValueError(
                    f"attribute key {k!r} clashes with a reserved frontmatter key"
                )
            fm[k] = v

        # sources / source — pick singular vs plural deterministically
        if self.sources:
            if len(self.sources) == 1 and not self.force_plural_sources:
                fm["source"] = self.sources[0].to_yaml_dict()
            else:
                fm["sources"] = [s.to_yaml_dict() for s in self.sources]

        # relations last
        if self.relations:
            fm["relations"] = [r.to_yaml_dict() for r in self.relations]

        if check_invariant:
            check_wiki_link_invariant(self.body, self.relation_targets())

        return assemble_markdown(fm, self.body)

    # ------------------------------------------------------------------
    # markdown parsing
    # ------------------------------------------------------------------

    @classmethod
    def from_markdown(cls, text: str, *, id: str | None = None) -> AtomicNote:
        """Parse markdown text into an :class:`AtomicNote`.

        ``id`` is the atom id (typically the filename stem). It is not
        part of the on-disk frontmatter — filenames are the source of
        truth — so the caller must supply it. If absent, defaults to
        ``"atom"`` (round-trip tests should always pass the id).
        """
        fm, body = parse_markdown(text)
        return cls._from_parts(fm, body, id=id or "atom")

    @classmethod
    def _from_parts(
        cls,
        fm: dict[str, Any],
        body: str,
        *,
        id: str,
    ) -> AtomicNote:
        # extract reserved keys
        reserved: dict[str, Any] = {}
        for key in (
            "type",
            "status",
            "created_at",
            "updated_at",
            "aliases",
            "tags",
        ):
            if key in fm:
                reserved[key] = fm[key]

        # sources / source
        sources: list[Source] = []
        force_plural = False
        if "source" in fm and "sources" in fm:
            raise ValueError("atom frontmatter has both 'source' and 'sources'")
        if "source" in fm and fm["source"] is not None:
            sources = [Source.from_yaml_dict(dict(fm["source"]))]
        elif "sources" in fm and fm["sources"] is not None:
            sources = [Source.from_yaml_dict(dict(s)) for s in fm["sources"]]
            # If the file says ``sources:`` we honour that on round-trip
            # — preserves user intent so a future write doesn't silently
            # collapse a one-item list back to singular ``source:``.
            force_plural = True

        # relations
        relations: list[Relation] = []
        for r in fm.get("relations") or []:
            if not isinstance(r, dict):
                raise ValueError(f"relation entry must be a mapping, got {r!r}")
            relations.append(Relation.from_yaml_dict(r))

        # attributes — everything not in RESERVED_KEYS
        attributes: dict[str, Any] = {}
        for k, v in fm.items():
            if k in RESERVED_KEYS:
                continue
            attributes[k] = v

        return cls(
            id=id,
            type=reserved.get("type", "claim"),
            status=reserved.get("status", "active"),
            created_at=reserved.get("created_at", _utcnow_iso()),
            updated_at=reserved.get("updated_at", _utcnow_iso()),
            aliases=list(reserved.get("aliases") or []),
            tags=list(reserved.get("tags") or []),
            attributes=attributes,
            sources=sources,
            force_plural_sources=force_plural,
            relations=relations,
            body=body,
        )

    # ------------------------------------------------------------------
    # mutation helpers
    # ------------------------------------------------------------------

    def with_reconciled_body(self) -> AtomicNote:
        """Return a copy whose body has missing ``[[wiki-links]]`` appended."""
        new_body = append_missing_wiki_links(self.body, self.relation_targets())
        return self.model_copy(update={"body": new_body})

    def equals_modulo_timestamps(self, other: AtomicNote) -> bool:
        """Round-trip equality test — ignores ``updated_at`` drift."""
        a = self.model_dump()
        b = other.model_dump()
        for k in ("updated_at",):
            a.pop(k, None)
            b.pop(k, None)
        return a == b


__all__ = [
    "AtomicNote",
    "Source",
    "Span",
    "Relation",
    "WikiLinkMismatch",
]
