"""OpenAI Codex adapter."""

from __future__ import annotations

from pathlib import Path

from .base import BaseAdapter


class CodexAdapter(BaseAdapter):
    name = "codex"
    display_name = "OpenAI Codex"

    def __init__(self) -> None:
        self.skill_dir = Path.home() / ".codex" / "skills"
        self.mcp_config_path = Path.home() / ".codex" / "config.toml"

    def is_installed(self) -> bool:
        return (Path.home() / ".codex").exists()
