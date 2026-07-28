"""Skill installation and import logic."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from . import registry
from .adapters import detect_installed
from .config import enable_platform, load_config, save_config
from .models import SkillManifest, SkillTier, PlatformCompat
from .paths import get_skills_dir, ensure_dirs
from .utils.frontmatter import get_skill_name, get_skill_description


def _generate_manifest(
    skill_id: str,
    skill_dir: Path,
    source: str,
    source_path: str | None = None,
) -> SkillManifest:
    """Generate a skillhub.json manifest by inspecting a skill directory."""
    name = get_skill_name(skill_dir) or skill_id
    description = get_skill_description(skill_dir)

    # Detect platforms compatibility — start with the source platform
    platforms: dict[str, PlatformCompat] = {}
    if source == "workbuddy":
        platforms["workbuddy"] = PlatformCompat(supported=True, method="symlink")
        platforms["claudecode"] = PlatformCompat(supported=True, method="symlink")
        platforms["codex"] = PlatformCompat(supported=True, method="symlink")
    elif source == "claudecode":
        platforms["claudecode"] = PlatformCompat(supported=True, method="symlink")
        platforms["workbuddy"] = PlatformCompat(supported=True, method="symlink")
        platforms["codex"] = PlatformCompat(supported=True, method="symlink")
    elif source == "codex":
        platforms["codex"] = PlatformCompat(supported=True, method="symlink")
        platforms["claudecode"] = PlatformCompat(supported=True, method="symlink")
        platforms["workbuddy"] = PlatformCompat(supported=True, method="symlink")

    return SkillManifest(
        id=skill_id,
        name=name,
        description=description,
        tier=SkillTier.SKILL,
        platforms=platforms,
        install_info={
            "source": source,
            "original_path": source_path or str(skill_dir),
        },
    )


def import_from_directory(
    source_platform: str,
    source_dir: Path,
    overwrite: bool = False,
) -> list[str]:
    """Import all skills from a platform's skills directory into the registry.

    Returns list of imported skill IDs.
    """
    if not source_dir.exists():
        raise FileNotFoundError(f"Source directory not found: {source_dir}")

    ensure_dirs()
    skills_dir = get_skills_dir()
    imported: list[str] = []

    for entry in sorted(source_dir.iterdir()):
        # Skip hidden files, files, meta files
        if entry.name.startswith("_") or entry.name.startswith("."):
            continue
        if not entry.is_dir() and not entry.is_symlink():
            continue

        skill_id = entry.name
        dest = skills_dir / skill_id

        # Check if already in registry
        if registry.get_skill(skill_id):
            if not overwrite:
                continue
            # Remove old canonical copy
            if dest.exists():
                shutil.rmtree(dest)

        # Copy skill contents to canonical location
        try:
            # Resolve symlinks before copying
            real_path = entry.resolve() if entry.is_symlink() else entry
            if not real_path.is_dir():
                continue

            shutil.copytree(real_path, dest, symlinks=True, dirs_exist_ok=overwrite)

            # Generate and save manifest
            manifest = _generate_manifest(skill_id, dest, source_platform, str(entry))
            from .models import save_manifest
            save_manifest(dest, manifest)

            # Register in database
            registry.add_skill(
                skill_id=skill_id,
                name=manifest.name,
                version=manifest.version,
                tier=manifest.tier.value,
                description=manifest.description,
                category=manifest.category,
            )

            imported.append(skill_id)
        except Exception as e:
            print(f"  ! Failed to import {skill_id}: {e}")
            continue

    registry.log_operation(
        "import",
        f"Imported {len(imported)} skills from {source_platform}",
    )
    return imported


def init_skillhub() -> dict[str, Any]:
    """Initialize skillhub: detect platforms, import skills, run initial sync.

    Returns summary dict with detected platforms and import counts.
    """
    from .registry import init_db, upsert_platform, log_operation
    from .adapters import detect_installed as detect_adapters

    # Initialize database
    init_db()
    ensure_dirs()

    # Detect platforms
    installed = detect_adapters()
    detected_names: list[str] = []

    for adapter in installed:
        upsert_platform(
            name=adapter.name,
            display_name=adapter.display_name,
            detected=True,
            enabled=True,  # Enable all detected platforms by default
            skill_dir=str(adapter.skill_dir) if adapter.skill_dir else None,
            mcp_config_path=str(adapter.mcp_config_path) if adapter.mcp_config_path else None,
        )
        enable_platform(adapter.name)
        detected_names.append(adapter.name)

    # Import from the richest source first (WorkBuddy has the most skills)
    import_counts: dict[str, int] = {}
    for source_name in ["workbuddy", "claudecode", "codex"]:
        adapter = next((a for a in installed if a.name == source_name), None)
        if not adapter or not adapter.skill_dir:
            continue

        # Skip if we already imported the skills from another source
        # (they share the same IDs, so subsequent imports will be no-ops due to overwrite=False)
        count = len(import_from_directory(source_name, adapter.skill_dir, overwrite=False))
        import_counts[source_name] = count

    log_operation("init", f"Detected {len(installed)} platforms, imported skills from {list(import_counts.keys())}")

    return {
        "platforms_detected": detected_names,
        "import_counts": import_counts,
    }
