"""Tetris MVP bootstrap package."""

from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = ["AppConfig", "AppShell", "TetrisApp", "create_app"]
__version__ = "0.1.0"


def __getattr__(name: str) -> Any:
    if name == "AppConfig":
        return getattr(import_module(".config", __name__), name)
    if name in {"AppShell", "TetrisApp", "create_app"}:
        return getattr(import_module(".app_shell", __name__), name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
