"""SQLite registry for tracking installed skills and sync state."""

from __future__ import annotations

import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Optional

from .paths import get_registry_path, ensure_dirs


SCHEMA = """
CREATE TABLE IF NOT EXISTS skills (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    version TEXT NOT NULL,
    tier TEXT NOT NULL,
    description TEXT,
    category TEXT,
    installed_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS sync_state (
    skill_id TEXT NOT NULL,
    platform TEXT NOT NULL,
    status TEXT NOT NULL,
    synced_at REAL,
    error TEXT,
    PRIMARY KEY (skill_id, platform),
    FOREIGN KEY (skill_id) REFERENCES skills(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS platforms (
    name TEXT PRIMARY KEY,
    display_name TEXT,
    detected INTEGER NOT NULL DEFAULT 0,
    enabled INTEGER NOT NULL DEFAULT 0,
    skill_dir TEXT,
    mcp_config_path TEXT
);

CREATE TABLE IF NOT EXISTS operations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp REAL NOT NULL,
    operation TEXT NOT NULL,
    details TEXT
);
"""


@contextmanager
def get_db() -> Iterator[sqlite3.Connection]:
    ensure_dirs()
    db_path = get_registry_path()
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    """Initialize the database schema."""
    with get_db() as conn:
        conn.executescript(SCHEMA)


# ---- Skills CRUD ----

def add_skill(
    skill_id: str,
    name: str,
    version: str,
    tier: str,
    description: str = "",
    category: str = "general",
) -> None:
    now = time.time()
    with get_db() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO skills (id, name, version, tier, description, category, installed_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (skill_id, name, version, tier, description, category, now),
        )


def remove_skill(skill_id: str) -> None:
    with get_db() as conn:
        conn.execute("DELETE FROM skills WHERE id = ?", (skill_id,))


def get_skill(skill_id: str) -> Optional[dict]:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM skills WHERE id = ?", (skill_id,)).fetchone()
        return dict(row) if row else None


def list_skills(tier: str | None = None) -> list[dict]:
    with get_db() as conn:
        if tier:
            rows = conn.execute("SELECT * FROM skills WHERE tier = ? ORDER BY id", (tier,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM skills ORDER BY id").fetchall()
        return [dict(r) for r in rows]


# ---- Sync State CRUD ----

def set_sync_state(skill_id: str, platform: str, status: str, error: str = "") -> None:
    now = time.time()
    with get_db() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO sync_state (skill_id, platform, status, synced_at, error)
               VALUES (?, ?, ?, ?, ?)""",
            (skill_id, platform, status, now, error),
        )


def get_sync_state(skill_id: str, platform: str) -> Optional[dict]:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM sync_state WHERE skill_id = ? AND platform = ?",
            (skill_id, platform),
        ).fetchone()
        return dict(row) if row else None


def list_sync_state(platform: str | None = None) -> list[dict]:
    with get_db() as conn:
        if platform:
            rows = conn.execute(
                "SELECT * FROM sync_state WHERE platform = ? ORDER BY skill_id",
                (platform,),
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM sync_state ORDER BY skill_id, platform").fetchall()
        return [dict(r) for r in rows]


# ---- Platforms CRUD ----

def upsert_platform(
    name: str,
    display_name: str = "",
    detected: bool = False,
    enabled: bool = False,
    skill_dir: str | None = None,
    mcp_config_path: str | None = None,
) -> None:
    with get_db() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO platforms (name, display_name, detected, enabled, skill_dir, mcp_config_path)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (name, display_name or name, int(detected), int(enabled), skill_dir, mcp_config_path),
        )


def get_platform(name: str) -> Optional[dict]:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM platforms WHERE name = ?", (name,)).fetchone()
        if row:
            d = dict(row)
            d["detected"] = bool(d["detected"])
            d["enabled"] = bool(d["enabled"])
            return d
        return None


def list_platforms() -> list[dict]:
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM platforms ORDER BY name").fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["detected"] = bool(d["detected"])
            d["enabled"] = bool(d["enabled"])
            result.append(d)
        return result


def set_platform_enabled(name: str, enabled: bool) -> None:
    with get_db() as conn:
        conn.execute(
            "UPDATE platforms SET enabled = ? WHERE name = ?",
            (int(enabled), name),
        )


# ---- Operations log ----

def log_operation(operation: str, details: str = "") -> None:
    now = time.time()
    with get_db() as conn:
        conn.execute(
            "INSERT INTO operations (timestamp, operation, details) VALUES (?, ?, ?)",
            (now, operation, details),
        )
