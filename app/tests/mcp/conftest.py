"""Fixtures for tests/mcp.

If the optional `mcp` SDK isn't installed, every test in this directory is
skipped (rather than failing) — the SDK is an opt-in extra, not a base
requirement.
"""

from __future__ import annotations

import pytest


@pytest.fixture(scope="session")
def mcp_lib_available() -> bool:
    """True iff the optional `mcp` Python SDK is importable.

    Tests should use `pytest.importorskip("mcp")` directly when they actually need
    the SDK; this fixture is here for tests that want to branch on availability.
    """
    try:
        import mcp  # noqa: F401
        return True
    except ImportError:
        return False


@pytest.fixture
def tmp_vault(tmp_path):
    """A fresh empty Vault rooted at a temp directory."""
    from openacad.vault import Vault

    return Vault(tmp_path / "vault")
