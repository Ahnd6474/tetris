from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from tetris import AppConfig
from tetris.actions import AppAction, ShellState
from tetris.app_shell import AppShell, StartupFailureKind
from tetris.config import StageSource
from tetris.engine import EngineState, GameLoop as EngineLoop
from tetris.game_loop import GameLoop as CompatLoop
from tetris.state import GameState
from tetris.ui import NullRenderer


ROOT = Path(__file__).resolve().parents[1]


def test_engine_and_stage_boundaries_stay_headless_in_clean_process() -> None:
    script = """
import json
import sys

import tetris.engine
import tetris.stage
from tetris.config import AppConfig
from tetris.engine import EngineRuntime
from tetris.stage import StageCatalog, StageSession

runtime = EngineRuntime.from_config(AppConfig(headless=True))
session = StageSession(StageCatalog.bootstrap())

print(json.dumps({
    "ui_renderers_loaded": "tetris.ui.renderers" in sys.modules,
    "board": [runtime.board.width, runtime.board.height],
    "stage": session.current_stage.identifier,
    "status": session.state.status,
}))
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["board"] == [10, 20]
    assert payload["stage"] == "stage-001"
    assert payload["status"] == "ready"
    assert not payload["ui_renderers_loaded"]


def test_app_shell_wires_runtime_stage_and_compatibility_exports(tmp_path: Path) -> None:
    app = AppShell(
        config=AppConfig(headless=True, save_path=tmp_path / "save.json"),
        renderer=NullRenderer(),
    )

    assert app.loop.runtime is app.engine
    assert app.stage_session is not None
    assert app.objective_panel.stage_title == "Key Delivery"
    assert app.objective_panel.stage_status == ShellState.TITLE.value
    assert CompatLoop is EngineLoop
    assert GameState is EngineState

    app.boot()

    assert app.stage_session.state.status == "ready"
    assert app.game_view.stage_status == ShellState.TITLE.value
    assert app.handle_action(AppAction.START)
    assert app.stage_session.state.status == "active"
    assert app.objective_panel.stage_status == ShellState.ACTIVE.value

    app.shutdown()

    assert app.objective_panel.stage_status == ShellState.TITLE.value


class _ExplodingRenderer:
    def __init__(self, error: Exception) -> None:
        self.error = error
        self.bound = None
        self.is_open = False

    def bind(self, controller) -> None:
        self.bound = controller

    def open(self) -> None:
        raise self.error

    def render(self, state: EngineState) -> None:
        return None

    def close(self) -> None:
        self.is_open = False


class TclError(RuntimeError):
    pass


def test_boot_converts_missing_tkinter_into_controlled_startup_failure(tmp_path: Path) -> None:
    error = ModuleNotFoundError("No module named 'tkinter'")
    error.name = "tkinter"
    app = AppShell(
        config=AppConfig.bootstrap(save_path=tmp_path / "save.json"),
        renderer=_ExplodingRenderer(error),
    )

    app.boot()

    assert app.startup_failure is not None
    assert app.startup_failure.kind == StartupFailureKind.TKINTER_UNAVAILABLE
    assert isinstance(app.renderer, NullRenderer)
    assert app.loop.renderer is app.renderer
    assert app.game_view.stage_status == ShellState.STARTUP_ERROR.value
    assert app.run(frame_limit=3) == 0

    app.shutdown()


def test_boot_converts_display_creation_failure_into_controlled_startup_failure(tmp_path: Path) -> None:
    app = AppShell(
        config=AppConfig.bootstrap(save_path=tmp_path / "save.json"),
        renderer=_ExplodingRenderer(TclError("no display name and no $DISPLAY environment variable")),
    )

    app.boot()

    assert app.startup_failure is not None
    assert app.startup_failure.kind == StartupFailureKind.DISPLAY_UNAVAILABLE
    assert isinstance(app.renderer, NullRenderer)
    assert app.loop.renderer is app.renderer
    assert app.game_view.stage_status == ShellState.STARTUP_ERROR.value

    app.shutdown()


def test_app_runtime_and_view_follow_restored_stage_dimensions(tmp_path: Path) -> None:
    stage_path = tmp_path / "custom-stages.json"
    save_path = tmp_path / "save.json"
    stage_path.write_text(
        json.dumps(
            {
                "stages": [
                    {
                        "id": "stage-001",
                        "title": "Small Stage",
                        "objective": {
                            "kind": "key_to_bottom",
                            "summary": "Bring the key to the bottom row.",
                        },
                        "board_width": 4,
                        "board_height": 4,
                        "board": ["....", "....", "....", "...."],
                        "tiles": ["....", "....", "....", "...."],
                        "objects": ["....", ".K..", "....", "...."],
                    },
                    {
                        "id": "stage-002",
                        "title": "Wide Stage",
                        "objective": {
                            "kind": "key_to_bottom",
                            "summary": "Bring the key to the bottom row.",
                        },
                        "board_width": 6,
                        "board_height": 5,
                        "board": ["......", "......", "......", "......", "......"],
                        "tiles": ["......", "......", "......", "......", "......"],
                        "objects": ["......", "..K...", "......", "......", "......"],
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    save_path.write_text(
        json.dumps(
            {
                "version": 1,
                "progress": {
                    "unlocked_stage_id": "stage-002",
                    "current_stage_id": "stage-002",
                    "last_selected_stage_id": "stage-002",
                },
                "settings": {
                    "show_controls": True,
                },
            }
        ),
        encoding="utf-8",
    )

    app = AppShell(
        config=AppConfig.bootstrap(
            headless=True,
            stage_source=StageSource.file(stage_path),
            save_path=save_path,
        ),
        renderer=NullRenderer(),
    )

    try:
        app.boot()

        assert app.stage_session is not None
        assert app.stage_session.current_stage.identifier == "stage-002"
        assert app.engine.board.width == 6
        assert app.engine.board.height == 5
        assert app.game_view.board_width == 6
        assert app.game_view.board_height == 5
        assert app.objective_panel.stage_title == "Wide Stage"
    finally:
        app.shutdown()
