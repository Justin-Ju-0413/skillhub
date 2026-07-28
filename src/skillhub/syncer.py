"""Sync orchestrator — syncs skills/servers across all enabled platforms."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from . import registry
from .adapters import get_adapter, detect_installed
from .adapters.base import BaseAdapter, SyncResult
from .config import load_config
from .models import SkillTier
from .paths import get_skills_dir, get_servers_dir


@dataclass
class SyncReport:
    results: list[SyncResult]

    @property
    def synced(self) -> int:
        return sum(1 for r in self.results if r.status == "synced")

    @property
    def skipped(self) -> int:
        return sum(1 for r in self.results if r.status == "skipped")

    @property
    def failed(self) -> int:
        return sum(1 for r in self.results if r.status == "failed")

    @property
    def removed(self) -> int:
        return sum(1 for r in self.results if r.status == "removed")


def get_enabled_platforms() -> list[BaseAdapter]:
    """Get list of enabled platform adapter instances."""
    config = load_config()
    adapters: list[BaseAdapter] = []
    for name in config.enabled_platforms:
        adapter = get_adapter(name)
        if adapter and adapter.is_installed():
            adapters.append(adapter)
    return adapters


def sync_skills(
    platform_filter: str | None = None,
    skill_filter: str | None = None,
    dry_run: bool = False,
) -> SyncReport:
    """Sync all Tier 1 skills to enabled platforms.

    Args:
        platform_filter: Only sync to this platform (optional)
        skill_filter: Only sync this skill (optional)
        dry_run: If True, don't actually make changes
    """
    platforms = get_enabled_platforms()
    if platform_filter:
        platforms = [p for p in platforms if p.name == platform_filter]

    skills = registry.list_skills(tier=SkillTier.SKILL.value)
    if skill_filter:
        skills = [s for s in skills if s["id"] == skill_filter]

    results: list[SyncResult] = []
    skills_dir = get_skills_dir()

    for skill in skills:
        skill_dir = skills_dir / skill["id"]
        if not skill_dir.exists():
            continue

        for platform in platforms:
            if not platform.supports_skills():
                continue

            if dry_run:
                if platform.skill_installed(skill["id"]):
                    results.append(SyncResult(skill["id"], platform.name, "skipped", "Already present"))
                else:
                    results.append(SyncResult(skill["id"], platform.name, "synced", "[dry-run] Would create junction"))
            else:
                result = platform.install_skill(skill["id"], skill_dir)
                registry.set_sync_state(skill["id"], platform.name, result.status, result.error)
                results.append(result)

    return SyncReport(results)


def remove_skill_from_platform(skill_id: str, platform_name: str) -> SyncResult | None:
    """Remove a single skill from a specific platform."""
    adapter = get_adapter(platform_name)
    if not adapter:
        return None
    result = adapter.remove_skill(skill_id)
    registry.set_sync_state(skill_id, platform_name, result.status, result.error)
    return result


def remove_skill_everywhere(skill_id: str) -> SyncReport:
    """Remove a skill from all enabled platforms."""
    platforms = get_enabled_platforms()
    results: list[SyncResult] = []
    for platform in platforms:
        if not platform.supports_skills():
            continue
        result = platform.remove_skill(skill_id)
        registry.set_sync_state(skill_id, platform.name, result.status, result.error)
        results.append(result)
    return SyncReport(results)


def doctor(fix: bool = False) -> list[dict]:
    """Check health of all synced skills.

    Returns list of issues found. If fix=True, attempts to repair.
    """
    from .utils.symlinks import is_junction, get_junction_target

    platforms = get_enabled_platforms()
    skills = registry.list_skills(tier=SkillTier.SKILL.value)
    skills_dir = get_skills_dir()
    issues: list[dict] = []

    for skill in skills:
        canonical = skills_dir / skill["id"]
        if not canonical.exists():
            issues.append({
                "skill": skill["id"],
                "platform": "skillhub",
                "type": "missing_canonical",
                "detail": f"Canonical skill directory missing: {canonical}",
            })
            continue

        for platform in platforms:
            if not platform.skill_dir:
                continue

            target = platform.skill_dir / skill["id"]
            state = registry.get_sync_state(skill["id"], platform.name)
            expected_status = state["status"] if state else "unknown"

            # Check if it should be synced but isn't
            if expected_status in ("synced",) and not (target.exists() or target.is_symlink()):
                issue = {
                    "skill": skill["id"],
                    "platform": platform.name,
                    "type": "missing_link",
                    "detail": f"Expected junction not found: {target}",
                }
                if fix:
                    result = platform.install_skill(skill["id"], canonical)
                    issue["fixed"] = result.status == "synced"
                    issue["fix_detail"] = result.detail
                issues.append(issue)
                continue

            # Check if it's a real directory instead of a junction (manual install)
            if target.exists() and not is_junction(target) and not target.is_symlink():
                issues.append({
                    "skill": skill["id"],
                    "platform": platform.name,
                    "type": "real_directory",
                    "detail": f"Real directory (not a skillhub junction): {target}",
                })
                continue

            # Check if junction points to the right place
            if is_junction(target):
                actual_target = get_junction_target(target)
                if actual_target and Path(actual_target).resolve() != canonical.resolve():
                    issue = {
                        "skill": skill["id"],
                        "platform": platform.name,
                        "type": "wrong_target",
                        "detail": f"Junction points to {actual_target}, expected {canonical}",
                    }
                    if fix:
                        try:
                            platform.remove_skill(skill["id"])
                            result = platform.install_skill(skill["id"], canonical)
                            issue["fixed"] = result.status == "synced"
                        except Exception as e:
                            issue["fixed"] = False
                            issue["fix_detail"] = str(e)
                    issues.append(issue)

    return issues
