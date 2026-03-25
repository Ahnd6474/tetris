from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from tetris import AppConfig
from tetris.app_shell import AppShell
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


def test_app_shell_wires_runtime_stage_and_compatibility_exports() -> None:
    app = AppShell(config=AppConfig(headless=True), renderer=NullRenderer())

    assert app.loop.runtime is app.engine
    assert app.objective_panel.stage_title == "Bootstrap Stage"
    assert app.objective_panel.stage_status == "ready"
    assert CompatLoop is EngineLoop
    assert GameState is EngineState

    app.boot()

    assert app.stage_session.state.status == "active"
    assert app.objective_panel.stage_status == "active"

    app.shutdown()

    assert app.objective_panel.stage_status == "ready"
