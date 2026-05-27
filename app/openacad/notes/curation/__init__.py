"""HITL gate — accept / edit / reject a draft into the vault."""

from openacad.notes.curation._legacy import accept, edit_and_accept, reject

# Back-compat alias: pages use `curate_service.edit` for the edit-and-accept op.
edit = edit_and_accept

__all__ = ["accept", "edit", "edit_and_accept", "reject"]
