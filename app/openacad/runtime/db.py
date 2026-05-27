"""Scenario-aware SQLite storage.

Two storage tiers:

- **Shared**: `data/shared.sqlite` holds `sources`, `chunks`, and `chunks_fts`.
  Every scenario reads the same PDFs and chunks, so there's no point duplicating.

- **Per-scenario**: `data/vaults/<key>/state.sqlite` holds everything that the
  scenario's atoms produce or consume — drafts, eval events, comparisons,
  tool_calls, rubrics, atom projections, atoms_fts, prompts, proposals.
  Switching scenarios switches the connection.

Code outside this module reads the active scenario via
`openacad.runtime.scenario.use_scenario(key)` / `active_scenario()`.

WAL mode + busy_timeout keep PydanticAI parallel tool-call writers safe.
"""

import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator, Literal

from openacad.notes.schema import AtomicNote, DraftAtom

from openacad.runtime.corpus.source import Chunk, PaperSource

from openacad.feedback.schema import ComparisonResult, EvalEvent, PromptVersion, ToolCall

from openacad.notes.registry.schema import Proposal
from openacad.runtime.scenario import active_scenario, shared_db_path

# Per-thread connection cache keyed by "shared" or scenario_key.
_local = threading.local()
_init_lock = threading.Lock()
_initialized_for: set[str] = set()


def _conn_for(key: str) -> sqlite3.Connection:
    """Return (and lazily create) a thread-local connection for the given store key.

    key is either "shared" or a scenario key.
    """
    cache: dict[str, sqlite3.Connection] = getattr(_local, "conns", None)
    if cache is None:
        cache = {}
        _local.conns = cache
    conn = cache.get(key)
    if conn is None:
        path = _resolve_path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(
            path,
            timeout=30.0,
            isolation_level=None,  # autocommit; we BEGIN/COMMIT explicitly when needed
            check_same_thread=False,
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA busy_timeout=30000;")
        conn.execute("PRAGMA foreign_keys=ON;")
        cache[key] = conn
    return conn


def _resolve_path(key: str) -> Path:
    if key == "shared":
        return shared_db_path()
    # Scenario key
    from openacad.runtime.scenario import SCENARIOS_BY_KEY
    if key not in SCENARIOS_BY_KEY:
        raise ValueError(f"unknown store key: {key!r}")
    return SCENARIOS_BY_KEY[key].state_db_path


def _init_and_get(key: str) -> sqlite3.Connection:
    """Get connection and initialize its schema once."""
    conn = _conn_for(key)
    if key not in _initialized_for:
        with _init_lock:
            if key not in _initialized_for:
                schema = _SHARED_SCHEMA_SQL if key == "shared" else _SCENARIO_SCHEMA_SQL
                conn.executescript(schema)
                # ── per-scenario in-place migrations ────────────────────
                # Older scenario DBs may pre-date the tool_calls.error_message
                # column. ALTER is idempotent-by-exception: if the column is
                # already there, SQLite raises OperationalError and we move on.
                if key != "shared":
                    try:
                        conn.execute(
                            "ALTER TABLE tool_calls ADD COLUMN error_message TEXT"
                        )
                    except sqlite3.OperationalError:
                        pass  # column already exists
                _initialized_for.add(key)
    return conn


def _shared() -> sqlite3.Connection:
    return _init_and_get("shared")


def _scenario() -> sqlite3.Connection:
    return _init_and_get(active_scenario().key)


@contextmanager
def transaction(target: Literal["shared", "scenario"] = "scenario") -> Iterator[sqlite3.Connection]:
    c = _shared() if target == "shared" else _scenario()
    c.execute("BEGIN IMMEDIATE")
    try:
        yield c
    except Exception:
        c.execute("ROLLBACK")
        raise
    else:
        c.execute("COMMIT")


# ── schemas ─────────────────────────────────────────────────────────────


_SHARED_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS sources (
    id TEXT PRIMARY KEY,
    filename TEXT NOT NULL,
    title TEXT,
    uploaded_at TEXT NOT NULL,
    n_pages INTEGER NOT NULL,
    n_chunks INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS chunks (
    id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    ordinal INTEGER NOT NULL,
    text TEXT NOT NULL,
    page_start INTEGER NOT NULL,
    page_end INTEGER NOT NULL,
    char_start INTEGER NOT NULL DEFAULT 0,
    char_end INTEGER NOT NULL DEFAULT 0,
    metadata_json TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS chunks_by_source ON chunks(source_id, ordinal);

CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
    chunk_id UNINDEXED,
    source_id UNINDEXED,
    text,
    tokenize='unicode61 remove_diacritics 2'
);
"""

_SCENARIO_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS atoms_index (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    tags_json TEXT NOT NULL DEFAULT '[]',
    source_id TEXT,
    page_start INTEGER,
    page_end INTEGER,
    attributes_json TEXT NOT NULL DEFAULT '{}',
    relation_types_json TEXT NOT NULL DEFAULT '[]',
    relation_targets_json TEXT NOT NULL DEFAULT '[]',
    content TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS atoms_type ON atoms_index(type);
CREATE INDEX IF NOT EXISTS atoms_status ON atoms_index(status);
CREATE INDEX IF NOT EXISTS atoms_source ON atoms_index(source_id);

CREATE VIRTUAL TABLE IF NOT EXISTS atoms_fts USING fts5(
    atom_id UNINDEXED,
    content,
    tokenize='unicode61 remove_diacritics 2'
);

CREATE TABLE IF NOT EXISTS drafts (
    draft_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    drafted_at TEXT NOT NULL,
    prompt_version TEXT NOT NULL,
    suggested_id TEXT NOT NULL,
    type TEXT NOT NULL,
    payload_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS drafts_by_source ON drafts(source_id);

CREATE TABLE IF NOT EXISTS events (
    id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    kind TEXT NOT NULL,
    actor TEXT NOT NULL DEFAULT 'scholar',
    payload_json TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS events_by_kind ON events(kind, timestamp DESC);
CREATE INDEX IF NOT EXISTS events_by_ts ON events(timestamp DESC);

CREATE TABLE IF NOT EXISTS prompts (
    version TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL,
    body TEXT NOT NULL,
    parent_version TEXT,
    state TEXT NOT NULL DEFAULT 'proposed',
    accept_rate REAL,
    avg_edit_distance REAL,
    based_on_events_json TEXT NOT NULL DEFAULT '[]'
);

CREATE TABLE IF NOT EXISTS proposals (
    id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    key TEXT NOT NULL,
    proposed_at TEXT NOT NULL,
    triggered_by TEXT NOT NULL,
    payload_json TEXT NOT NULL DEFAULT '{}',
    state TEXT NOT NULL DEFAULT 'pending',
    rationale TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS proposals_state ON proposals(state);

CREATE TABLE IF NOT EXISTS comparisons (
    id TEXT PRIMARY KEY,
    question TEXT NOT NULL,
    paper_ids_json TEXT NOT NULL,
    pipeline TEXT NOT NULL,
    answer TEXT NOT NULL,
    citations_json TEXT NOT NULL DEFAULT '[]',
    tokens_in INTEGER NOT NULL DEFAULT 0,
    tokens_out INTEGER NOT NULL DEFAULT 0,
    latency_ms INTEGER NOT NULL DEFAULT 0,
    accuracy_vs_gold REAL,
    citation_precision REAL,
    n_units_retrieved INTEGER NOT NULL DEFAULT 0,
    tool_call_ids_json TEXT NOT NULL DEFAULT '[]',
    run_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS comparisons_pipeline ON comparisons(pipeline);

CREATE TABLE IF NOT EXISTS tool_calls (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    agent TEXT NOT NULL,
    tool_name TEXT NOT NULL,
    arguments_json TEXT NOT NULL DEFAULT '{}',
    n_results INTEGER NOT NULL DEFAULT 0,
    latency_ms INTEGER NOT NULL DEFAULT 0,
    timestamp TEXT NOT NULL,
    error_message TEXT NULL
);
CREATE INDEX IF NOT EXISTS tool_calls_session ON tool_calls(session_id);

CREATE TABLE IF NOT EXISTS rubrics (
    id TEXT PRIMARY KEY,
    role TEXT NOT NULL,
    target_id TEXT NOT NULL,
    overall INTEGER NOT NULL,
    criteria_json TEXT NOT NULL DEFAULT '{}',
    free_text TEXT NOT NULL DEFAULT '',
    rater TEXT NOT NULL DEFAULT 'scholar',
    timestamp TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS rubrics_role_ts ON rubrics(role, timestamp DESC);
"""


# ── projections ─────────────────────────────────────────────────────────


def project_atom(atom: AtomicNote) -> dict[str, Any]:
    return {
        "id": atom.metas.id,
        "type": atom.metas.type,
        "status": atom.metas.status,
        "created_at": atom.metas.created_at.isoformat(),
        "updated_at": atom.metas.updated_at.isoformat(),
        "tags_json": json.dumps(atom.metas.tags),
        "source_id": atom.origin.source_id,
        "page_start": atom.origin.page_range[0] if atom.origin.page_range else None,
        "page_end": atom.origin.page_range[1] if atom.origin.page_range else None,
        "attributes_json": json.dumps(atom.attributes, default=str),
        "relation_types_json": json.dumps([r.type for r in atom.relations]),
        "relation_targets_json": json.dumps([r.target for r in atom.relations]),
        "content": atom.content,
    }


# ── sources (SHARED) ────────────────────────────────────────────────────


def upsert_source(s: PaperSource) -> None:
    with transaction("shared") as c:
        c.execute(
            """INSERT INTO sources (id, filename, title, uploaded_at, n_pages, n_chunks)
               VALUES (?,?,?,?,?,?)
               ON CONFLICT(id) DO UPDATE SET
                 filename=excluded.filename, title=excluded.title,
                 uploaded_at=excluded.uploaded_at, n_pages=excluded.n_pages,
                 n_chunks=excluded.n_chunks""",
            (s.id, s.filename, s.title, s.uploaded_at.isoformat(), s.n_pages, s.n_chunks),
        )


def list_sources() -> list[PaperSource]:
    rows = _shared().execute("SELECT * FROM sources ORDER BY uploaded_at").fetchall()
    return [
        PaperSource(
            id=r["id"], filename=r["filename"], title=r["title"],
            uploaded_at=datetime.fromisoformat(r["uploaded_at"]),
            n_pages=r["n_pages"], n_chunks=r["n_chunks"],
        )
        for r in rows
    ]


def get_source(source_id: str) -> PaperSource | None:
    r = _shared().execute("SELECT * FROM sources WHERE id=?", (source_id,)).fetchone()
    if not r:
        return None
    return PaperSource(
        id=r["id"], filename=r["filename"], title=r["title"],
        uploaded_at=datetime.fromisoformat(r["uploaded_at"]),
        n_pages=r["n_pages"], n_chunks=r["n_chunks"],
    )


# ── chunks (SHARED) ─────────────────────────────────────────────────────


def upsert_chunk(c_obj: Chunk) -> None:
    with transaction("shared") as c:
        c.execute(
            """INSERT INTO chunks (id, source_id, ordinal, text, page_start, page_end,
                                   char_start, char_end, metadata_json)
               VALUES (?,?,?,?,?,?,?,?,?)
               ON CONFLICT(id) DO UPDATE SET
                 source_id=excluded.source_id, ordinal=excluded.ordinal, text=excluded.text,
                 page_start=excluded.page_start, page_end=excluded.page_end,
                 char_start=excluded.char_start, char_end=excluded.char_end,
                 metadata_json=excluded.metadata_json""",
            (
                c_obj.id, c_obj.source_id, c_obj.ordinal, c_obj.text,
                c_obj.page_range[0], c_obj.page_range[1],
                c_obj.char_range[0], c_obj.char_range[1],
                json.dumps(c_obj.metadata),
            ),
        )
        # Keep FTS5 mirror in sync
        c.execute("DELETE FROM chunks_fts WHERE chunk_id=?", (c_obj.id,))
        c.execute(
            "INSERT INTO chunks_fts (chunk_id, source_id, text) VALUES (?,?,?)",
            (c_obj.id, c_obj.source_id, c_obj.text),
        )


def upsert_chunks(chunks: list[Chunk]) -> None:
    with transaction("shared") as c:
        for ch in chunks:
            c.execute(
                """INSERT INTO chunks (id, source_id, ordinal, text, page_start, page_end,
                                       char_start, char_end, metadata_json)
                   VALUES (?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(id) DO UPDATE SET
                     source_id=excluded.source_id, ordinal=excluded.ordinal, text=excluded.text,
                     page_start=excluded.page_start, page_end=excluded.page_end,
                     char_start=excluded.char_start, char_end=excluded.char_end,
                     metadata_json=excluded.metadata_json""",
                (
                    ch.id, ch.source_id, ch.ordinal, ch.text,
                    ch.page_range[0], ch.page_range[1],
                    ch.char_range[0], ch.char_range[1],
                    json.dumps(ch.metadata),
                ),
            )
            c.execute("DELETE FROM chunks_fts WHERE chunk_id=?", (ch.id,))
            c.execute(
                "INSERT INTO chunks_fts (chunk_id, source_id, text) VALUES (?,?,?)",
                (ch.id, ch.source_id, ch.text),
            )


def chunks_for_source(source_id: str) -> list[Chunk]:
    rows = _shared().execute(
        "SELECT * FROM chunks WHERE source_id=? ORDER BY ordinal", (source_id,)
    ).fetchall()
    return [
        Chunk(
            id=r["id"], source_id=r["source_id"], ordinal=r["ordinal"], text=r["text"],
            page_range=(r["page_start"], r["page_end"]),
            char_range=(r["char_start"], r["char_end"]),
            metadata=json.loads(r["metadata_json"]),
        )
        for r in rows
    ]


def get_chunk(chunk_id: str) -> Chunk | None:
    r = _shared().execute("SELECT * FROM chunks WHERE id=?", (chunk_id,)).fetchone()
    if not r:
        return None
    return Chunk(
        id=r["id"], source_id=r["source_id"], ordinal=r["ordinal"], text=r["text"],
        page_range=(r["page_start"], r["page_end"]),
        char_range=(r["char_start"], r["char_end"]),
        metadata=json.loads(r["metadata_json"]),
    )


def search_chunks_fts(query: str, limit: int = 10, source_id: str | None = None) -> list[Chunk]:
    """Top-K chunks by SQLite FTS5/BM25, optionally narrowed by source."""
    fts_q = _fts5_safe_query(query)
    if not fts_q:
        return []
    if source_id:
        rows = _shared().execute(
            "SELECT c.* FROM chunks_fts f JOIN chunks c ON c.id = f.chunk_id "
            "WHERE chunks_fts MATCH ? AND c.source_id = ? ORDER BY rank LIMIT ?",
            (fts_q, source_id, limit),
        ).fetchall()
    else:
        rows = _shared().execute(
            "SELECT c.* FROM chunks_fts f JOIN chunks c ON c.id = f.chunk_id "
            "WHERE chunks_fts MATCH ? ORDER BY rank LIMIT ?",
            (fts_q, limit),
        ).fetchall()
    return [
        Chunk(
            id=r["id"], source_id=r["source_id"], ordinal=r["ordinal"], text=r["text"],
            page_range=(r["page_start"], r["page_end"]),
            char_range=(r["char_start"], r["char_end"]),
            metadata=json.loads(r["metadata_json"]),
        )
        for r in rows
    ]


# ── atoms_index + FTS5 (per-scenario) ───────────────────────────────────


def upsert_atom_projection(atom: AtomicNote) -> None:
    p = project_atom(atom)
    with transaction("scenario") as c:
        c.execute(
            """INSERT INTO atoms_index
                 (id, type, status, created_at, updated_at, tags_json, source_id,
                  page_start, page_end, attributes_json, relation_types_json,
                  relation_targets_json, content)
               VALUES (:id, :type, :status, :created_at, :updated_at, :tags_json,
                       :source_id, :page_start, :page_end, :attributes_json,
                       :relation_types_json, :relation_targets_json, :content)
               ON CONFLICT(id) DO UPDATE SET
                 type=excluded.type, status=excluded.status,
                 updated_at=excluded.updated_at, tags_json=excluded.tags_json,
                 source_id=excluded.source_id, page_start=excluded.page_start,
                 page_end=excluded.page_end, attributes_json=excluded.attributes_json,
                 relation_types_json=excluded.relation_types_json,
                 relation_targets_json=excluded.relation_targets_json,
                 content=excluded.content""",
            p,
        )
        c.execute("DELETE FROM atoms_fts WHERE atom_id=?", (atom.metas.id,))
        c.execute("INSERT INTO atoms_fts (atom_id, content) VALUES (?,?)", (atom.metas.id, atom.content))


def remove_atom_projection(atom_id: str) -> None:
    with transaction("scenario") as c:
        c.execute("DELETE FROM atoms_index WHERE id=?", (atom_id,))
        c.execute("DELETE FROM atoms_fts WHERE atom_id=?", (atom_id,))


def list_atom_projections(where: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    rows = _scenario().execute("SELECT * FROM atoms_index").fetchall()
    out: list[dict[str, Any]] = []
    for r in rows:
        attrs = json.loads(r["attributes_json"])
        flat = {
            "id": r["id"],
            "type": r["type"],
            "status": r["status"],
            "created_at": r["created_at"],
            "updated_at": r["updated_at"],
            "tags": json.loads(r["tags_json"]),
            "source_id": r["source_id"],
            "page_range": [r["page_start"], r["page_end"]] if r["page_start"] is not None else None,
            "relation_types": json.loads(r["relation_types_json"]),
            "relation_targets": json.loads(r["relation_targets_json"]),
        }
        for k, v in attrs.items():
            flat[f"attr.{k}"] = v
        if where and not all(flat.get(k) == v for k, v in where.items()):
            continue
        out.append(flat)
    return out


def search_atoms_fts(query: str, limit: int = 20) -> list[str]:
    fts_q = _fts5_safe_query(query)
    if not fts_q:
        return []
    rows = _scenario().execute(
        "SELECT atom_id FROM atoms_fts WHERE atoms_fts MATCH ? ORDER BY rank LIMIT ?",
        (fts_q, limit),
    ).fetchall()
    return [r["atom_id"] for r in rows]


_FTS5_STOP = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "and", "or", "not", "of", "in", "on", "at", "to", "for", "with", "by",
    "from", "into", "about", "as", "than", "that", "this", "these", "those",
    "it", "its", "do", "does", "did", "has", "have", "had", "what", "which",
    "who", "whom", "whose", "when", "where", "why", "how", "if", "any", "all",
    "some", "many", "much", "few", "no", "nor", "so", "yet", "but", "would",
    "could", "should", "may", "might", "can", "will", "shall",
}


def _fts5_safe_query(query: str) -> str:
    """Convert free-form text into a safe FTS5 MATCH expression.

    FTS5 treats ?, *, +, -, :, (, ), AND, OR, NOT as operators. We strip
    everything but word characters, drop common English stop words (otherwise
    AND-of-all-tokens returns 0 hits on natural-language questions), then
    OR the remaining content tokens so BM25 ranking surfaces the best chunks.
    """
    import re
    tokens = [
        t for t in re.findall(r"\w+", query.lower())
        if len(t) > 2 and t not in _FTS5_STOP
    ]
    if not tokens:
        return ""
    return " OR ".join(f'"{t}"' for t in tokens)


# ── drafts (per-scenario) ───────────────────────────────────────────────


def upsert_draft(d: DraftAtom) -> None:
    with transaction("scenario") as c:
        c.execute(
            """INSERT INTO drafts (draft_id, source_id, drafted_at, prompt_version, suggested_id, type, payload_json)
               VALUES (?,?,?,?,?,?,?)
               ON CONFLICT(draft_id) DO UPDATE SET
                 source_id=excluded.source_id, drafted_at=excluded.drafted_at,
                 prompt_version=excluded.prompt_version, suggested_id=excluded.suggested_id,
                 type=excluded.type, payload_json=excluded.payload_json""",
            (d.draft_id, d.source_id, d.drafted_at.isoformat(), d.prompt_version,
             d.suggested_id, d.type, json.dumps(d.model_dump(mode="json"))),
        )


def get_draft(draft_id: str) -> DraftAtom | None:
    r = _scenario().execute("SELECT payload_json FROM drafts WHERE draft_id=?", (draft_id,)).fetchone()
    if not r:
        return None
    return DraftAtom(**json.loads(r["payload_json"]))


def drafts_for_source(source_id: str) -> list[DraftAtom]:
    rows = _scenario().execute(
        "SELECT payload_json FROM drafts WHERE source_id=? ORDER BY drafted_at", (source_id,)
    ).fetchall()
    return [DraftAtom(**json.loads(r["payload_json"])) for r in rows]


def delete_draft(draft_id: str) -> None:
    with transaction("scenario") as c:
        c.execute("DELETE FROM drafts WHERE draft_id=?", (draft_id,))


# ── events (per-scenario) ───────────────────────────────────────────────


def log_event(e: EvalEvent) -> None:
    with transaction("scenario") as c:
        c.execute(
            "INSERT INTO events (id, timestamp, kind, actor, payload_json) VALUES (?,?,?,?,?)",
            (e.id, e.timestamp.isoformat(), e.kind, e.actor, json.dumps(e.payload, default=str)),
        )


def list_events(kind: str | None = None, limit: int = 100) -> list[EvalEvent]:
    if kind:
        rows = _scenario().execute(
            "SELECT * FROM events WHERE kind=? ORDER BY timestamp DESC LIMIT ?", (kind, limit)
        ).fetchall()
    else:
        rows = _scenario().execute(
            "SELECT * FROM events ORDER BY timestamp DESC LIMIT ?", (limit,)
        ).fetchall()
    return [
        EvalEvent(
            id=r["id"], timestamp=datetime.fromisoformat(r["timestamp"]),
            kind=r["kind"], actor=r["actor"], payload=json.loads(r["payload_json"]),
        )
        for r in rows
    ]


# ── prompts (per-scenario) ──────────────────────────────────────────────


def upsert_prompt(p: PromptVersion) -> None:
    with transaction("scenario") as c:
        c.execute(
            """INSERT INTO prompts (version, name, created_at, body, parent_version, state,
                                    accept_rate, avg_edit_distance, based_on_events_json)
               VALUES (?,?,?,?,?,?,?,?,?)
               ON CONFLICT(version) DO UPDATE SET
                 name=excluded.name, body=excluded.body, parent_version=excluded.parent_version,
                 state=excluded.state, accept_rate=excluded.accept_rate,
                 avg_edit_distance=excluded.avg_edit_distance,
                 based_on_events_json=excluded.based_on_events_json""",
            (p.version, p.name, p.created_at.isoformat(), p.body, p.parent_version, p.state,
             p.accept_rate, p.avg_edit_distance, json.dumps(p.based_on_events)),
        )


def list_prompts(name: str | None = None) -> list[PromptVersion]:
    if name:
        rows = _scenario().execute("SELECT * FROM prompts WHERE name=?", (name,)).fetchall()
    else:
        rows = _scenario().execute("SELECT * FROM prompts").fetchall()
    return [
        PromptVersion(
            name=r["name"], version=r["version"],
            created_at=datetime.fromisoformat(r["created_at"]),
            body=r["body"], parent_version=r["parent_version"], state=r["state"],
            accept_rate=r["accept_rate"], avg_edit_distance=r["avg_edit_distance"],
            based_on_events=json.loads(r["based_on_events_json"]),
        )
        for r in rows
    ]


def update_prompt_state(version: str, state: str) -> None:
    with transaction("scenario") as c:
        c.execute("UPDATE prompts SET state=? WHERE version=?", (state, version))


def archive_active_prompts(name: str) -> None:
    with transaction("scenario") as c:
        c.execute("UPDATE prompts SET state='archived' WHERE name=? AND state='active'", (name,))


# ── proposals (per-scenario) ────────────────────────────────────────────


def insert_proposal(p: Proposal) -> None:
    with transaction("scenario") as c:
        c.execute(
            """INSERT INTO proposals (id, kind, key, proposed_at, triggered_by, payload_json,
                                       state, rationale)
               VALUES (?,?,?,?,?,?,?,?)""",
            (p.id, p.kind, p.key, p.proposed_at.isoformat(), p.triggered_by,
             json.dumps(p.payload, default=str), p.state, p.rationale),
        )


def list_proposals(state: str | None = None) -> list[Proposal]:
    if state:
        rows = _scenario().execute("SELECT * FROM proposals WHERE state=?", (state,)).fetchall()
    else:
        rows = _scenario().execute("SELECT * FROM proposals").fetchall()
    return [
        Proposal(
            id=r["id"], kind=r["kind"], key=r["key"],
            proposed_at=datetime.fromisoformat(r["proposed_at"]),
            triggered_by=r["triggered_by"], payload=json.loads(r["payload_json"]),
            state=r["state"], rationale=r["rationale"],
        )
        for r in rows
    ]


def get_proposal(proposal_id: str) -> Proposal | None:
    r = _scenario().execute("SELECT * FROM proposals WHERE id=?", (proposal_id,)).fetchone()
    if not r:
        return None
    return Proposal(
        id=r["id"], kind=r["kind"], key=r["key"],
        proposed_at=datetime.fromisoformat(r["proposed_at"]),
        triggered_by=r["triggered_by"], payload=json.loads(r["payload_json"]),
        state=r["state"], rationale=r["rationale"],
    )


def update_proposal_state(proposal_id: str, state: str) -> None:
    with transaction("scenario") as c:
        c.execute("UPDATE proposals SET state=? WHERE id=?", (state, proposal_id))


# ── comparisons (per-scenario) ──────────────────────────────────────────


def insert_comparison(c_obj: ComparisonResult) -> None:
    with transaction("scenario") as c:
        c.execute(
            """INSERT INTO comparisons (id, question, paper_ids_json, pipeline, answer,
                                        citations_json, tokens_in, tokens_out, latency_ms,
                                        accuracy_vs_gold, citation_precision,
                                        n_units_retrieved, tool_call_ids_json, run_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                c_obj.id, c_obj.question, json.dumps(c_obj.paper_ids), c_obj.pipeline,
                c_obj.answer, json.dumps(c_obj.citations), c_obj.tokens_in,
                c_obj.tokens_out, c_obj.latency_ms, c_obj.accuracy_vs_gold,
                c_obj.citation_precision, c_obj.n_units_retrieved,
                json.dumps(c_obj.tool_call_ids), c_obj.run_at.isoformat(),
            ),
        )


def list_comparisons() -> list[ComparisonResult]:
    rows = _scenario().execute("SELECT * FROM comparisons ORDER BY run_at").fetchall()
    return [
        ComparisonResult(
            id=r["id"], question=r["question"], paper_ids=json.loads(r["paper_ids_json"]),
            pipeline=r["pipeline"], answer=r["answer"],
            citations=json.loads(r["citations_json"]),
            tokens_in=r["tokens_in"], tokens_out=r["tokens_out"],
            latency_ms=r["latency_ms"], accuracy_vs_gold=r["accuracy_vs_gold"],
            citation_precision=r["citation_precision"],
            n_units_retrieved=r["n_units_retrieved"],
            tool_call_ids=json.loads(r["tool_call_ids_json"]),
            run_at=datetime.fromisoformat(r["run_at"]),
        )
        for r in rows
    ]


# ── tool_calls (per-scenario) ───────────────────────────────────────────


def log_tool_call(t: ToolCall) -> None:
    with transaction("scenario") as c:
        c.execute(
            """INSERT INTO tool_calls (id, session_id, agent, tool_name, arguments_json,
                                       n_results, latency_ms, timestamp, error_message)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (t.id, t.session_id, t.agent, t.tool_name,
             json.dumps(t.arguments, default=str), t.n_results, t.latency_ms,
             t.timestamp.isoformat(),
             getattr(t, "error_message", None)),
        )


def list_tool_calls(session_id: str | None = None) -> list[ToolCall]:
    if session_id:
        rows = _scenario().execute(
            "SELECT * FROM tool_calls WHERE session_id=? ORDER BY timestamp", (session_id,)
        ).fetchall()
    else:
        rows = _scenario().execute("SELECT * FROM tool_calls ORDER BY timestamp").fetchall()
    return [
        ToolCall(
            id=r["id"], session_id=r["session_id"], agent=r["agent"],
            tool_name=r["tool_name"], arguments=json.loads(r["arguments_json"]),
            n_results=r["n_results"], latency_ms=r["latency_ms"],
            timestamp=datetime.fromisoformat(r["timestamp"]),
            error_message=(r["error_message"] if "error_message" in r.keys() else None),
        )
        for r in rows
    ]


# ── rubrics (per-scenario) — Step 4 will add real Rubric model ─────────


def log_rubric_row(row: dict[str, Any]) -> None:
    """Generic row insert; Step 4 wraps this with the typed Rubric model."""
    with transaction("scenario") as c:
        c.execute(
            """INSERT INTO rubrics (id, role, target_id, overall, criteria_json,
                                    free_text, rater, timestamp)
               VALUES (?,?,?,?,?,?,?,?)""",
            (
                row["id"], row["role"], row["target_id"], row["overall"],
                json.dumps(row.get("criteria", {})), row.get("free_text", ""),
                row.get("rater", "scholar"), row["timestamp"],
            ),
        )


def list_rubric_rows(role: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
    if role:
        rows = _scenario().execute(
            "SELECT * FROM rubrics WHERE role=? ORDER BY timestamp DESC LIMIT ?", (role, limit)
        ).fetchall()
    else:
        rows = _scenario().execute(
            "SELECT * FROM rubrics ORDER BY timestamp DESC LIMIT ?", (limit,)
        ).fetchall()
    out: list[dict[str, Any]] = []
    for r in rows:
        out.append({
            "id": r["id"], "role": r["role"], "target_id": r["target_id"],
            "overall": r["overall"], "criteria": json.loads(r["criteria_json"]),
            "free_text": r["free_text"], "rater": r["rater"], "timestamp": r["timestamp"],
        })
    return out


# ── back-compat shims ───────────────────────────────────────────────────


def db():
    """Legacy accessor — returns the active-scenario connection."""
    return _scenario()


def _ensure() -> sqlite3.Connection:
    """Legacy: scripts called this with no args expecting a connection.
    Returns the active-scenario connection."""
    return _scenario()
