"""Frontmatter + wiki-link parsing utilities for atom markdown files.

This module is intentionally low-level. The Vault uses these primitives
to enforce the **wiki-link reconciliation invariant**:

    frontmatter.relations[].target  ==  set of [[wiki-links]] in body

The canonical writer (``dump_frontmatter``) emits keys in a stable order
that matches the convention used in ``~/Documents/notes/`` and the
openacad atom spec.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

import yaml

# A [[wiki-link]] target. Supports the Obsidian ``[[target|display]]`` form,
# where only the ``target`` (left of the pipe) is meaningful for graph
# traversal. The capture group returns just the target part.
WIKI_LINK_RE = re.compile(r"\[\[([^\]|]+?)(?:\|[^\]]+)?\]\]")

# Canonical key order for atom frontmatter. Keys not listed here are
# treated as free-form attributes and emitted *after* the reserved
# preamble (in stable, sorted order).
RESERVED_PREAMBLE = (
    "type",
    "aliases",
    "created_at",
    "updated_at",
    "status",
    "tags",
)
RESERVED_TRAILER = (
    "source",
    "sources",
    "relations",
)
RESERVED_KEYS = frozenset(RESERVED_PREAMBLE + RESERVED_TRAILER)


# ---------------------------------------------------------------------------
# wiki-link helpers
# ---------------------------------------------------------------------------


def extract_wiki_link_targets(body: str) -> list[str]:
    """Return wiki-link targets in document order, with duplicates removed.

    >>> extract_wiki_link_targets("see [[a]] and [[b|alias]] and [[a]]")
    ['a', 'b']
    """
    seen: dict[str, None] = {}
    for match in WIKI_LINK_RE.finditer(body):
        target = match.group(1).strip()
        if target and target not in seen:
            seen[target] = None
    return list(seen.keys())


def normalize_relation_target(target: str) -> str:
    """Strip the ``[[...]]`` envelope (and optional ``|display``) from a target.

    >>> normalize_relation_target("[[atom-fa72]]")
    'atom-fa72'
    >>> normalize_relation_target("[[atom-fa72|display]]")
    'atom-fa72'
    >>> normalize_relation_target("atom-fa72")
    'atom-fa72'
    """
    t = target.strip()
    if t.startswith("[[") and t.endswith("]]"):
        t = t[2:-2]
    if "|" in t:
        t = t.split("|", 1)[0]
    return t.strip()


def wrap_relation_target(target: str) -> str:
    """Inverse of :func:`normalize_relation_target` — always emit ``[[target]]``."""
    t = normalize_relation_target(target)
    return f"[[{t}]]"


# ---------------------------------------------------------------------------
# frontmatter I/O
# ---------------------------------------------------------------------------


def parse_markdown(text: str) -> tuple[dict[str, Any], str]:
    """Split a markdown file into ``(frontmatter_dict, body_str)``.

    The frontmatter block is YAML between two ``---`` fences. If no
    frontmatter is found, returns ``({}, text)``.
    """
    if not text.startswith("---"):
        return {}, text
    # Find the closing fence. We require it to start at column 0.
    rest = text[3:]
    # consume a leading newline after the opening fence
    if rest.startswith("\n"):
        rest = rest[1:]
    end_match = re.search(r"^---[ \t]*\r?\n?", rest, re.MULTILINE)
    if end_match is None:
        return {}, text
    yaml_block = rest[: end_match.start()]
    body = rest[end_match.end() :]
    try:
        data = yaml.safe_load(yaml_block) or {}
    except yaml.YAMLError as exc:
        raise ValueError(f"Failed to parse frontmatter YAML: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(
            f"Frontmatter must be a YAML mapping, got {type(data).__name__}"
        )
    # Strip exactly one trailing newline that often separates frontmatter
    # fence from the body — the body itself is what users wrote.
    if body.startswith("\n"):
        body = body[1:]
    # Normalise trailing whitespace: a single trailing newline is the
    # canonical on-disk form (cf. ``assemble_markdown``), but in-memory
    # bodies are stored without it for round-trip purity.
    body = body.rstrip("\n")
    return data, body


class _OrderedDumper(yaml.SafeDumper):
    """SafeDumper that preserves insertion order of regular dicts."""


def _represent_dict_preserve_order(dumper: yaml.SafeDumper, data: Mapping[str, Any]):
    return dumper.represent_mapping("tag:yaml.org,2002:map", data.items())


_OrderedDumper.add_representer(dict, _represent_dict_preserve_order)


def _quote_string(dumper: yaml.SafeDumper, data: str):
    # Force double-quoted strings when they look ambiguous (lead with [, !, *, &, ?, |, >, ", etc.)
    if data.startswith(("[", "{", "!", "*", "&", "?", "|", ">", "%", "@", "`")):
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style='"')
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


_OrderedDumper.add_representer(str, _quote_string)


def dump_frontmatter(data: Mapping[str, Any]) -> str:
    """Serialize ``data`` to a YAML frontmatter block (no fences).

    Keys are emitted in canonical order:

        type, aliases, created_at, updated_at, status, tags,
        <attributes sorted alphabetically>,
        source/sources, relations

    String timestamps pass through unchanged; ``datetime`` instances are
    emitted as ISO 8601 strings via the standard YAML representer.
    """
    ordered: dict[str, Any] = {}
    for key in RESERVED_PREAMBLE:
        if key in data:
            ordered[key] = data[key]
    # attributes: everything outside RESERVED_KEYS, sorted alphabetically
    attrs = sorted(k for k in data.keys() if k not in RESERVED_KEYS)
    for key in attrs:
        ordered[key] = data[key]
    for key in RESERVED_TRAILER:
        if key in data:
            ordered[key] = data[key]
    return yaml.dump(
        ordered,
        Dumper=_OrderedDumper,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
        width=1_000_000,  # disable line wrapping; relevant for long quotes
    )


def assemble_markdown(frontmatter: Mapping[str, Any], body: str) -> str:
    """Inverse of :func:`parse_markdown`. Always emits a trailing newline."""
    fm = dump_frontmatter(frontmatter)
    body = body.rstrip("\n")
    return f"---\n{fm}---\n\n{body}\n"


# ---------------------------------------------------------------------------
# reconciliation
# ---------------------------------------------------------------------------


class WikiLinkMismatch(ValueError):
    """Raised by :func:`check_wiki_link_invariant` when body and relations diverge."""

    def __init__(
        self,
        *,
        only_in_body: list[str],
        only_in_relations: list[str],
    ) -> None:
        self.only_in_body = only_in_body
        self.only_in_relations = only_in_relations
        msg_parts = []
        if only_in_body:
            msg_parts.append(
                f"body has wiki-links not declared in frontmatter relations: {only_in_body}"
            )
        if only_in_relations:
            msg_parts.append(
                f"frontmatter relations target atoms not mentioned in body: {only_in_relations}"
            )
        super().__init__("; ".join(msg_parts) or "wiki-link mismatch")


def check_wiki_link_invariant(
    body: str,
    relation_targets: list[str],
) -> None:
    """Raise :class:`WikiLinkMismatch` if body wiki-links differ from relation targets.

    Both sides are normalised (``[[...]]`` stripped). Comparison is on the
    *set* of names — order does not matter, but presence does.
    """
    body_targets = set(extract_wiki_link_targets(body))
    relation_set = {normalize_relation_target(t) for t in relation_targets}
    only_in_body = sorted(body_targets - relation_set)
    only_in_relations = sorted(relation_set - body_targets)
    if only_in_body or only_in_relations:
        raise WikiLinkMismatch(
            only_in_body=only_in_body,
            only_in_relations=only_in_relations,
        )


def append_missing_wiki_links(body: str, relation_targets: list[str]) -> str:
    """Append a ``See also`` footer with any relation targets missing from body.

    This is the **reconcile-toward-frontmatter** primitive. Used by the
    migration script and by ``Vault.reconcile()`` when the caller asks
    for auto-repair. Leaves body unchanged if nothing is missing.
    """
    body_targets = set(extract_wiki_link_targets(body))
    missing: list[str] = []
    seen: set[str] = set()
    for raw in relation_targets:
        t = normalize_relation_target(raw)
        if t and t not in body_targets and t not in seen:
            missing.append(t)
            seen.add(t)
    if not missing:
        return body
    suffix = "\n\nSee also: " + " ".join(f"[[{t}]]" for t in missing)
    return body.rstrip("\n") + suffix
