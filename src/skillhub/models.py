"""Skill and server data models."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class SkillTier(str, Enum):
    SKILL = "skill"       # Tier 1: SKILL.md prompt-based
    SERVER = "server"     # Tier 2: MCP tool server


@dataclass
class PlatformCompat:
    supported: bool = True
    method: str = "symlink"   # symlink | mcpjson | toml | sqlite
    reason: str = ""


@dataclass
class SkillManifest:
    id: str
    name: str = ""
    version: str = "0.1.0"
    description: str = ""
    tier: SkillTier = SkillTier.SKILL
    category: str = "general"
    author: str = ""
    homepage: str = ""
    license: str = ""
    tags: list[str] = field(default_factory=list)
    platforms: dict[str, PlatformCompat] = field(default_factory=dict)
    dependencies: dict[str, Any] = field(default_factory=dict)
    install_info: dict[str, Any] = field(default_factory=dict)
    mcp_config: dict[str, Any] = field(default_factory=dict)  # For server tier

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "tier": self.tier.value,
            "category": self.category,
            "author": self.author,
            "homepage": self.homepage,
            "license": self.license,
            "tags": self.tags,
            "platforms": {k: v.__dict__ for k, v in self.platforms.items()},
            "dependencies": self.dependencies,
            "install": self.install_info,
            "mcp": self.mcp_config,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SkillManifest":
        platforms = {}
        for k, v in data.get("platforms", {}).items():
            if isinstance(v, dict):
                platforms[k] = PlatformCompat(
                    supported=v.get("supported", True),
                    method=v.get("method", "symlink"),
                    reason=v.get("reason", ""),
                )
            else:
                platforms[k] = PlatformCompat(supported=bool(v))

        tier = data.get("tier", "skill")
        try:
            tier_enum = SkillTier(tier)
        except ValueError:
            tier_enum = SkillTier.SKILL

        return cls(
            id=data["id"],
            name=data.get("name", data["id"]),
            version=data.get("version", "0.1.0"),
            description=data.get("description", ""),
            tier=tier_enum,
            category=data.get("category", "general"),
            author=data.get("author", ""),
            homepage=data.get("homepage", ""),
            license=data.get("license", ""),
            tags=data.get("tags", []),
            platforms=platforms,
            dependencies=data.get("dependencies", {}),
            install_info=data.get("install", {}),
            mcp_config=data.get("mcp", {}),
        )


def load_manifest(skill_dir: Path) -> SkillManifest | None:
    manifest_path = skill_dir / "skillhub.json"
    if not manifest_path.exists():
        return None
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        return SkillManifest.from_dict(data)
    except (json.JSONDecodeError, OSError, KeyError):
        return None


def save_manifest(skill_dir: Path, manifest: SkillManifest) -> None:
    skill_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = skill_dir / "skillhub.json"
    manifest_path.write_text(
        json.dumps(manifest.to_dict(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
