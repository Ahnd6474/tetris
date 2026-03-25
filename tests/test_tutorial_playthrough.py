from __future__ import annotations

from tetris import AppConfig, create_app


def test_headless_app_can_clear_the_five_tutorial_stages_in_order() -> None:
    app = create_app(AppConfig(headless=True))
    app.boot()

    try:
        for stage_id in ("stage-001", "stage-002", "stage-003", "stage-004", "stage-005"):
            assert app.stage_session.current_stage.identifier == stage_id

            _solve_active_stage(app, stage_id)

            assert app.stage_session.state.status == "cleared"

            if stage_id != "stage-005":
                assert app.advance_stage()

        assert not app.advance_stage()
        assert app.game_view.stage_status == "cleared"
        assert app.game_view.status_message == "Final stage cleared. Press R to replay."
        assert "Key on door: yes" in app.game_view.progress_lines
        assert "Ice remaining: 0" in app.game_view.progress_lines
        assert "Gems remaining: 0" in app.game_view.progress_lines
    finally:
        app.shutdown()


def test_restart_stage_resets_partial_tutorial_progress_in_the_app_shell() -> None:
    app = create_app(AppConfig(headless=True))
    app.boot()

    try:
        _solve_active_stage(app, "stage-001")
        assert app.advance_stage()
        _solve_active_stage(app, "stage-002")
        assert app.advance_stage()

        stage = app.stage_session.current_stage
        assert stage.identifier == "stage-003"

        assert app.handle_action("hold")
        assert app.handle_action("hard_drop")

        piece_session = app.stage_session.piece_session
        assert piece_session is not None
        assert piece_session.hold_kind == "O"
        assert piece_session.hold_used is False
        assert piece_session.tiles[6][1] is not None

        assert app.restart_stage()

        reset_session = app.stage_session.piece_session
        assert reset_session is not None
        assert reset_session.board == stage.create_board()
        assert reset_session.tiles == stage.create_tiles()
        assert reset_session.objects == stage.create_objects()
        assert reset_session.hold_kind is None
        assert not reset_session.hold_used
        assert app.stage_session.state.status == "active"
    finally:
        app.shutdown()


def _solve_active_stage(app, stage_id: str) -> None:
    if stage_id == "stage-001":
        assert app.handle_action("hard_drop")
        return

    if stage_id == "stage-002":
        assert app.handle_action("move_left")
        assert app.handle_action("rotate_clockwise")
        assert app.handle_action("hard_drop")
        return

    if stage_id == "stage-003":
        assert app.handle_action("hard_drop")
        assert app.stage_session.state.status == "active"
        assert app.handle_action("hard_drop")
        return

    if stage_id == "stage-004":
        assert app.handle_action("hard_drop")
        return

    if stage_id == "stage-005":
        assert app.handle_action("hard_drop")
        assert app.stage_session.state.status == "active"
        assert app.handle_action("hard_drop")
        return

    raise AssertionError(f"unexpected stage id: {stage_id}")
