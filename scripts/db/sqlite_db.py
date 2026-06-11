import logging
import sqlite3
from pathlib import Path

logger = logging.getLogger(__name__)

_db_path: Path | None = None

SCHEMA_VERSION = 1

_DDL = """
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY
);
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now'))
);
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL REFERENCES sessions(id),
    role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now'))
);
"""

_current_session_id: int | None = None


def init_db(db_dir: "str | Path"):
    global _db_path, _current_session_id
    _db_path = Path(db_dir) / "shikhbo.db"
    _migrate()
    _current_session_id = _new_session()
    logger.info(f"SQLite DB ready at {_db_path}, session={_current_session_id}")


def _connect() -> sqlite3.Connection:
    if not _db_path:
        raise RuntimeError("DB not initialized — call init_db() first")
    conn = sqlite3.connect(str(_db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _migrate():
    try:
        conn = _connect()
        conn.executescript(_DDL)
        row = conn.execute("SELECT version FROM schema_version").fetchone()
        if row is None:
            conn.execute("INSERT INTO schema_version(version) VALUES(?)", (SCHEMA_VERSION,))
        conn.commit()
        conn.close()
    except sqlite3.DatabaseError as e:
        logger.error(f"DB migration failed ({e}), recreating...")
        if _db_path and _db_path.exists():
            _db_path.rename(_db_path.with_suffix(".db.bak"))
        conn = _connect()
        conn.executescript(_DDL)
        conn.execute("INSERT INTO schema_version(version) VALUES(?)", (SCHEMA_VERSION,))
        conn.commit()
        conn.close()


def _new_session() -> int:
    conn = _connect()
    cur = conn.execute("INSERT INTO sessions DEFAULT VALUES")
    conn.commit()
    sid = cur.lastrowid
    conn.close()
    return sid


def save_turn(user_text: str, assistant_text: str):
    global _current_session_id
    if _db_path is None:
        return
    if _current_session_id is None:
        _current_session_id = _new_session()
    try:
        conn = _connect()
        conn.execute(
            "INSERT INTO messages(session_id, role, content) VALUES(?,?,?)",
            (_current_session_id, "user", user_text),
        )
        conn.execute(
            "INSERT INTO messages(session_id, role, content) VALUES(?,?,?)",
            (_current_session_id, "assistant", assistant_text),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"save_turn failed: {e}")


def get_recent_messages(limit: int = 50) -> list[dict]:
    if _db_path is None or not _db_path.exists():
        return []
    try:
        conn = _connect()
        rows = conn.execute(
            """
            SELECT role, content, created_at
            FROM messages
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        conn.close()
        return [dict(r) for r in reversed(rows)]
    except Exception as e:
        logger.error(f"get_recent_messages failed: {e}")
        return []
