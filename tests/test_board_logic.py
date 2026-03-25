from __future__ import annotations

from tetris.engine import ActivePiece, PieceBag, PieceSession


def test_lock_active_clears_rows_and_compacts_stage_layers() -> None:
    snapshots = []
    session = PieceSession(
        width=4,
        height=4,
        bag=PieceBag(initial_queue=("I", "O")),
        board=[
            [None, None, None, None],
            [None, None, None, None],
            ["X", "X", None, "X"],
            ["X", "X", None, "X"],
        ],
        tiles=[
            [None, None, None, None],
            [None, "ice", None, None],
            ["rock", None, None, None],
            [None, None, "ice", None],
        ],
        objects=[
            [None, None, "gem", None],
            ["key", None, None, None],
            [None, None, None, None],
            [None, "door", None, None],
        ],
        on_lines_cleared=lambda _session, cleared: snapshots.extend(cleared),
    )
    session.active = ActivePiece("I", rotation=1, x=0, y=0)
    session.hold_used = True

    result = session.lock_active()

    assert result.kind == "I"
    assert result.landing_row == 3
    assert result.cleared_rows == (2, 3)
    assert result.lines_cleared == 2
    assert not result.top_out
    assert not result.game_over
    assert session.last_lock_result == result
    assert not session.hold_used

    assert tuple(snapshot.index for snapshot in snapshots) == (2, 3)
    assert snapshots[0].tiles[0] == "rock"
    assert snapshots[1].objects[1] == "door"

    assert session.board == [
        [None, None, None, None],
        [None, None, None, None],
        [None, None, "I", None],
        [None, None, "I", None],
    ]
    assert session.tiles == [
        [None, None, None, None],
        [None, None, None, None],
        [None, None, None, None],
        [None, "ice", None, None],
    ]
    assert session.objects == [
        [None, None, None, None],
        [None, None, None, None],
        [None, None, "gem", None],
        ["key", None, None, None],
    ]
    assert session.active is not None
    assert session.active.kind == "O"


def test_spawn_blocked_sets_game_over_on_session_start() -> None:
    board = [[None for _ in range(10)] for _ in range(20)]
    board[0][4] = "#"

    session = PieceSession(width=10, height=20, bag=PieceBag(initial_queue=("O",)), board=board)

    assert session.game_over
    assert session.active is None


def test_locking_above_the_visible_playfield_marks_top_out() -> None:
    session = PieceSession(width=6, height=6, bag=PieceBag(initial_queue=("I",)))
    session.active = ActivePiece("I", rotation=1, x=0, y=-1)

    result = session.lock_active()

    assert result.top_out
    assert result.game_over
    assert result.cleared_rows == ()
    assert session.game_over
    assert session.active is None
    assert session.board[0][2] == "I"
    assert session.board[1][2] == "I"
    assert session.board[2][2] == "I"
