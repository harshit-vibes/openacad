"""Coverage assessment: given an external artifact (as raw text or chunks)
and the active scenario's notes vault, find which notes the artifact
ALREADY references / could cite / is missing.

MVP: split the artifact into windowed passages, semantic-search the vault
per passage, report covered notes vs. notes the artifact never approached.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from openacad.artifacts.schema import Assessment
from openacad.notes.persistence import vault as vault_io
from openacad.notes.query import semantic as semantic_query
from openacad.runtime.scenario import active_scenario
from openacad.feedback.timeline import log_event


def assess_coverage(
    artifact_text: str,
    artifact_id: str = "",
    passage_size: int = 800,
    top_k_per_passage: int = 5,
    similarity_threshold: float = 0.45,
) -> Assessment:
    """Walk the artifact's passages and find note coverage.

    Returns an Assessment with:
      - `supporting_notes`: notes that scored high vs at least one passage
      - `missing_topics`: tags from vault notes that no passage touched
    """
    s = active_scenario()
    assessment_id = f"as-{uuid.uuid4().hex[:8]}"
    if not artifact_id:
        artifact_id = f"ext-{uuid.uuid4().hex[:8]}"

    # Split artifact into rough passages.
    passages = []
    for i in range(0, len(artifact_text), passage_size):
        passages.append(artifact_text[i : i + passage_size])

    # All atoms in the active vault — for the "missing" calc.
    all_atoms = vault_io.list_atoms()
    all_atom_ids = {a.metas.id for a in all_atoms}

    referenced: set[str] = set()
    findings: list[dict] = []

    store = semantic_query.atoms_store()
    for idx, passage in enumerate(passages):
        try:
            hits = store.search(passage, limit=top_k_per_passage)
        except Exception as e:
            findings.append({"passage_idx": idx, "error": str(e)})
            continue
        for atom_id, score in hits:
            if score < similarity_threshold:
                continue
            referenced.add(atom_id)
            findings.append({
                "passage_idx": idx,
                "atom_id": atom_id,
                "score": round(float(score), 3),
            })

    missing = sorted(all_atom_ids - referenced)
    coverage_ratio = len(referenced) / max(len(all_atom_ids), 1)

    summary = (
        f"Artifact covers {len(referenced)} of {len(all_atom_ids)} vault notes "
        f"({coverage_ratio:.0%}). {len(missing)} notes were not referenced by "
        f"any passage at threshold ≥{similarity_threshold}."
    )

    assessment = Assessment(
        id=assessment_id,
        target_artifact_id=artifact_id,
        created_at=datetime.now(timezone.utc),
        scenario_key=s.key,
        kind="coverage",
        summary=summary,
        findings=findings,
        supporting_notes=sorted(referenced),
        missing_topics=missing[:50],   # cap to avoid huge reports
    )

    log_event("artifact_assessed", {
        "assessment_id": assessment_id,
        "artifact_id": artifact_id,
        "kind": "coverage",
        "coverage_ratio": round(coverage_ratio, 3),
        "referenced_count": len(referenced),
    })
    return assessment


__all__ = ["assess_coverage"]
