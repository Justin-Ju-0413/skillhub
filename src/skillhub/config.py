"""Global configuration management."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .paths import get_config_path, ensure_dirs


@dataclass
class Config:
    enabled_platforms: list[str] = field(default_factory=list)
    registry_sources: list[str] = field(default_factory=list)
    settings: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "enabled_platforms": self.enabled_platforms,
            "registry_sources": self.registry_sources,
            "settings": self.settings,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Config":
        return cls(
            enabled_platforms=data.get("enabled_platforms", []),
            registry_sources=data.get("registry_sources", []),
            settings=data.get("settings", {}),
        )


def load_config() -> Config:
    path = get_config_path()
    if not path.exists():
        return Config()
    try:
        return Config.from_dict(json.loads(path.read_text(encoding="utf-8")))
    except (json.JSONDecodeError, OSError):
        return Config()


def save_config(config: Config) -> None:
    ensure_dirs()
    path = get_config_path()
    path.write_text(
        json.dumps(config.to_dict(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def is_platform_enabled(name: str) -> bool:
    config = load_config()
    return name in config.enabled_platforms


def enable_platform(name: str) -> None:
    config = load_config()
    if name not in config.enabled_platforms:
        config.enabled_platforms.append(name)
        save_config(config)


def disable_platform(name: str) -> None:
    config = load_config()
    if name in config.enabled_platforms:
        config.enabled_platforms.remove(name)
        save_config(config)
