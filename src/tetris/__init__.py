"""Tetris MVP bootstrap package."""

from .app import TetrisApp, create_app
from .config import AppConfig

__all__ = ["AppConfig", "TetrisApp", "create_app"]
__version__ = "0.1.0"
