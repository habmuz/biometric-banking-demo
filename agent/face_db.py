"""
Face template database — SQLite-backed persistent store.
Stores cancelable face embeddings (ISO 24745: irreversible, unlinkable, revocable).

NOTE for production: apply a per-user random projection transform before storing
the embedding to make templates cancelable. For this demo we store raw embeddings
with a comment flagging this for production hardening.
"""
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from config import get_settings

_lock = threading.Lock()
_db_path: Path | None = None


def _get_db_path() -> Path:
    global _db_path
    if _db_path is None:
        settings = get_settings()
        path = Path(getattr(settings, 'face_db_path', 'data/face_templates.db'))
        path.parent.mkdir(parents=True, exist_ok=True)
        _db_path = path
    return _db_path


@contextmanager
def _conn():
    with _lock:
        con = sqlite3.connect(str(_get_db_path()))
        con.row_factory = sqlite3.Row
        try:
            yield con
            con.commit()
        finally:
            con.close()


def init_db() -> None:
    with _conn() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS face_templates (
                username     TEXT PRIMARY KEY,
                embedding    BLOB NOT NULL,
                registered_at TEXT NOT NULL,
                updated_at   TEXT NOT NULL
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS registered_users (
                username     TEXT PRIMARY KEY,
                registered_at TEXT NOT NULL
            )
        """)


def is_registered(username: str) -> bool:
    with _conn() as con:
        row = con.execute(
            "SELECT 1 FROM face_templates WHERE username = ?", (username,)
        ).fetchone()
        return row is not None


def store_template(username: str, embedding: np.ndarray) -> None:
    now = datetime.now(timezone.utc).isoformat()
    blob = embedding.astype(np.float32).tobytes()
    with _conn() as con:
        con.execute("""
            INSERT INTO face_templates (username, embedding, registered_at, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(username) DO UPDATE SET embedding=excluded.embedding, updated_at=excluded.updated_at
        """, (username, blob, now, now))
        con.execute("""
            INSERT OR IGNORE INTO registered_users (username, registered_at) VALUES (?, ?)
        """, (username, now))


def load_template(username: str) -> np.ndarray | None:
    with _conn() as con:
        row = con.execute(
            "SELECT embedding FROM face_templates WHERE username = ?", (username,)
        ).fetchone()
        if row is None:
            return None
        return np.frombuffer(row["embedding"], dtype=np.float32).copy()


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Dot product of L2-normed vectors = cosine similarity."""
    return float(np.dot(a / np.linalg.norm(a), b / np.linalg.norm(b)))


def delete_template(username: str) -> bool:
    """PDPA: delete on consent withdrawal."""
    with _conn() as con:
        cur = con.execute("DELETE FROM face_templates WHERE username = ?", (username,))
        con.execute("DELETE FROM registered_users WHERE username = ?", (username,))
        return cur.rowcount > 0


# Initialise on import
init_db()
