from __future__ import annotations

import importlib
import json
import subprocess
import sys
from pathlib import Path

from tetris import AppConfig, create_app
from tetris.actions import AppAction, ShellState
from tetris.app_shell import StartupFailureKind
from tetris.config import RendererStrategy, RuntimeMode, StageSource, StageSourceKind


ROOT = Path(__file__).resolve().parents[1]


def test_core_modules_import() -> None:
    package = importlib.import_module("tetris")
    app_module = importlib.import_module("tetris.app")
    loop_module = importlib.import_module("tetris.game_loop")
    main_module = importlib.import_module("tetris.__main__")

    assert package.__version__ == "0.1.0"
    assert hasattr(app_module, "TetrisApp")
    assert hasattr(loop_module, "GameLoop")
    assert callable(main_module.main)


def test_headless_app_bootstrap_smoke(tmp_path: Path) -> None:
    app = create_app(AppConfig(headless=True, save_path=tmp_path / "save.json"))

    assert not app.is_booted
    app.boot()
    assert app.is_booted
    assert app.renderer.is_open
    assert app.game_view.stage_status == ShellState.TITLE.value

    frames = app.run(frame_limit=3)

    assert frames == 3
    assert app.loop.state.tick == 3
    assert app.renderer.frames_rendered == 3

    assert app.handle_action(AppAction.START)
    assert app.game_view.stage_status == ShellState.ACTIVE.value

    app.shutdown()

    assert not app.is_booted
    assert not app.renderer.is_open


def test_app_config_bootstrap_makes_startup_choices_explicit() -> None:
    config = AppConfig.bootstrap(headless=True, package_root=ROOT)

    assert config.runtime_mode == RuntimeMode.SOURCE
    assert config.stage_source.kind == StageSourceKind.FILE
    assert config.stage_source.path == ROOT / "src" / "tetris" / "stage" / "stages.json"
    assert config.save_path == ROOT / ".local" / "save.json"
    assert config.renderer_strategy == RendererStrategy.NULL


def test_app_config_bootstrap_uses_installed_defaults_outside_the_repo(tmp_path: Path) -> None:
    package_root = tmp_path / "installed-layout"
    package_root.mkdir()

    config = AppConfig.bootstrap(package_root=package_root)

    assert config.runtime_mode == RuntimeMode.INSTALLED
    assert config.stage_source.kind == StageSourceKind.BUNDLED
    assert config.save_path.name == "save.json"
    assert config.save_path.parent.name == "tetris"
    assert config.renderer_strategy == RendererStrategy.TK


def test_create_app_loads_stages_from_the_configured_stage_source(tmp_path: Path) -> None:
    stage_path = tmp_path / "custom-stages.json"
    stage_path.write_text(
        json.dumps(
            {
                "stages": [
                    {
                        "id": "custom-001",
                        "title": "Bootstrap File Stage",
                        "objective": {
                            "kind": "key_to_bottom",
                            "summary": "Bring the key to the bottom row.",
                        },
                        "board_width": 4,
                        "board_height": 4,
                        "piece_queue": ["I", "O"],
                        "board": ["....", "....", "....", "...."],
                        "tiles": ["....", "....", "....", "...."],
                        "objects": ["....", ".K..", "....", "...."],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    app = create_app(
        AppConfig.bootstrap(
            renderer_strategy=RendererStrategy.NULL,
            stage_source=StageSource.file(stage_path),
        )
    )

    app.boot()

    assert app.objective_panel.stage_title == "Bootstrap File Stage"
    assert app.handle_action(AppAction.START)
    assert app.game_view.stage_status == ShellState.ACTIVE.value

    app.shutdown()


def test_stage_loading_failures_become_controlled_app_state(tmp_path: Path) -> None:
    missing_stage_path = tmp_path / "missing-stages.json"
    app = create_app(
        AppConfig.bootstrap(
            renderer_strategy=RendererStrategy.NULL,
            stage_source=StageSource.file(missing_stage_path),
        )
    )

    assert app.startup_failure is not None
    assert app.startup_failure.kind == StartupFailureKind.STAGE_LOAD

    app.boot()

    assert app.is_booted
    assert app.game_view.stage_status == ShellState.STARTUP_ERROR.value
    assert "Unable to load stages" in app.game_view.status_message
    assert app.run(frame_limit=3) == 0

    app.shutdown()


def test_cli_main_headless_exit_code() -> None:
    main_module = importlib.import_module("tetris.cli")

    assert main_module.main(["--headless", "--frames", "2"]) == 0


def test_module_entrypoint_runs_from_repo_root() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "tetris", "--headless", "--frames", "2"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
