from __future__ import annotations

import json
from pathlib import Path

from tetris import AppConfig, create_app
from tetris.actions import AppAction, ShellState


def test_malformed_save_data_falls_back_to_safe_defaults(tmp_path: Path) -> None:
    save_path = tmp_path / "save.json"
    save_path.write_text("{ malformed", encoding="utf-8")

    app = create_app(AppConfig.bootstrap(headless=True, save_path=save_path))
    app.boot()

    try:
        assert app.startup_failure is None
        assert app.stage_session is not None
        assert app.stage_session.current_stage.identifier == "stage-001"
        assert app.player_settings.show_controls is True
        assert app.game_view.stage_status == ShellState.TITLE.value
    finally:
        app.shutdown()

    payload = json.loads(save_path.read_text(encoding="utf-8"))
    assert payload["version"] == 1
    assert payload["progress"]["unlocked_stage_id"] == "stage-001"
    assert payload["progress"]["last_selected_stage_id"] == "stage-001"
    assert payload["settings"]["show_controls"] is True


def test_player_settings_changes_write_immediately_to_the_save_file(tmp_path: Path) -> None:
    save_path = tmp_path / "profile" / "save.json"
    app = create_app(AppConfig.bootstrap(headless=True, save_path=save_path))

    try:
        assert app.update_player_settings(show_controls=False)
    finally:
        app.shutdown()

    payload = json.loads(save_path.read_text(encoding="utf-8"))
    assert payload["settings"]["show_controls"] is False


def test_progress_and_settings_survive_shutdown_and_restart(tmp_path: Path) -> None:
    save_path = tmp_path / "save.json"
    first_run = create_app(AppConfig.bootstrap(headless=True, save_path=save_path))
    first_run.boot()

    try:
        assert first_run.update_player_settings(show_controls=False)
        assert first_run.handle_action(AppAction.START)
        assert first_run.handle_action(AppAction.HARD_DROP)
        assert first_run.game_view.stage_status == ShellState.CLEARED.value
    finally:
        first_run.shutdown()

    payload = json.loads(save_path.read_text(encoding="utf-8"))
    assert payload["progress"]["current_stage_id"] == "stage-001"
    assert payload["progress"]["unlocked_stage_id"] == "stage-002"
    assert payload["progress"]["last_selected_stage_id"] == "stage-002"
    assert payload["settings"]["show_controls"] is False

    second_run = create_app(AppConfig.bootstrap(headless=True, save_path=save_path))
    second_run.boot()

    try:
        assert second_run.stage_session is not None
        assert second_run.stage_session.current_stage.identifier == "stage-002"
        assert second_run.player_settings.show_controls is False
        assert second_run.game_view.status_message == "Ready to begin."
        assert second_run.handle_action(AppAction.START)
        assert second_run.game_view.stage_status == ShellState.ACTIVE.value
        assert second_run.game_view.status_message == "Stage in progress."
    finally:
        second_run.shutdown()
