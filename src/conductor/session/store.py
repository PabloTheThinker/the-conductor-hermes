"""SQLite session store shared by CLI, TUI, and dashboard."""

from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from conductor.paths import state_db_path


def _utcnow() -> str:
    return datetime.now(UTC).isoformat()


@dataclass
class Message:
    role: str
    content: str
    created_at: str = field(default_factory=_utcnow)
    extras: dict[str, Any] = field(default_factory=dict)


@dataclass
class SessionRecord:
    id: str
    title: str
    source: str
    created_at: str
    updated_at: str
    messages: list[Message] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)


# Process-wide store cache — hooks must not re-init SQLite schema every call
# (benchmark finding: SessionStore() on each pre_tool was ~1ms+).
_STORE_CACHE: dict[str, "SessionStore"] = {}


def default_session_store(db_path: Path | None = None) -> "SessionStore":
    """Return a cached SessionStore for the active state DB (hook-safe)."""
    path = (db_path or state_db_path()).expanduser().resolve()
    key = str(path)
    store = _STORE_CACHE.get(key)
    if store is None:
        store = SessionStore(path)
        _STORE_CACHE[key] = store
    return store


def clear_store_cache() -> None:
    """Test helper — drop cached stores."""
    _STORE_CACHE.clear()


class SessionStore:
    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or state_db_path()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        # check_same_thread=False: Hermes may call hooks from worker threads
        conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            # Refuse to reuse a foreign schema (e.g. Hermes state.db) if mis-pointed
            row = conn.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name='sessions'"
            ).fetchone()
            if row and row[0] and "created_at" not in row[0] and "started_at" in row[0]:
                raise RuntimeError(
                    f"Conductor state DB looks like a Hermes sessions table: {self.db_path}. "
                    "Use conductor_state.db (default) or set CONDUCTOR_STATE_DB."
                )
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL DEFAULT '',
                    source TEXT NOT NULL DEFAULT 'cli',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(session_id) REFERENCES sessions(id)
                );
                CREATE TABLE IF NOT EXISTS session_meta (
                    session_id TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    PRIMARY KEY(session_id, key)
                );
                CREATE INDEX IF NOT EXISTS idx_messages_session
                    ON messages(session_id);
                """
            )
            try:
                conn.execute(
                    "ALTER TABLE messages ADD COLUMN extras TEXT NOT NULL DEFAULT '{}'"
                )
            except sqlite3.OperationalError:
                pass

    def create_session(self, *, source: str = "cli", title: str = "") -> SessionRecord:
        sid = str(uuid.uuid4())
        now = _utcnow()
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO sessions (id, title, source, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                (sid, title, source, now, now),
            )
        return SessionRecord(id=sid, title=title, source=source, created_at=now, updated_at=now)

    def _row_to_message(self, row: sqlite3.Row) -> Message:
        extras_raw = row["extras"] if "extras" in row.keys() else "{}"
        try:
            extras = json.loads(extras_raw) if extras_raw else {}
        except json.JSONDecodeError:
            extras = {}
        if not isinstance(extras, dict):
            extras = {}
        return Message(
            role=row["role"],
            content=row["content"],
            created_at=row["created_at"],
            extras=extras,
        )

    def get_session(self, session_id: str) -> SessionRecord | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
            if not row:
                return None
            msg_rows = conn.execute(
                "SELECT role, content, created_at, extras FROM messages WHERE session_id = ? ORDER BY id",
                (session_id,),
            ).fetchall()
            messages = [self._row_to_message(r) for r in msg_rows]
            meta_rows = conn.execute(
                "SELECT key, value FROM session_meta WHERE session_id = ?", (session_id,)
            ).fetchall()
            meta = {r["key"]: json.loads(r["value"]) for r in meta_rows}
            return SessionRecord(
                id=row["id"],
                title=row["title"],
                source=row["source"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                messages=messages,
                meta=meta,
            )

    def list_sessions(self, *, limit: int = 50) -> list[SessionRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id FROM sessions ORDER BY updated_at DESC LIMIT ?", (limit,)
            ).fetchall()
        out: list[SessionRecord] = []
        for row in rows:
            rec = self.get_session(row["id"])
            if rec:
                out.append(rec)
        return out

    def latest_session(self, *, source: str | None = None) -> SessionRecord | None:
        with self._connect() as conn:
            if source:
                row = conn.execute(
                    "SELECT id FROM sessions WHERE source = ? ORDER BY updated_at DESC LIMIT 1",
                    (source,),
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT id FROM sessions ORDER BY updated_at DESC LIMIT 1"
                ).fetchone()
        return self.get_session(row["id"]) if row else None

    def resolve_session(self, token: str) -> SessionRecord | None:
        rec = self.get_session(token)
        if rec:
            return rec
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id FROM sessions WHERE title = ? ORDER BY updated_at DESC LIMIT 1",
                (token,),
            ).fetchone()
        return self.get_session(row["id"]) if row else None

    def append_message(
        self,
        session_id: str,
        role: str,
        content: str,
        *,
        extras: dict[str, Any] | None = None,
    ) -> None:
        now = _utcnow()
        payload = json.dumps(extras or {})
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO messages (session_id, role, content, created_at, extras) VALUES (?, ?, ?, ?, ?)",
                (session_id, role, content, now, payload),
            )
            conn.execute("UPDATE sessions SET updated_at = ? WHERE id = ?", (now, session_id))

    def set_meta(self, session_id: str, key: str, value: Any) -> None:
        payload = json.dumps(value)
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO session_meta (session_id, key, value) VALUES (?, ?, ?)"
                " ON CONFLICT(session_id, key) DO UPDATE SET value = excluded.value",
                (session_id, key, payload),
            )

    def get_meta(self, session_id: str, key: str, default: Any = None) -> Any:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT value FROM session_meta WHERE session_id = ? AND key = ?",
                (session_id, key),
            ).fetchone()
        if not row:
            return default
        return json.loads(row["value"])

    def count_sessions(self) -> int:
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) AS c FROM sessions").fetchone()
        return int(row["c"]) if row else 0
