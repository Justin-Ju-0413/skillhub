"""Utilities for parsing and writing SKILL.md frontmatter."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml


_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.DOTALL)


def parse_frontmatter(skill_md_path: Path) -> tuple[dict[str, Any], str]:
    """Parse YAML frontmatter from a SKILL.md file.

    Returns (frontmatter_dict, body_text).
    """
    text = skill_md_path.read_text(encoding="utf-8")
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return {}, text

    try:
        fm = yaml.safe_load(match.group(1)) or {}
        body = text[match.end():]
        if not isinstance(fm, dict):
            return {}, text
        return fm, body
    except yaml.YAMLError:
        return {}, text


def get_skill_name(skill_dir: Path) -> str:
    """Extract a skill's name from its SKILL.md frontmatter or directory name."""
    skill_md = skill_dir / "SKILL.md"
    if skill_md.exists():
        fm, _ = parse_frontmatter(skill_md)
        name = fm.get("name") or fm.get("display_name") or fm.get("title")
        if name:
            return str(name)
    return skill_dir.name


def get_skill_description(skill_dir: Path) -> str:
    """Extract skill description from SKILL.md frontmatter."""
    skill_md = skill_dir / "SKILL.md"
    if skill_md.exists():
        fm, _ = parse_frontmatter(skill_md)
        for key in ("description", "description_zh", "summary"):
            if fm.get(key):
                return str(fm[key])
    return ""
