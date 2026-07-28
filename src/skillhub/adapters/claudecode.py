"""Claude Code adapter."""

from __future__ import annotations

from pathlib import Path

from .base import BaseAdapter


class ClaudeCodeAdapter(BaseAdapter):
    name = "claudecode"
    display_name = "Claude Code"

    def __init__(self) -> None:
        self.skill_dir = Path.home() / ".claude" / "skills"
        self.mcp_config_path = None  # Per-project mcp.json — global TBD

    def is_installed(self) -> bool:
        return (Path.home() / ".claude").exists()
