"""Round-trip purity tests: ``from_markdown(to_markdown(a)) == a``.

The :class:`AtomicNote` model is the contract between the user (who
opens these files in Obsidian) and the agent runtime. Any silent
mutation on read or write is a bug — so we lock the behaviour with
table-driven tests across many shapes.
"""

from __future__ import annotations

from datetime import UTC

import pytest

from openacad.vault import AtomicNote, Relation, Source, Span
from openacad.vault.atoms import _coerce_timestamp


def _shapes() -> list[AtomicNote]:
    """A representative cross-section of real-world atom shapes."""
    return [
        # 1. Bare minimum
        AtomicNote(
            id="atom-bare",
            type="concept",
            body="Just a body, no attrs, no relations.",
        ),
        # 2. Full single-source claim
        AtomicNote(
            id="atom-claim",
            type="claim",
            aliases=["halving extreme poverty"],
            created_at="2026-05-27T10:00:00Z",
            updated_at="2026-05-27T10:00:00Z",
            status="active",
            tags=["poverty", "sdg-1", "2030-target"],
            attributes={
                "domain": "poverty",
                "era": "2015-present",
                "evidence": "strong",
            },
            sources=[
                Source(
                    document="doi-10-xxxx-abc",
                    chunk="chunk-fa72",
                    span=Span(start=1234, end=1456),
                    page=5,
                )
            ],
            relations=[
                Relation(type="supports", target="atom-fa72"),
                Relation(type="extends", target="atom-3c41"),
            ],
            body="A claim about [[atom-fa72]] and [[atom-3c41]].",
        ),
        # 3. Multi-source atom (after merge)
        AtomicNote(
            id="atom-merged",
            type="finding",
            sources=[
                Source(
                    document="doc1",
                    chunk="c1",
                    span=Span(start=0, end=10),
                ),
                Source(
                    document="doc2",
                    chunk="c2",
                    span=Span(start=5, end=20),
                    page=2,
                ),
            ],
            force_plural_sources=True,
            body="Merged from two sources.",
        ),
        # 4. Bag of attribute types (str, int, float, bool, list)
        AtomicNote(
            id="atom-typed-attrs",
            type="indicator",
            attributes={
                "name": "$2.15/day",
                "year_started": 2015,
                "share": 0.082,
                "is_global": True,
                "regions": ["sub-saharan-africa", "south-asia"],
            },
            body="An indicator with mixed-type attributes.",
        ),
        # 5. Aliases-only (no tags)
        AtomicNote(
            id="atom-aliases-only",
            type="definition",
            aliases=["Gita", "Bhagavad Gita"],
            body="Definition with aliases.",
        ),
        # 6. Tags-only (no aliases)
        AtomicNote(
            id="atom-tags-only",
            type="method",
            tags=["statistical", "household-survey"],
            body="Method tagged.",
        ),
        # 7. Body with wiki-link variants (pipe alias, dup)
        AtomicNote(
            id="atom-wiki-variants",
            type="concept",
            relations=[
                Relation(type="relates-to", target="atom-x"),
                Relation(type="relates-to", target="atom-y"),
            ],
            body="Refs [[atom-x|the X note]] and [[atom-y]] and [[atom-x]] again.",
        ),
        # 8. Body with no wiki-links and no relations
        AtomicNote(
            id="atom-no-graph",
            type="insight",
            body="Standalone insight, no graph edges.",
        ),
    ]


@pytest.mark.parametrize("atom", _shapes(), ids=lambda a: a.id)
def test_roundtrip_modulo_timestamps(atom: AtomicNote) -> None:
    md = atom.to_markdown()
    parsed = AtomicNote.from_markdown(md, id=atom.id)
    assert atom.equals_modulo_timestamps(parsed), parsed.model_dump()


def test_roundtrip_idempotent() -> None:
    """Serialising twice produces byte-identical output."""
    atom = AtomicNote(
        id="atom-stable",
        type="claim",
        attributes={"z": 1, "a": 2, "m": 3},
        relations=[Relation(type="r", target="t")],
        body="See [[t]]",
    )
    md1 = atom.to_markdown()
    parsed = AtomicNote.from_markdown(md1, id=atom.id)
    md2 = parsed.to_markdown()
    assert md1 == md2


def test_attributes_emitted_in_alphabetical_order() -> None:
    atom = AtomicNote(
        id="atom-x",
        type="claim",
        attributes={"zebra": 1, "alpha": 2, "mango": 3},
        body="text",
    )
    md = atom.to_markdown()
    # locate the three keys in the frontmatter
    idx_alpha = md.find("\nalpha:")
    idx_mango = md.find("\nmango:")
    idx_zebra = md.find("\nzebra:")
    assert 0 < idx_alpha < idx_mango < idx_zebra


def test_reserved_keys_appear_in_canonical_order() -> None:
    atom = AtomicNote(
        id="atom-x",
        type="claim",
        aliases=["x"],
        created_at="2026-05-27T10:00:00Z",
        updated_at="2026-05-27T10:00:00Z",
        status="active",
        tags=["t"],
        attributes={"k": "v"},
        sources=[Source(document="d", chunk="c", span=Span(start=0, end=1))],
        relations=[Relation(type="r", target="t")],
        body="See [[t]]",
    )
    md = atom.to_markdown()
    order = [
        md.index("type:"),
        md.index("aliases:"),
        md.index("created_at:"),
        md.index("updated_at:"),
        md.index("status:"),
        md.index("tags:"),
        md.index("k:"),  # attribute
        md.index("source:"),
        md.index("relations:"),
    ]
    assert order == sorted(order)


def test_singular_source_emitted_for_single_source_atom() -> None:
    atom = AtomicNote(
        id="atom-x",
        type="claim",
        sources=[Source(document="d", chunk="c", span=Span(start=0, end=1))],
        body="text",
    )
    md = atom.to_markdown()
    assert "\nsource:\n" in md
    assert "\nsources:" not in md


def test_plural_sources_emitted_when_forced() -> None:
    atom = AtomicNote(
        id="atom-x",
        type="claim",
        sources=[Source(document="d", chunk="c", span=Span(start=0, end=1))],
        force_plural_sources=True,
        body="text",
    )
    md = atom.to_markdown()
    assert "\nsources:" in md
    assert "\nsource:" not in md


def test_one_item_plural_sources_round_trips_as_plural() -> None:
    """If the file says ``sources: [one]``, we preserve that on round-trip."""
    md = """---
type: claim
created_at: 2026-05-27T10:00:00Z
updated_at: 2026-05-27T10:00:00Z
status: active
sources:
  - document: d
    chunk: c
    span:
      start: 0
      end: 5
---

body
"""
    atom = AtomicNote.from_markdown(md, id="atom-x")
    assert atom.force_plural_sources is True
    out = atom.to_markdown()
    assert "\nsources:" in out
    assert "\nsource:" not in out


def test_plural_sources_emitted_for_multi_source() -> None:
    atom = AtomicNote(
        id="atom-x",
        type="claim",
        sources=[
            Source(document="d1", chunk="c1", span=Span(start=0, end=1)),
            Source(document="d2", chunk="c2", span=Span(start=0, end=1)),
        ],
        body="text",
    )
    md = atom.to_markdown()
    assert "\nsources:" in md


def test_legacy_singular_source_kwarg_accepted() -> None:
    atom = AtomicNote(
        id="atom-x",
        type="claim",
        source=Source(document="d", chunk="c", span=Span(start=0, end=1)),
        body="text",
    )
    assert atom.sources[0].chunk == "c"


def test_reject_when_both_source_and_sources_supplied() -> None:
    with pytest.raises(ValueError):
        AtomicNote(
            id="atom-x",
            type="claim",
            source=Source(document="d", chunk="c", span=Span(start=0, end=1)),
            sources=[Source(document="d", chunk="c", span=Span(start=0, end=1))],
            body="text",
        )


def test_reserved_attribute_key_rejected_on_serialize() -> None:
    """Attributes cannot collide with reserved frontmatter keys."""
    # We can construct the model (no validator at construct time) but
    # serializing must surface the conflict.
    atom = AtomicNote(
        id="atom-x",
        type="claim",
        body="text",
    )
    atom.attributes["status"] = "duplicate"
    with pytest.raises(ValueError, match="reserved"):
        atom.to_markdown()


def test_iso_timestamp_with_datetime_coerced() -> None:
    """PyYAML may parse ISO strings as datetimes — we coerce back to ISO."""
    from datetime import datetime

    dt = datetime(2026, 5, 27, 10, 0, 0, tzinfo=UTC)
    atom = AtomicNote(id="atom-x", type="claim", created_at=dt, body="hi")
    assert atom.created_at == "2026-05-27T10:00:00Z"


def test_coerce_timestamp_naive_datetime_assumes_utc() -> None:
    from datetime import datetime

    s = _coerce_timestamp(datetime(2026, 1, 2, 3, 4, 5))
    assert s == "2026-01-02T03:04:05Z"


def test_relation_target_envelope_normalised() -> None:
    """Whether you pass ``"[[x]]"`` or ``"x"`` you get the bare id back."""
    r1 = Relation(type="t", target="[[atom-x]]")
    r2 = Relation(type="t", target="atom-x")
    r3 = Relation(type="t", target="[[atom-x|the X]]")
    assert r1.target == r2.target == r3.target == "atom-x"


def test_relation_yaml_dict_always_wraps_target() -> None:
    r = Relation(type="t", target="atom-x")
    assert r.to_yaml_dict() == {"type": "t", "target": "[[atom-x]]"}


def test_span_validation_rejects_negative_or_inverted() -> None:
    with pytest.raises(ValueError):
        Span(start=10, end=5)
    with pytest.raises(Exception):  # noqa: B017
        Span(start=-1, end=5)


def test_source_from_yaml_handles_list_span() -> None:
    """Some YAML writers emit ``span: [start, end]``; we accept both."""
    s = Source.from_yaml_dict({"document": "d", "chunk": "c", "span": [0, 5]})
    assert s.span.start == 0 and s.span.end == 5


def test_source_from_yaml_requires_span() -> None:
    with pytest.raises(ValueError):
        Source.from_yaml_dict({"document": "d", "chunk": "c"})


def test_unknown_fields_in_frontmatter_become_attributes() -> None:
    md = """---
type: claim
created_at: 2026-05-27T10:00:00Z
updated_at: 2026-05-27T10:00:00Z
status: active
unknown_attr: foo
nested_thing:
  k: v
---

Body content here.
"""
    atom = AtomicNote.from_markdown(md, id="atom-unk")
    assert atom.attributes == {"unknown_attr": "foo", "nested_thing": {"k": "v"}}


def test_from_markdown_with_no_frontmatter() -> None:
    atom = AtomicNote.from_markdown("just body text", id="atom-pure")
    assert atom.body == "just body text"
    assert atom.attributes == {}


def test_from_markdown_rejects_yaml_list_top_level() -> None:
    bad = "---\n- a\n- b\n---\n\nbody"
    with pytest.raises(ValueError, match="mapping"):
        AtomicNote.from_markdown(bad, id="atom-bad")


def test_relation_yaml_dict_roundtrip_preserves_bare_target() -> None:
    """Serialise then re-parse preserves the bare target form."""
    r = Relation(type="t", target="x")
    d = r.to_yaml_dict()
    r2 = Relation.from_yaml_dict(d)
    assert r2.target == "x"


def test_source_property_returns_lone_source() -> None:
    """``atom.source`` returns the single source when there's just one."""
    atom = AtomicNote(
        id="x",
        type="claim",
        sources=[Source(document="d", chunk="c", span=Span(start=0, end=1))],
        body="",
    )
    assert atom.source is not None and atom.source.chunk == "c"


def test_source_property_none_for_multi_or_plural_forced() -> None:
    atom = AtomicNote(
        id="x",
        type="claim",
        sources=[
            Source(document="d", chunk="c1", span=Span(start=0, end=1)),
            Source(document="d", chunk="c2", span=Span(start=0, end=1)),
        ],
        body="",
    )
    assert atom.source is None


def test_source_from_yaml_list_span_roundtrip() -> None:
    """Some pre-existing files use ``span: [start, end]`` form."""
    md = """---
type: claim
created_at: 2026-05-27T10:00:00Z
updated_at: 2026-05-27T10:00:00Z
status: active
source:
  document: d
  chunk: c
  span: [0, 5]
---

body
"""
    atom = AtomicNote.from_markdown(md, id="atom-x")
    assert atom.sources[0].span.start == 0
    assert atom.sources[0].span.end == 5


def test_source_yaml_dict_rejects_non_span() -> None:
    with pytest.raises(ValueError, match="mapping or 2-list"):
        Source.from_yaml_dict({"document": "d", "chunk": "c", "span": "garbage"})


def test_from_markdown_rejects_both_source_and_sources() -> None:
    md = """---
type: claim
created_at: 2026-05-27T10:00:00Z
updated_at: 2026-05-27T10:00:00Z
status: active
source:
  document: d
  chunk: c
  span: [0, 1]
sources:
  - document: d
    chunk: c
    span: [0, 1]
---

body
"""
    with pytest.raises(ValueError, match="both"):
        AtomicNote.from_markdown(md, id="atom-x")


def test_from_markdown_rejects_non_dict_relation_entry() -> None:
    md = """---
type: claim
created_at: 2026-05-27T10:00:00Z
updated_at: 2026-05-27T10:00:00Z
status: active
relations:
  - "stringy"
---

body
"""
    with pytest.raises(ValueError, match="mapping"):
        AtomicNote.from_markdown(md, id="atom-x")
