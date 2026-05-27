"""Sidecar SQLite store: FTS5 mirror of atom bodies + activity log + tool-call log.

Lives at ``<vault>/.openacad/index/cache.sqlite``. Mirrors atom bodies
into an FTS5 virtual table so ``vault.search()`` returns matches by id.
The mirror is rebuildable from disk — atoms are the source of truth; the
SQLite file is a cache.

Activity log is an append-only JSONL at ``<vault>/.openacad/activity.jsonl``
(not in the SQLite file, so it's easy to ``tail -f`` from the shell).
"""

from __future__ import annotations

import json
import sqlite3
import time
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS atoms (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    status TEXT NOT NULL,
    body TEXT NOT NULL,
    aliases_json TEXT NOT NULL DEFAULT '[]',
    tags_json TEXT NOT NULL DEFAULT '[]',
    updated_at TEXT NOT NULL
);

CREATE VIRTUAL TABLE IF NOT EXISTS atoms_fts USING fts5(
    id UNINDEXED,
    body,
    aliases,
    tags
);

CREATE TABLE IF NOT EXISTS tool_calls (
    rowid INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    agent TEXT,
    tool TEXT NOT NULL,
    args_json TEXT NOT NULL,
    result_json TEXT,
    duration_ms INTEGER,
    error TEXT
);

CREATE INDEX IF NOT EXISTS idx_atoms_status ON atoms(status);
CREATE INDEX IF NOT EXISTS idx_atoms_type ON atoms(type);
"""


def _utcnow() -> str:
    return datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


class Store:
    """Connection wrapper. Caller is responsible for lifecycle (``close()``)."""

    def __init__(self, db_path: str | Path, *, activity_path: str | Path | None = None) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.activity_path: Path | None = (
            Path(activity_path) if activity_path is not None else None
        )
        if self.activity_path is not None:
            self.activity_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(
            str(self.db_path),
            isolation_level=None,  # autocommit; we use explicit transactions
            check_same_thread=False,
        )
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript("PRAGMA journal_mode=WAL;")
        self._conn.executescript(SCHEMA)

    @property
    def conn(self) -> sqlite3.Connection:
        return self._conn

    def close(self) -> None:
        try:
            self._conn.close()
        except sqlite3.ProgrammingError:
            pass

    # ------------------------------------------------------------------
    # atom mirror (FTS + metadata)
    # ------------------------------------------------------------------

    def upsert_atom(
        self,
        *,
        id: str,
        type: str,
        status: str,
        body: str,
        aliases: list[str],
        tags: list[str],
        updated_at: str,
    ) -> None:
        with self._transaction():
            self._conn.execute("DELETE FROM atoms_fts WHERE id = ?", (id,))
            self._conn.execute(
                """
                INSERT INTO atoms (id, type, status, body, aliases_json, tags_json, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    type=excluded.type,
                    status=excluded.status,
                    body=excluded.body,
                    aliases_json=excluded.aliases_json,
                    tags_json=excluded.tags_json,
                    updated_at=excluded.updated_at
                """,
                (
                    id,
                    type,
                    status,
                    body,
                    json.dumps(aliases),
                    json.dumps(tags),
                    updated_at,
                ),
            )
            self._conn.execute(
                "INSERT INTO atoms_fts (id, body, aliases, tags) VALUES (?, ?, ?, ?)",
                (id, body, " ".join(aliases), " ".join(tags)),
            )

    def delete_atom(self, id: str) -> None:
        with self._transaction():
            self._conn.execute("DELETE FROM atoms_fts WHERE id = ?", (id,))
            self._conn.execute("DELETE FROM atoms WHERE id = ?", (id,))

    def all_atom_ids(self) -> list[str]:
        rows = self._conn.execute("SELECT id FROM atoms ORDER BY id").fetchall()
        return [r["id"] for r in rows]

    def search(self, query: str, *, top_k: int = 10) -> list[str]:
        """Return matching atom ids in relevance order.

        Query tokens are quoted before being passed to FTS5 to keep
        operator characters (``-``, ``"``, ``*``) from breaking the
        parser. Pass the raw FTS5 syntax via :meth:`raw_search` if you
        need phrase or NEAR queries.
        """
        if not query.strip():
            return []
        tokens = _tokenise(query)
        if not tokens:
            return []
        safe_query = " ".join(f'"{t}"' for t in tokens)
        try:
            rows = self._conn.execute(
                """
                SELECT id FROM atoms_fts
                WHERE atoms_fts MATCH ?
                ORDER BY bm25(atoms_fts)
                LIMIT ?
                """,
                (safe_query, top_k),
            ).fetchall()
        except sqlite3.OperationalError:
            return []
        return [r["id"] for r in rows]

    def raw_search(self, fts_query: str, *, top_k: int = 10) -> list[str]:
        """Run an arbitrary FTS5 query (caller is responsible for syntax)."""
        rows = self._conn.execute(
            """
            SELECT id FROM atoms_fts
            WHERE atoms_fts MATCH ?
            ORDER BY bm25(atoms_fts)
            LIMIT ?
            """,
            (fts_query, top_k),
        ).fetchall()
        return [r["id"] for r in rows]

    # ------------------------------------------------------------------
    # tool-call log
    # ------------------------------------------------------------------

    def record_tool_call(
        self,
        *,
        tool: str,
        agent: str | None = None,
        args: dict[str, Any] | None = None,
        result: Any | None = None,
        duration_ms: int | None = None,
        error: str | None = None,
    ) -> int:
        cur = self._conn.execute(
            """
            INSERT INTO tool_calls (ts, agent, tool, args_json, result_json, duration_ms, error)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                _utcnow(),
                agent,
                tool,
                json.dumps(args or {}),
                json.dumps(result, default=str) if result is not None else None,
                duration_ms,
                error,
            ),
        )
        return int(cur.lastrowid or 0)

    # ------------------------------------------------------------------
    # activity log (JSONL appender)
    # ------------------------------------------------------------------

    def append_activity(self, event: str, **payload: Any) -> None:
        if self.activity_path is None:
            return
        entry = {"ts": _utcnow(), "event": event, **payload}
        with self.activity_path.open("a", encoding="utf-8") as fp:
            fp.write(json.dumps(entry, default=str))
            fp.write("\n")

    def read_activity(self) -> Iterator[dict[str, Any]]:
        if self.activity_path is None or not self.activity_path.exists():
            return iter(())
        return _iter_jsonl(self.activity_path)

    # ------------------------------------------------------------------
    # transactional helper
    # ------------------------------------------------------------------

    @contextmanager
    def _transaction(self):
        self._conn.execute("BEGIN")
        try:
            yield
            self._conn.execute("COMMIT")
        except Exception:
            self._conn.execute("ROLLBACK")
            raise

    # ------------------------------------------------------------------
    # batch helpers (used by reindex)
    # ------------------------------------------------------------------

    def rebuild_from(self, atoms: Iterable) -> None:
        """Wipe and re-mirror every atom. Used by ``vault.reindex()``."""
        with self._transaction():
            self._conn.execute("DELETE FROM atoms_fts")
            self._conn.execute("DELETE FROM atoms")
        for atom in atoms:
            self.upsert_atom(
                id=atom.id,
                type=atom.type,
                status=atom.status,
                body=atom.body,
                aliases=list(atom.aliases),
                tags=list(atom.tags),
                updated_at=atom.updated_at,
            )


def _tokenise(text: str) -> list[str]:
    """Conservative tokenisation for FTS fallback (alnum + dashes)."""
    out: list[str] = []
    cur: list[str] = []
    for ch in text:
        if ch.isalnum() or ch in ("-", "_"):
            cur.append(ch)
        else:
            if cur:
                out.append("".join(cur))
                cur = []
    if cur:
        out.append("".join(cur))
    return out


def _iter_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as fp:
        for line in fp:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                # ignore malformed lines — activity log is best-effort
                continue


# Re-export ``time`` so callers can use ``store.time.monotonic()`` in
# tool-call timing without an extra import; harmless and keeps the
# call sites tidy.
__all__ = ["Store", "time"]
