from __future__ import annotations

from tetris.engine import ActivePiece, GemObject, KeyObject, PieceBag, PieceSession, RockTile


def test_lock_active_clears_rows_and_respects_stage_mechanics() -> None:
    snapshots = []
    shifted_gem = GemObject("gem-shifted")
    shifted_key = KeyObject("key-shifted")
    cleared_gem = GemObject("gem-cleared")
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
            [RockTile(), None, None, None],
            [None, None, None, None],
            [None, None, None, None],
        ],
        objects=[
            [None, None, shifted_gem, None],
            [shifted_key, None, None, None],
            [None, None, None, None],
            [None, cleared_gem, None, None],
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
    assert snapshots[1].objects[1] is cleared_gem

    assert session.board == [
        [None, None, None, None],
        [None, None, None, None],
        [None, None, "I", None],
        [None, None, "I", None],
    ]
    assert session.tiles == [
        [None, None, None, None],
        [RockTile(), None, None, None],
        [None, None, None, None],
        [None, None, None, None],
    ]
    assert session.objects[2][2] is shifted_gem
    assert session.objects[3][0] is shifted_key
    assert sum(obj is shifted_gem for row in session.objects for obj in row) == 1
    assert sum(obj is shifted_key for row in session.objects for obj in row) == 1
    assert sum(obj is cleared_gem for row in session.objects for obj in row) == 0
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
