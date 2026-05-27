"""CLI entry point: `python -m openacad.mcp --vault <path>`.

Starts the MCP stdio server bound to the given vault directory.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m openacad.mcp",
        description=(
            "Start the openacad MCP stdio server. Exposes the vault's tool registry "
            "(search_vault, semantic_search, get_atom, propose_atom, ...) to any "
            "MCP-aware client (Claude Code, Claude Desktop, Cursor, Zed)."
        ),
    )
    parser.add_argument(
        "--vault",
        required=True,
        type=Path,
        help="Path to the openacad vault directory (will be created if missing).",
    )
    parser.add_argument(
        "--name",
        default="openacad",
        help="MCP server name advertised to the client (default: openacad).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    # Import openacad.mcp.server lazily so --help works even if `mcp` SDK is missing.
    try:
        from openacad.mcp.server import build_server, run_stdio
    except ImportError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    # Bind vault. Vault.__init__ creates the directory if needed.
    from openacad.vault import Vault

    vault_path = args.vault.expanduser().resolve()
    try:
        vault = Vault(vault_path)
    except Exception as e:  # noqa: BLE001
        print(f"error: could not open vault at {vault_path}: {e}", file=sys.stderr)
        return 1

    try:
        server = build_server(vault, name=args.name)
    except ImportError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    try:
        asyncio.run(run_stdio(server))
    except KeyboardInterrupt:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
