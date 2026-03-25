from __future__ import annotations

from importlib import import_module
from pathlib import Path
from typing import Any


SRC_PACKAGE = Path(__file__).resolve().parents[1] / "src" / "tetris"

if SRC_PACKAGE.is_dir():
    src_package_path = str(SRC_PACKAGE)
    if src_package_path not in __path__:
        __path__.append(src_package_path)

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
