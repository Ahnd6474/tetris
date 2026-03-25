from __future__ import annotations

import importlib

from tetris import AppConfig, create_app


def test_core_modules_import() -> None:
    package = importlib.import_module("tetris")
    app_module = importlib.import_module("tetris.app")
    loop_module = importlib.import_module("tetris.game_loop")
    main_module = importlib.import_module("tetris.__main__")

    assert package.__version__ == "0.1.0"
    assert hasattr(app_module, "TetrisApp")
    assert hasattr(loop_module, "GameLoop")
    assert callable(main_module.main)


def test_headless_app_bootstrap_smoke() -> None:
    app = create_app(AppConfig(headless=True))

    assert not app.is_booted
    app.boot()
    assert app.is_booted
    assert app.renderer.is_open

    frames = app.run(frame_limit=3)

    assert frames == 3
    assert app.loop.state.tick == 3
    assert app.renderer.frames_rendered == 3

    app.shutdown()

    assert not app.is_booted
    assert not app.renderer.is_open


def test_cli_main_headless_exit_code() -> None:
    main_module = importlib.import_module("tetris.cli")

    assert main_module.main(["--headless", "--frames", "2"]) == 0
