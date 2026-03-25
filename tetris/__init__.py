from __future__ import annotations

from pathlib import Path


SRC_PACKAGE = Path(__file__).resolve().parents[1] / "src" / "tetris"

if SRC_PACKAGE.is_dir():
    src_package_path = str(SRC_PACKAGE)
    if src_package_path not in __path__:
        __path__.append(src_package_path)

from .app import TetrisApp, create_app
from .config import AppConfig

__all__ = ["AppConfig", "TetrisApp", "create_app"]
__version__ = "0.1.0"
