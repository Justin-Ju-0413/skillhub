"""Path helpers for skillhub."""

from __future__ import annotations

import os
from pathlib import Path


def get_skillhub_dir() -> Path:
    """Return the root skillhub data directory."""
    base = os.environ.get("SKILLHUB_HOME")
    if base:
        return Path(base).expanduser().resolve()
    return Path.home() / ".skillhub"


def get_skills_dir() -> Path:
    return get_skillhub_dir() / "skills"


def get_servers_dir() -> Path:
    return get_skillhub_dir() / "servers"


def get_config_path() -> Path:
    return get_skillhub_dir() / "config.json"


def get_registry_path() -> Path:
    return get_skillhub_dir() / "registry.db"


def get_logs_dir() -> Path:
    return get_skillhub_dir() / "logs"


def ensure_dirs() -> None:
    """Create all required directories if they don't exist."""
    for d in [get_skillhub_dir(), get_skills_dir(), get_servers_dir(), get_logs_dir()]:
        d.mkdir(parents=True, exist_ok=True)
