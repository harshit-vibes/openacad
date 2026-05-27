"""Shared FastAPI dependencies for the playground API.

The Vault holds an open SQLite connection + sentence-transformer encoder
state, so we keep a single module-level lazy singleton rather than building
one per request.
"""

from __future__ import annotations

import os
from pathlib import Path

from openacad.vault import Vault


_DEFAULT_VAULT_PATH = "data/vault"
_VAULT: Vault | None = None


def vault_path() -> Path:
    """Resolve the vault path from the OPENACAD_VAULT_PATH env var."""
    return Path(os.environ.get("OPENACAD_VAULT_PATH", _DEFAULT_VAULT_PATH))


def get_vault() -> Vault:
    """Return the process-wide Vault singleton (lazy)."""
    global _VAULT
    if _VAULT is None:
        # encoder=None keeps semantic-search disabled until somebody uses
        # it; the EmbeddingIndex lazy-loads when add() is called.
        _VAULT = Vault(vault_path(), create=True)
    return _VAULT


def reset_vault() -> None:
    """Reset the singleton (used by tests)."""
    global _VAULT
    if _VAULT is not None:
        try:
            _VAULT.close()
        except Exception:  # noqa: BLE001
            pass
    _VAULT = None


__all__ = ["get_vault", "reset_vault", "vault_path"]
