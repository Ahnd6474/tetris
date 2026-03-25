from __future__ import annotations

import pytest

from tetris.engine import PieceBag, PieceSession, TETROMINO_KINDS


def test_seven_bag_generator_yields_complete_deterministic_bags() -> None:
    first_bag = PieceBag(seed=17)
    second_bag = PieceBag(seed=17)

    first_sequence = [first_bag.pop() for _ in range(14)]
    second_sequence = [second_bag.pop() for _ in range(14)]

    assert first_sequence == second_sequence
    assert tuple(sorted(first_sequence[:7])) == TETROMINO_KINDS
    assert tuple(sorted(first_sequence[7:14])) == TETROMINO_KINDS


@pytest.mark.parametrize("kind", TETROMINO_KINDS)
def test_each_tetromino_spawns_with_four_cells_inside_the_board(kind: str) -> None:
    session = PieceSession(width=10, height=20, bag=PieceBag(initial_queue=(kind,)))

    assert session.active is not None
    assert session.active.kind == kind
    assert len(session.active_cells) == 4
    assert len(set(session.active_cells)) == 4
    assert all(0 <= cell_x < session.width for cell_x, _ in session.active_cells)
    assert all(0 <= cell_y < session.height for _, cell_y in session.active_cells)


def test_invalid_horizontal_moves_are_rejected_by_wall_and_cell_collisions() -> None:
    wall_session = PieceSession(width=10, height=20, bag=PieceBag(initial_queue=("O",)))

    assert wall_session.active is not None
    while wall_session.move_left():
        continue

    left_edge = wall_session.active.x
    assert not wall_session.move_left()
    assert wall_session.active.x == left_edge

    blocked_session = PieceSession(width=10, height=20, bag=PieceBag(initial_queue=("O",)))
    blocked_session.board[0][6] = "#"

    assert blocked_session.active is not None
    start_cells = blocked_session.active_cells
    assert not blocked_session.move_right()
    assert blocked_session.active_cells == start_cells


def test_rotation_changes_orientation_and_rejects_collisions() -> None:
    open_session = PieceSession(width=10, height=20, bag=PieceBag(initial_queue=("T",)))

    assert open_session.active is not None
    start_cells = open_session.active_cells
    assert open_session.rotate_clockwise()
    assert open_session.active.rotation == 1
    assert open_session.active_cells != start_cells

    blocked_session = PieceSession(width=10, height=20, bag=PieceBag(initial_queue=("T",)))
    blocked_session.board[2][4] = "#"

    assert blocked_session.active is not None
    assert not blocked_session.rotate_clockwise()
    assert blocked_session.active.rotation == 0


def test_soft_drop_moves_the_active_piece_down_by_one_row() -> None:
    session = PieceSession(width=10, height=20, bag=PieceBag(initial_queue=("L",)))

    start_cells = session.active_cells
    assert session.soft_drop()
    assert session.active_cells == tuple((cell_x, cell_y + 1) for cell_x, cell_y in start_cells)


def test_hard_drop_lands_on_expected_row_and_locks_the_piece() -> None:
    session = PieceSession(width=10, height=20, bag=PieceBag(initial_queue=("O", "I")))

    landing_row = session.hard_drop()

    assert landing_row == 19
    assert session.board[18][4] == "O"
    assert session.board[18][5] == "O"
    assert session.board[19][4] == "O"
    assert session.board[19][5] == "O"
    assert session.active is not None
    assert session.active.kind == "I"


def test_hold_is_limited_to_one_swap_until_the_piece_locks() -> None:
    session = PieceSession(width=10, height=20, bag=PieceBag(initial_queue=("T", "I", "O", "L")))

    assert session.active is not None
    assert session.active.kind == "T"
    assert session.next_queue[:3] == ("I", "O", "L")

    assert session.hold()
    assert session.hold_kind == "T"
    assert session.active is not None
    assert session.active.kind == "I"
    assert session.next_queue[:2] == ("O", "L")

    assert not session.hold()
    assert session.active.kind == "I"

    session.hard_drop()

    assert session.active is not None
    assert session.active.kind == "O"
    assert session.hold()
    assert session.hold_kind == "O"
    assert session.active.kind == "T"
