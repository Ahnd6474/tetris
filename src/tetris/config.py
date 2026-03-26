from __future__ import annotations

import os
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class RuntimeMode(StrEnum):
    SOURCE = "source"
    INSTALLED = "installed"


class RendererStrategy(StrEnum):
    TK = "tk"
    NULL = "null"


class StageSourceKind(StrEnum):
    BUNDLED = "bundled"
    FILE = "file"


def _package_root() -> Path:
    return Path(__file__).resolve().parents[2]


def detect_runtime_mode(package_root: Path | None = None) -> RuntimeMode:
    root = package_root or _package_root()
    if (root / "pyproject.toml").is_file() and (root / "src" / "tetris").is_dir():
        return RuntimeMode.SOURCE
    return RuntimeMode.INSTALLED


def default_stage_source(
    runtime_mode: RuntimeMode,
    *,
    package_root: Path | None = None,
) -> "StageSource":
    root = package_root or _package_root()
    if runtime_mode == RuntimeMode.SOURCE:
        return StageSource.file(root / "src" / "tetris" / "stage" / "stages.json")
    return StageSource.bundled()


def default_save_path(
    runtime_mode: RuntimeMode,
    *,
    package_root: Path | None = None,
) -> Path:
    if runtime_mode == RuntimeMode.SOURCE:
        root = package_root or _package_root()
        return root / ".local" / "save.json"

    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / "tetris" / "save.json"
    return Path.home() / ".local" / "state" / "tetris" / "save.json"


@dataclass(frozen=True, slots=True)
class StageSource:
    kind: StageSourceKind
    path: Path | None = None

    def __post_init__(self) -> None:
        if self.kind == StageSourceKind.BUNDLED:
            object.__setattr__(self, "path", None)
            return
        if self.path is None:
            raise ValueError("file stage sources must include a path")
        object.__setattr__(self, "path", Path(self.path))

    @classmethod
    def bundled(cls) -> "StageSource":
        return cls(kind=StageSourceKind.BUNDLED)

    @classmethod
    def file(cls, path: str | Path) -> "StageSource":
        return cls(kind=StageSourceKind.FILE, path=Path(path))


@dataclass(frozen=True, slots=True)
class BootstrapConfig:
    runtime_mode: RuntimeMode
    stage_source: StageSource
    save_path: Path
    renderer_strategy: RendererStrategy

    @property
    def headless(self) -> bool:
        return self.renderer_strategy == RendererStrategy.NULL


def resolve_bootstrap_config(
    *,
    runtime_mode: RuntimeMode | None = None,
    stage_source: StageSource | None = None,
    save_path: str | Path | None = None,
    renderer_strategy: RendererStrategy | None = None,
    headless: bool | None = None,
    package_root: Path | None = None,
) -> BootstrapConfig:
    resolved_runtime_mode = runtime_mode or detect_runtime_mode(package_root)
    resolved_stage_source = stage_source or default_stage_source(
        resolved_runtime_mode,
        package_root=package_root,
    )

    if renderer_strategy is not None and headless is not None:
        is_headless_strategy = renderer_strategy == RendererStrategy.NULL
        if is_headless_strategy != headless:
            raise ValueError("renderer_strategy and headless must agree")

    resolved_renderer_strategy = renderer_strategy
    if resolved_renderer_strategy is None:
        resolved_renderer_strategy = RendererStrategy.NULL if headless else RendererStrategy.TK

    resolved_save_path = (
        Path(save_path)
        if save_path is not None
        else default_save_path(resolved_runtime_mode, package_root=package_root)
    )

    return BootstrapConfig(
        runtime_mode=resolved_runtime_mode,
        stage_source=resolved_stage_source,
        save_path=resolved_save_path,
        renderer_strategy=resolved_renderer_strategy,
    )


@dataclass(frozen=True, slots=True)
class AppConfig:
    board_width: int = 10
    board_height: int = 20
    target_fps: int = 60
    startup: BootstrapConfig | None = None
    runtime_mode: RuntimeMode | None = None
    stage_source: StageSource | None = None
    save_path: Path | None = None
    renderer_strategy: RendererStrategy | None = None
    headless: bool | None = None

    @classmethod
    def bootstrap(
        cls,
        *,
        board_width: int = 10,
        board_height: int = 20,
        target_fps: int = 60,
        runtime_mode: RuntimeMode | None = None,
        stage_source: StageSource | None = None,
        save_path: str | Path | None = None,
        renderer_strategy: RendererStrategy | None = None,
        headless: bool | None = None,
        package_root: Path | None = None,
    ) -> "AppConfig":
        startup = resolve_bootstrap_config(
            runtime_mode=runtime_mode,
            stage_source=stage_source,
            save_path=save_path,
            renderer_strategy=renderer_strategy,
            headless=headless,
            package_root=package_root,
        )
        return cls(
            board_width=board_width,
            board_height=board_height,
            target_fps=target_fps,
            startup=startup,
        )

    def __post_init__(self) -> None:
        base_startup = self.startup
        startup = resolve_bootstrap_config(
            runtime_mode=(
                self.runtime_mode
                if self.runtime_mode is not None
                else (base_startup.runtime_mode if base_startup is not None else None)
            ),
            stage_source=(
                self.stage_source
                if self.stage_source is not None
                else (base_startup.stage_source if base_startup is not None else None)
            ),
            save_path=(
                self.save_path
                if self.save_path is not None
                else (base_startup.save_path if base_startup is not None else None)
            ),
            renderer_strategy=(
                self.renderer_strategy
                if self.renderer_strategy is not None
                else (
                    base_startup.renderer_strategy
                    if base_startup is not None and self.headless is None
                    else None
                )
            ),
            headless=self.headless,
        )

        object.__setattr__(self, "startup", startup)
        object.__setattr__(self, "runtime_mode", startup.runtime_mode)
        object.__setattr__(self, "stage_source", startup.stage_source)
        object.__setattr__(self, "save_path", startup.save_path)
        object.__setattr__(self, "renderer_strategy", startup.renderer_strategy)
        object.__setattr__(self, "headless", startup.headless)
