from __future__ import annotations

from pathlib import Path

import tetris.app_shell as app_shell
import tetris.cli as cli
from tetris.app_shell import StartupFailure, StartupFailureKind
from tetris.config import RendererStrategy, RuntimeMode, StageSourceKind


class _FakeApp:
    def __init__(self, *, startup_failure: StartupFailure | None = None) -> None:
        self.frame_limit = "unset"
        self.shutdown_called = False
        self.startup_failure = startup_failure

    def run(self, frame_limit: int | None = None) -> int:
        self.frame_limit = frame_limit
        return 0

    def shutdown(self) -> None:
        self.shutdown_called = True


def test_cli_defaults_to_interactive_ui_mode(monkeypatch) -> None:
    fake_app = _FakeApp()
    create_app_calls = []

    def fake_create_app(*, config) -> _FakeApp:
        create_app_calls.append(config)
        return fake_app

    monkeypatch.setattr(cli, "create_app", fake_create_app)

    assert cli.main([]) == 0
    assert create_app_calls[0].renderer_strategy == RendererStrategy.TK
    assert fake_app.frame_limit is None
    assert fake_app.shutdown_called


def test_cli_headless_mode_defaults_to_a_single_frame(monkeypatch) -> None:
    fake_app = _FakeApp()
    create_app_calls = []

    def fake_create_app(*, config) -> _FakeApp:
        create_app_calls.append(config)
        return fake_app

    monkeypatch.setattr(cli, "create_app", fake_create_app)

    assert cli.main(["--headless"]) == 0
    assert create_app_calls[0].renderer_strategy == RendererStrategy.NULL
    assert fake_app.frame_limit == 1
    assert fake_app.shutdown_called


def test_cli_passes_explicit_bootstrap_options_into_config(monkeypatch, tmp_path: Path) -> None:
    fake_app = _FakeApp()
    create_app_calls = []
    stage_file = tmp_path / "custom.json"
    save_path = tmp_path / "save.json"

    def fake_create_app(*, config) -> _FakeApp:
        create_app_calls.append(config)
        return fake_app

    monkeypatch.setattr(cli, "create_app", fake_create_app)

    assert (
        cli.main(
            [
                "--runtime-mode",
                "installed",
                "--renderer",
                "null",
                "--stage-source",
                "file",
                "--stage-file",
                str(stage_file),
                "--save-path",
                str(save_path),
                "--frames",
                "2",
            ]
        )
        == 0
    )

    config = create_app_calls[0]
    assert config.runtime_mode == RuntimeMode.INSTALLED
    assert config.renderer_strategy == RendererStrategy.NULL
    assert config.stage_source.kind == StageSourceKind.FILE
    assert config.stage_source.path == stage_file
    assert config.save_path == save_path
    assert fake_app.frame_limit == 2


def test_cli_reports_controlled_startup_failures(monkeypatch, capsys) -> None:
    fake_app = _FakeApp(
        startup_failure=StartupFailure(
            kind=StartupFailureKind.STAGE_LOAD,
            message="Unable to load stages from test data.",
            detail="boom",
        )
    )

    def fake_create_app(*, config) -> _FakeApp:
        return fake_app

    monkeypatch.setattr(cli, "create_app", fake_create_app)

    assert cli.main(["--headless"]) == 1
    assert "Unable to load stages from test data." in capsys.readouterr().err
    assert fake_app.shutdown_called


def test_create_app_uses_renderer_strategy_from_config(monkeypatch) -> None:
    renderer = object()
    factory_calls: list[RendererStrategy] = []

    def fake_renderer_factory(strategy: RendererStrategy) -> object:
        factory_calls.append(strategy)
        return renderer

    monkeypatch.setattr(app_shell, "_create_renderer", fake_renderer_factory)

    app = app_shell.create_app()

    assert factory_calls == [RendererStrategy.TK]
    assert app.renderer is renderer
