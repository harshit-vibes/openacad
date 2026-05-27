"""Seed the vault with the initial registry + 6-8 example atoms.

Run: python scripts/seed_vault.py

What this writes:
- vault/registry/types/type-{claim,method,finding}.md         (3 type defs)
- vault/registry/attributes/attr-*.md                          (8 attribute defs)
- vault/registry/relations/rel-*.md                            (6 relation defs)
- vault/registry/schema-evolution.md                           (audit log seeded)
- vault/notes/*.md                                             (7 example atoms)

The atoms are deliberately interlinked so a fresh checkout has a non-trivial
graph to demo against — contradictions, supported-by chains, part-of nests.
Embeddings for the seed atoms are also written so /query works immediately.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

# Make api importable when running as a script.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from openacad.notes.schema import AtomicNote, Metas, Origin, Relation

from openacad.notes.registry.schema import AttributeDef, RelationDef, TypeDef
from openacad.notes.query import semantic as semantic_service
from openacad.runtime import db
from openacad.notes.persistence import vault as vault_io
def now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


# ── seed type registry ──────────────────────────────────────────────────


TYPES = [
    TypeDef(
        key="claim",
        description="An assertion the source paper argues to be true.",
        suggested_attributes=["domain.primary", "domain.sub", "evidence.type", "evidence.confidence"],
        suggested_relations=["extends", "contradicts", "supported-by", "part-of"],
        example_atom="2026-05-24-claim-attention-quadratic",
        first_seen=now(),
        auto_registered=False,
    ),
    TypeDef(
        key="method",
        description="A technique, algorithm, or procedure described by the paper.",
        suggested_attributes=["domain.primary", "domain.sub", "method.class"],
        suggested_relations=["part-of", "applied-to", "extends"],
        example_atom="2026-05-24-method-scaled-dot-product-attention",
        first_seen=now(),
        auto_registered=False,
    ),
    TypeDef(
        key="finding",
        description="An empirical result or observation reported by the paper.",
        suggested_attributes=["domain.primary", "domain.sub", "evidence.type", "evidence.sample-size"],
        suggested_relations=["supported-by", "refuted-by", "contradicts"],
        example_atom="2026-05-24-finding-bleu-transformer-wmt2014",
        first_seen=now(),
        auto_registered=False,
    ),
]


# ── seed attribute registry ─────────────────────────────────────────────


ATTRIBUTES = [
    AttributeDef(
        key="domain.primary",
        namespace="domain",
        description="Top-level scholarly field.",
        value_type="string",
        applicable_types=["claim", "method", "finding"],
        usage_count=7,
        first_seen=now(),
        auto_registered=False,
    ),
    AttributeDef(
        key="domain.sub",
        namespace="domain",
        description="Sub-field within the primary domain.",
        value_type="string",
        applicable_types=["claim", "method", "finding"],
        usage_count=7,
        first_seen=now(),
        auto_registered=False,
    ),
    AttributeDef(
        key="evidence.type",
        namespace="evidence",
        description="Source of support for this atom.",
        value_type="enum",
        allowed_values=["empirical", "theoretical", "anecdotal", "computational"],
        applicable_types=["claim", "finding"],
        usage_count=5,
        first_seen=now(),
        auto_registered=False,
    ),
    AttributeDef(
        key="evidence.confidence",
        namespace="evidence",
        description="How strongly the source supports this atom.",
        value_type="enum",
        allowed_values=["high", "medium", "low"],
        applicable_types=["claim", "finding"],
        usage_count=5,
        first_seen=now(),
        auto_registered=False,
    ),
    AttributeDef(
        key="evidence.sample-size",
        namespace="evidence",
        description="Number of subjects, samples, or examples in a study.",
        value_type="number",
        applicable_types=["finding"],
        usage_count=2,
        first_seen=now(),
        auto_registered=False,
    ),
    AttributeDef(
        key="method.class",
        namespace="method",
        description="Family of method (e.g. attention, convolution, recurrence).",
        value_type="string",
        applicable_types=["method"],
        usage_count=2,
        first_seen=now(),
        auto_registered=False,
    ),
    AttributeDef(
        key="temporal.year",
        namespace="temporal",
        description="Publication year of the source.",
        value_type="number",
        applicable_types=["claim", "method", "finding"],
        usage_count=4,
        first_seen=now(),
        auto_registered=False,
    ),
    AttributeDef(
        key="modality.length-regime",
        namespace="modality",
        description="Sequence-length regime the atom applies to.",
        value_type="string",
        applicable_types=["claim", "method"],
        usage_count=2,
        first_seen=now(),
        auto_registered=False,
    ),
]


# ── seed relation registry ──────────────────────────────────────────────


RELATIONS = [
    RelationDef(
        key="extends",
        namespace="inferential",
        description="Source atom generalizes or builds on the target atom.",
        inverse="extended-by",
        source_types=["claim", "finding", "method"],
        target_types=["claim", "method"],
        usage_count=3,
        first_seen=now(),
        auto_registered=False,
    ),
    RelationDef(
        key="contradicts",
        namespace="inferential",
        description="Source atom asserts something incompatible with the target.",
        inverse="contradicts",  # symmetric
        source_types=["claim", "finding"],
        target_types=["claim", "finding"],
        usage_count=2,
        first_seen=now(),
        auto_registered=False,
    ),
    RelationDef(
        key="supported-by",
        namespace="evidential",
        description="Target atom is evidence for the source atom.",
        inverse="supports",
        source_types=["claim"],
        target_types=["finding"],
        usage_count=2,
        first_seen=now(),
        auto_registered=False,
    ),
    RelationDef(
        key="part-of",
        namespace="compositional",
        description="Source atom is a component of the target atom.",
        inverse="contains",
        source_types=["claim", "method", "finding"],
        target_types=["method"],
        usage_count=2,
        first_seen=now(),
        auto_registered=False,
    ),
    RelationDef(
        key="applied-to",
        namespace="methodological",
        description="Method (source) is applied to a target domain or task.",
        source_types=["method"],
        target_types=["claim", "finding"],
        usage_count=1,
        first_seen=now(),
        auto_registered=False,
    ),
    RelationDef(
        key="refuted-by",
        namespace="evidential",
        description="Target atom refutes the source atom.",
        inverse="refutes",
        source_types=["claim", "finding"],
        target_types=["finding"],
        usage_count=0,
        first_seen=now(),
        auto_registered=False,
    ),
]


# ── seed atoms ──────────────────────────────────────────────────────────


SEED_ATOMS = [
    AtomicNote(
        metas=Metas(
            id="2026-05-24-claim-attention-quadratic",
            type="claim",
            created_at=now(),
            updated_at=now(),
            tags=["claim", "nlp", "attention", "complexity"],
        ),
        origin=Origin(scholar_action="seeded"),
        attributes={
            "domain.primary": "machine-learning",
            "domain.sub": "nlp",
            "evidence.type": "theoretical",
            "evidence.confidence": "high",
            "modality.length-regime": ">512 tokens",
            "temporal.year": 2017,
        },
        relations=[
            Relation(type="part-of", target="2026-05-24-method-scaled-dot-product-attention"),
            Relation(type="supported-by", target="2026-05-24-finding-attention-memory-empirical"),
        ],
        content=(
            "The standard scaled dot-product attention mechanism is O(n²) in sequence length, "
            "where n is the number of input tokens. Above ~512 tokens with typical hidden sizes, "
            "the attention matrix becomes the dominant memory and compute cost of the model."
        ),
    ),
    AtomicNote(
        metas=Metas(
            id="2026-05-24-method-scaled-dot-product-attention",
            type="method",
            created_at=now(),
            updated_at=now(),
            tags=["method", "nlp", "attention"],
        ),
        origin=Origin(scholar_action="seeded"),
        attributes={
            "domain.primary": "machine-learning",
            "domain.sub": "nlp",
            "method.class": "attention",
            "temporal.year": 2017,
            "modality.length-regime": "<= 4096 tokens",
        },
        relations=[
            Relation(type="extends", target="2026-05-24-claim-bahdanau-attention"),
        ],
        content=(
            "Scaled dot-product attention computes Attention(Q, K, V) = softmax(QKᵀ/√d_k) V, "
            "where d_k is the key dimension. The 1/√d_k scaling keeps the softmax gradient "
            "well-conditioned at large d_k."
        ),
    ),
    AtomicNote(
        metas=Metas(
            id="2026-05-24-finding-bleu-transformer-wmt2014",
            type="finding",
            created_at=now(),
            updated_at=now(),
            tags=["finding", "nlp", "machine-translation", "benchmarks"],
        ),
        origin=Origin(scholar_action="seeded"),
        attributes={
            "domain.primary": "machine-learning",
            "domain.sub": "nlp",
            "evidence.type": "empirical",
            "evidence.confidence": "high",
            "evidence.sample-size": 4500000,
            "temporal.year": 2017,
        },
        relations=[
            Relation(type="extends", target="2026-05-24-claim-attention-quadratic"),
        ],
        content=(
            "On WMT 2014 English-to-German, the Transformer base model achieves 27.3 BLEU, "
            "surpassing the prior best ensemble result while training in a fraction of the wall-clock time."
        ),
    ),
    AtomicNote(
        metas=Metas(
            id="2026-05-24-finding-attention-memory-empirical",
            type="finding",
            created_at=now(),
            updated_at=now(),
            tags=["finding", "nlp", "attention", "memory"],
        ),
        origin=Origin(scholar_action="seeded"),
        attributes={
            "domain.primary": "machine-learning",
            "domain.sub": "nlp",
            "evidence.type": "empirical",
            "evidence.confidence": "high",
            "evidence.sample-size": 64,
            "temporal.year": 2019,
        },
        relations=[],
        content=(
            "Empirical profiling of BERT-base at sequence length 1024 shows the attention "
            "activations occupy ~58% of total GPU memory, confirming the asymptotic O(n²) "
            "characterization in practice."
        ),
    ),
    AtomicNote(
        metas=Metas(
            id="2026-05-24-claim-bahdanau-attention",
            type="claim",
            created_at=now(),
            updated_at=now(),
            tags=["claim", "nlp", "attention", "rnn"],
        ),
        origin=Origin(scholar_action="seeded"),
        attributes={
            "domain.primary": "machine-learning",
            "domain.sub": "nlp",
            "evidence.type": "empirical",
            "evidence.confidence": "high",
            "temporal.year": 2014,
        },
        relations=[],
        content=(
            "Additive attention over a recurrent encoder lets a decoder align variable-length "
            "input and output sequences without a fixed-width bottleneck — improving machine "
            "translation BLEU on long sentences in particular."
        ),
    ),
    AtomicNote(
        metas=Metas(
            id="2026-05-24-claim-rnn-better-long-context",
            type="claim",
            created_at=now(),
            updated_at=now(),
            tags=["claim", "nlp", "rnn", "long-context"],
        ),
        origin=Origin(scholar_action="seeded"),
        attributes={
            "domain.primary": "machine-learning",
            "domain.sub": "nlp",
            "evidence.type": "anecdotal",
            "evidence.confidence": "low",
            "modality.length-regime": ">8192 tokens",
        },
        relations=[
            Relation(type="contradicts", target="2026-05-24-claim-attention-quadratic"),
        ],
        content=(
            "Some practitioners report that RNNs handle very long contexts (>8K tokens) more "
            "efficiently than vanilla attention, since RNN memory cost is linear in sequence length. "
            "The claim is folk knowledge — the supporting evidence is thin and the comparison "
            "usually ignores effective context utilisation."
        ),
    ),
    AtomicNote(
        metas=Metas(
            id="2026-05-24-method-multi-head-attention",
            type="method",
            created_at=now(),
            updated_at=now(),
            tags=["method", "nlp", "attention", "multi-head"],
        ),
        origin=Origin(scholar_action="seeded"),
        attributes={
            "domain.primary": "machine-learning",
            "domain.sub": "nlp",
            "method.class": "attention",
            "temporal.year": 2017,
        },
        relations=[
            Relation(type="extends", target="2026-05-24-method-scaled-dot-product-attention"),
        ],
        content=(
            "Multi-head attention runs h scaled dot-product attention operations in parallel "
            "over learned linear projections of Q, K, V. The h outputs are concatenated and "
            "projected back to d_model, letting the model attend to information from different "
            "representation subspaces."
        ),
    ),
]


# ── runner ──────────────────────────────────────────────────────────────


def main() -> None:
    print("seeding type registry …")
    for t in TYPES:
        vault_io.write_type_def(t)
    print(f"  {len(TYPES)} types written")

    print("seeding attribute registry …")
    for a in ATTRIBUTES:
        vault_io.write_attribute_def(a)
    print(f"  {len(ATTRIBUTES)} attributes written")

    print("seeding relation registry …")
    for r in RELATIONS:
        vault_io.write_relation_def(r)
    print(f"  {len(RELATIONS)} relations written")

    print("appending schema-evolution audit …")
    vault_io.append_schema_evolution(
        {
            "timestamp": now().isoformat(),
            "action": "seed",
            "kind": "initial",
            "types": len(TYPES),
            "attributes": len(ATTRIBUTES),
            "relations": len(RELATIONS),
            "atoms": len(SEED_ATOMS),
        }
    )

    print("seeding atoms + projections + embeddings …")
    embeds: list[tuple[str, str]] = []
    for atom in SEED_ATOMS:
        vault_io.write_atom(atom)
        db.upsert_atom_projection(atom)
        embeds.append((atom.metas.id, atom.content))
    semantic_service.atoms_store().upsert_many(embeds)
    print(f"  {len(SEED_ATOMS)} atoms written + embedded")

    print("done.")


if __name__ == "__main__":
    main()
