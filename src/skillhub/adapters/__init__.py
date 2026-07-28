"""Adapter registry — auto-discovers and manages platform adapters."""

from __future__ import annotations

import importlib
import pkgutil
from pathlib import Path
from typing import Iterator

from .base import BaseAdapter


_ADAPTERS: dict[str, type[BaseAdapter]] = {}
_LOADED = False


def _discover_adapters() -> None:
    """Dynamically discover all adapter classes in this package."""
    global _LOADED
    if _LOADED:
        return

    package_path = Path(__file__).parent
    for _, module_name, _ in pkgutil.iter_modules([str(package_path)]):
        if module_name.startswith("_") or module_name == "base":
            continue
        try:
            module = importlib.import_module(f".{module_name}", package=__name__)
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (
                    isinstance(attr, type)
                    and issubclass(attr, BaseAdapter)
                    and attr is not BaseAdapter
                    and getattr(attr, "name", "")
                ):
                    _ADAPTERS[attr.name] = attr
        except Exception:
            # Skip broken adapters silently
            continue

    _LOADED = True


def get_adapter(name: str) -> BaseAdapter | None:
    """Get an adapter instance by name, or None if not found."""
    _discover_adapters()
    cls = _ADAPTERS.get(name)
    if cls:
        return cls()
    return None


def list_adapter_classes() -> dict[str, type[BaseAdapter]]:
    """Return all discovered adapter classes."""
    _discover_adapters()
    return dict(_ADAPTERS)


def iter_adapters() -> Iterator[BaseAdapter]:
    """Iterate over instances of all discovered adapters."""
    _discover_adapters()
    for cls in _ADAPTERS.values():
        yield cls()


def detect_installed() -> list[BaseAdapter]:
    """Return list of adapters whose platforms are installed on this machine."""
    return [a for a in iter_adapters() if a.is_installed()]


__all__ = [
    "BaseAdapter",
    "get_adapter",
    "list_adapter_classes",
    "iter_adapters",
    "detect_installed",
]
