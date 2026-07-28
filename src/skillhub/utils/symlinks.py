"""Windows junction / symlink helpers."""

from __future__ import annotations

import ctypes
import os
import subprocess
import sys
from pathlib import Path


def is_windows() -> bool:
    return sys.platform == "win32"


def create_junction(target: Path, link: Path) -> None:
    """Create a Windows directory junction (link -> target)."""
    target = Path(target).resolve()
    link = Path(link)

    if link.exists() or link.is_symlink():
        raise FileExistsError(f"Link already exists: {link}")

    if not target.is_dir():
        raise NotADirectoryError(f"Target is not a directory: {target}")

    link.parent.mkdir(parents=True, exist_ok=True)

    if is_windows():
        # Use mklink /J via cmd — works without admin for junctions
        result = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(link), str(target)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise OSError(f"Failed to create junction: {result.stderr.strip()}")
    else:
        # Unix fallback
        link.symlink_to(target, target_is_directory=True)


def remove_junction(link: Path) -> None:
    """Remove a junction/symlink directory."""
    link = Path(link)
    if not link.exists() and not link.is_symlink():
        return

    if is_windows():
        if is_junction(link):
            # rmdir works for junctions without deleting contents
            result = subprocess.run(
                ["cmd", "/c", "rmdir", str(link)],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                raise OSError(f"Failed to remove junction: {result.stderr.strip()}")
        else:
            # Real directory — be safe, use rmdir (only works if empty)
            link.rmdir()
    else:
        link.unlink()


def is_junction(path: Path) -> bool:
    """Check if a path is a Windows junction or symlink."""
    path = Path(path)
    if not path.exists() and not path.is_symlink():
        return False

    if path.is_symlink():
        return True

    if is_windows():
        # Check for junction reparse point
        try:
            FILE_ATTRIBUTE_REPARSE_POINT = 0x0400
            attrs = ctypes.windll.kernel32.GetFileAttributesW(str(path))
            if attrs == -1:
                return False
            return bool(attrs & FILE_ATTRIBUTE_REPARSE_POINT)
        except Exception:
            return False

    return False


def get_junction_target(path: Path) -> Path | None:
    """Get the target of a junction/symlink."""
    path = Path(path)
    if not is_junction(path):
        return None

    if is_windows():
        try:
            # Use PowerShell for reliable target resolution
            result = subprocess.run(
                ["powershell", "-Command", f"(Get-Item '{path}').Target"],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0 and result.stdout.strip():
                return Path(result.stdout.strip())
        except Exception:
            pass
        return None
    else:
        return Path(os.readlink(str(path)))


def junction_exists(path: Path) -> bool:
    """Check if a junction/symlink exists (even if broken)."""
    path = Path(path)
    return path.is_symlink() or (is_windows() and is_junction(path))
