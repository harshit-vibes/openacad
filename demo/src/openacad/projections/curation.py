"""Curation projection — pending drafts, verdict history, and verdict counts.

A draft is *pending* if it exists in the drafts table but has no terminal
accept/edit/reject event referencing its `draft_id`.
"""

from __future__ import annotations

from openacad.runtime import db
from openacad.runtime.scenario import use_scenario

from openacad.projections._models import CurationView, DraftRow, VerdictRow


_VERDICT_KINDS = ("accept", "edit", "reject", "deprecate")
_PAYLOAD_PREVIEW_CHARS = 200


def _draft_id_from_event(ev) -> str | None:
    """Pull draft_id from an event payload if present.

    EvalEvent payload shape is free-form dict; the curation events emitted by
    the pipeline put the draft id under "draft_id". Fall back to "target_id"
    if encountered.
    """
    payload = ev.payload or {}
    return payload.get("draft_id") or payload.get("target_id") or None


def curation_summary(scenario_key: str = "evolving-notes") -> CurationView:
    with use_scenario(scenario_key):
        # Collect all verdict events first — we need them for both the history
        # table and to compute the pending-drafts set.
        verdict_events_by_kind: dict[str, list] = {}
        for kind in _VERDICT_KINDS:
            verdict_events_by_kind[kind] = db.list_events(kind=kind, limit=1000)

        # Counts per kind (always include all four, even if seeded vault has none).
        counts: dict[str, int] = {k: len(v) for k, v in verdict_events_by_kind.items()}

        # Flatten verdict history, sort newest first.
        all_verdicts = [
            VerdictRow(
                event_id=ev.id,
                timestamp=ev.timestamp,
                kind=ev.kind,
                draft_id=_draft_id_from_event(ev),
                actor=ev.actor,
                delta=ev.payload or {},
            )
            for kind in _VERDICT_KINDS
            for ev in verdict_events_by_kind[kind]
        ]
        all_verdicts.sort(key=lambda r: r.timestamp, reverse=True)

        # Build the set of "resolved" draft ids — any draft mentioned by any
        # verdict event is considered no longer pending.
        resolved: set[str] = set()
        for evs in verdict_events_by_kind.values():
            for ev in evs:
                did = _draft_id_from_event(ev)
                if did:
                    resolved.add(did)

        # Walk every source's drafts and gather the pending ones.
        pending_drafts: list[DraftRow] = []
        for src in db.list_sources():
            for d in db.drafts_for_source(src.id):
                if d.draft_id in resolved:
                    continue
                # payload preview: lean on the content if present, else the suggested_id.
                preview = (d.content or d.suggested_id or "")[:_PAYLOAD_PREVIEW_CHARS]
                pending_drafts.append(
                    DraftRow(
                        draft_id=d.draft_id,
                        source_id=d.source_id,
                        drafted_at=d.drafted_at,
                        prompt_version=d.prompt_version,
                        payload_preview=preview,
                    )
                )

        counts["pending"] = len(pending_drafts)

        return CurationView(
            pending_drafts=pending_drafts,
            verdict_history=all_verdicts,
            counts=counts,
        )
