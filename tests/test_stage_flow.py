from __future__ import annotations

from tetris.stage import StageCatalog, StageSession


def test_restart_restores_the_active_stage_to_its_initial_state() -> None:
    session = StageSession(StageCatalog.bootstrap())
    stage = session.activate("stage-005")

    assert session.piece_session is not None
    session.piece_session.board[5][0] = "X"
    session.piece_session.tiles[1][2] = None
    session.piece_session.objects[0][2] = None
    session.piece_session.hold_kind = "T"
    session.piece_session.hold_used = True
    session.piece_session.game_over = True

    session.restart()

    assert session.state.current_stage_id == "stage-005"
    assert session.state.status == "active"
    assert session.piece_session is not None
    assert session.piece_session.board == stage.create_board()
    assert session.piece_session.tiles == stage.create_tiles()
    assert session.piece_session.objects == stage.create_objects()
    assert session.piece_session.hold_kind is None
    assert not session.piece_session.hold_used
    assert not session.piece_session.game_over


def test_stage_session_progression_and_status_transitions() -> None:
    session = StageSession(StageCatalog.bootstrap())

    assert session.state.status == "ready"

    session.activate("stage-001")

    assert session.state.status == "active"
    assert session.piece_session is not None

    key = session.piece_session.objects[1][2]
    session.piece_session.objects[1][2] = None
    session.piece_session.objects[5][2] = key
    evaluation = session.refresh()

    assert evaluation is not None
    assert evaluation.completed
    assert session.state.status == "cleared"

    next_stage = session.activate_next()

    assert next_stage is not None
    assert next_stage.identifier == "stage-002"
    assert session.state.status == "active"

    assert session.piece_session is not None
    session.piece_session.game_over = True
    evaluation = session.refresh()

    assert evaluation is not None
    assert evaluation.failed
    assert session.state.status == "failed"

    session.reset()

    assert session.state.status == "ready"
    assert session.piece_session is None
