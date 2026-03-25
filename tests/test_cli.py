from __future__ import annotations

import tetris.app_shell as app_shell
import tetris.cli as cli


class _FakeApp:
    def __init__(self) -> None:
        self.frame_limit = "unset"
        self.shutdown_called = False

    def run(self, frame_limit: int | None = None) -> int:
        self.frame_limit = frame_limit
        return 0

    def shutdown(self) -> None:
        self.shutdown_called = True


def test_cli_defaults_to_interactive_ui_mode(monkeypatch) -> None:
    fake_app = _FakeApp()
    create_app_calls: list[bool] = []

    def fake_create_app(*, headless: bool) -> _FakeApp:
        create_app_calls.append(headless)
        return fake_app

    monkeypatch.setattr(cli, "create_app", fake_create_app)

    assert cli.main([]) == 0
    assert create_app_calls == [False]
    assert fake_app.frame_limit is None
    assert fake_app.shutdown_called


def test_cli_headless_mode_defaults_to_a_single_frame(monkeypatch) -> None:
    fake_app = _FakeApp()
    create_app_calls: list[bool] = []

    def fake_create_app(*, headless: bool) -> _FakeApp:
        create_app_calls.append(headless)
        return fake_app

    monkeypatch.setattr(cli, "create_app", fake_create_app)

    assert cli.main(["--headless"]) == 0
    assert create_app_calls == [True]
    assert fake_app.frame_limit == 1
    assert fake_app.shutdown_called


def test_create_app_uses_the_default_renderer_factory_for_ui_mode(monkeypatch) -> None:
    renderer = object()
    factory_calls: list[bool] = []

    def fake_renderer_factory(*, headless: bool) -> object:
        factory_calls.append(headless)
        return renderer

    monkeypatch.setattr(app_shell, "create_default_renderer", fake_renderer_factory)

    app = app_shell.create_app()

    assert factory_calls == [False]
    assert app.renderer is renderer
