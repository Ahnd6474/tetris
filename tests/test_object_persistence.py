from __future__ import annotations

from tetris.engine import GemObject, KeyObject, PieceBag, PieceSession


def test_keys_and_gems_compact_without_duplication_or_loss() -> None:
    shifted_key = KeyObject("key-shifted")
    cleared_key = KeyObject("key-cleared")
    shifted_gem = GemObject("gem-shifted")
    cleared_gem = GemObject("gem-cleared")
    session = PieceSession(
        width=4,
        height=6,
        bag=PieceBag(initial_queue=("I",)),
        board=[
            [None, None, None, None],
            [None, None, None, None],
            [None, None, None, None],
            ["X", "X", "X", "X"],
            [None, None, None, None],
            ["X", "X", "X", "X"],
        ],
        objects=[
            [None, None, None, None],
            [shifted_key, None, None, shifted_gem],
            [None, None, None, None],
            [cleared_key, None, None, cleared_gem],
            [None, None, None, None],
            [None, None, None, None],
        ],
    )

    assert session.clear_filled_rows() == (3, 5)

    assert session.objects[3][0] is shifted_key
    assert session.objects[3][3] is shifted_gem
    assert session.objects[5][0] is cleared_key
    assert sum(obj is shifted_key for row in session.objects for obj in row) == 1
    assert sum(obj is cleared_key for row in session.objects for obj in row) == 1
    assert sum(obj is shifted_gem for row in session.objects for obj in row) == 1
    assert sum(obj is cleared_gem for row in session.objects for obj in row) == 0
