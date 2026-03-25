from __future__ import annotations

from tetris.engine import DoorTile, IceTile, PieceBag, PieceSession, RockTile
from tetris.stage import is_goal_tile, is_solid_tile


def test_solid_stage_tiles_block_piece_movement() -> None:
    session = PieceSession(
        width=4,
        height=4,
        bag=PieceBag(initial_queue=("O",)),
        tiles=[
            [None, None, None, None],
            [RockTile(), None, None, None],
            [None, None, None, None],
            [None, None, None, None],
        ],
    )

    assert session.active is not None
    start_cells = session.active_cells

    assert not session.move_left()
    assert session.active_cells == start_cells


def test_rock_tiles_survive_line_clears() -> None:
    session = PieceSession(
        width=4,
        height=4,
        bag=PieceBag(initial_queue=("I",)),
        board=[
            [None, None, None, None],
            [None, None, None, None],
            [None, None, None, None],
            [None, "X", "X", "X"],
        ],
        tiles=[
            [None, None, None, None],
            [None, None, None, None],
            [None, None, None, None],
            [RockTile(), None, None, None],
        ],
    )

    assert session.clear_filled_rows() == (3,)
    assert session.board[3] == [None, None, None, None]
    assert session.tiles[3][0] == RockTile()


def test_ice_requires_two_line_clears_to_break() -> None:
    session = PieceSession(
        width=4,
        height=4,
        bag=PieceBag(initial_queue=("I",)),
        board=[
            [None, None, None, None],
            [None, None, None, None],
            [None, None, None, None],
            [None, "X", "X", "X"],
        ],
        tiles=[
            [None, None, None, None],
            [None, None, None, None],
            [None, None, None, None],
            [IceTile(), None, None, None],
        ],
    )

    assert session.clear_filled_rows() == (3,)
    assert session.tiles[3][0] == IceTile(cracked=True)

    session.board[3][1:] = ["X", "X", "X"]

    assert session.clear_filled_rows() == (3,)
    assert session.tiles[3][0] is None


def test_door_tiles_are_goal_markers_without_blocking_line_fills() -> None:
    door = DoorTile()

    assert is_goal_tile(door)
    assert not is_solid_tile(door)
