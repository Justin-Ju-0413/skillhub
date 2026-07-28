"""WorkBuddy adapter."""

from __future__ import annotations

from pathlib import Path

from .base import BaseAdapter


class WorkBuddyAdapter(BaseAdapter):
    name = "workbuddy"
    display_name = "WorkBuddy"

    def __init__(self) -> None:
        self.skill_dir = Path.home() / ".workbuddy" / "skills"
        self.mcp_config_path = Path.home() / ".workbuddy" / ".mcp.json"

    def is_installed(self) -> bool:
        return (Path.home() / ".workbuddy").exists()
