"""Base adapter class — all platform adapters inherit from this."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class SyncResult:
    skill_id: str
    platform: str
    status: str       # "synced" | "skipped" | "failed" | "removed"
    detail: str = ""
    error: str = ""


class BaseAdapter(ABC):
    """Abstract base for platform adapters."""

    name: str = ""
    display_name: str = ""

    # Subclasses should set these
    skill_dir: Optional[Path] = None       # Tier 1: SKILL.md directory
    mcp_config_path: Optional[Path] = None  # Tier 2: MCP config file

    # ---- Detection ----

    @abstractmethod
    def is_installed(self) -> bool:
        """Return True if this platform is installed on the machine."""
        ...

    # ---- Tier 1: SKILL.md skills ----

    def supports_skills(self) -> bool:
        return self.skill_dir is not None and self.skill_dir is not None

    def skill_installed(self, skill_id: str) -> bool:
        if not self.skill_dir:
            return False
        skill_path = self.skill_dir / skill_id
        return skill_path.exists() or skill_path.is_symlink()

    def install_skill(self, skill_id: str, skill_dir: Path) -> SyncResult:
        """Install a Tier 1 skill via junction/symlink.

        Override in subclasses if your platform needs a different method.
        """
        from ..utils.symlinks import create_junction, is_junction, get_junction_target

        if not self.skill_dir:
            return SyncResult(skill_id, self.name, "skipped", "No skill directory")

        target = self.skill_dir / skill_id

        # Already exists — check what it is
        if target.exists() or target.is_symlink():
            if is_junction(target):
                current_target = get_junction_target(target)
                if current_target and Path(current_target).resolve() == Path(skill_dir).resolve():
                    return SyncResult(skill_id, self.name, "skipped", "Already linked")
                else:
                    # Different target — remove and relink
                    try:
                        self.remove_skill(skill_id)
                    except Exception as e:
                        return SyncResult(skill_id, self.name, "failed", error=f"Cannot remove existing link: {e}")
            else:
                # Real directory — don't overwrite user data
                return SyncResult(skill_id, self.name, "skipped", "Real directory exists, not overwriting")

        try:
            create_junction(skill_dir, target)
            return SyncResult(skill_id, self.name, "synced", f"Junction created → {skill_dir}")
        except Exception as e:
            return SyncResult(skill_id, self.name, "failed", error=str(e))

    def remove_skill(self, skill_id: str) -> SyncResult:
        """Remove a Tier 1 skill junction."""
        from ..utils.symlinks import remove_junction, is_junction

        if not self.skill_dir:
            return SyncResult(skill_id, self.name, "skipped", "No skill directory")

        target = self.skill_dir / skill_id

        if not target.exists() and not target.is_symlink():
            return SyncResult(skill_id, self.name, "skipped", "Not installed")

        if not is_junction(target):
            return SyncResult(skill_id, self.name, "skipped", "Not a skillhub-managed link")

        try:
            remove_junction(target)
            return SyncResult(skill_id, self.name, "removed")
        except Exception as e:
            return SyncResult(skill_id, self.name, "failed", error=str(e))

    def list_skills(self) -> list[str]:
        """List all skill directories in this platform's skills folder."""
        if not self.skill_dir or not self.skill_dir.exists():
            return []
        return [p.name for p in self.skill_dir.iterdir() if p.is_dir() or p.is_symlink()]

    # ---- Tier 2: MCP servers ----

    def supports_mcp(self) -> bool:
        return self.mcp_config_path is not None

    def install_server(self, server_id: str, server_def: dict) -> SyncResult:
        return SyncResult(server_id, self.name, "skipped", "MCP not implemented for this platform")

    def remove_server(self, server_id: str) -> SyncResult:
        return SyncResult(server_id, self.name, "skipped", "MCP not implemented for this platform")

    def list_servers(self) -> list[str]:
        return []
