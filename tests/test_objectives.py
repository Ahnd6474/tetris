from __future__ import annotations

from tetris.engine import DoorTile, GemObject, IceTile, KeyObject, PieceBag, PieceSession
from tetris.stage import ObjectiveDefinition, ObjectiveRequirement, evaluate_objectives


def _session(
    *,
    width: int = 4,
    height: int = 4,
    tiles: list[list[object | None]] | None = None,
    objects: list[list[object | None]] | None = None,
) -> PieceSession:
    return PieceSession(
        width=width,
        height=height,
        bag=PieceBag(initial_queue=("I",)),
        tiles=tiles,
        objects=objects,
    )


def test_key_to_bottom_objective_completes_when_key_reaches_bottom() -> None:
    session = _session(
        objects=[
            [None, None, None, None],
            [None, None, None, None],
            [None, None, None, None],
            [None, KeyObject("target"), None, None],
        ]
    )

    evaluation = evaluate_objectives(
        ObjectiveDefinition(kind="key_to_bottom", summary="Bring the key down."),
        session,
    )

    assert evaluation.completed
    assert not evaluation.failed
    assert evaluation.key_at_bottom


def test_key_to_door_objective_uses_goal_tiles() -> None:
    session = _session(
        tiles=[
            [None, None, None, None],
            [None, DoorTile(), None, None],
            [None, None, None, None],
            [None, None, None, None],
        ],
        objects=[
            [None, None, None, None],
            [None, KeyObject("target"), None, None],
            [None, None, None, None],
            [None, None, None, None],
        ],
    )

    evaluation = evaluate_objectives(
        ObjectiveDefinition(kind="key_to_door", summary="Bring the key to the door."),
        session,
    )

    assert evaluation.completed
    assert evaluation.key_on_goal


def test_clear_ice_objective_requires_every_ice_tile_to_be_removed() -> None:
    session = _session(
        tiles=[
            [None, None, None, None],
            [None, IceTile(), None, None],
            [None, None, IceTile(cracked=True), None],
            [None, None, None, None],
        ]
    )

    evaluation = evaluate_objectives(
        ObjectiveDefinition(kind="clear_ice", summary="Clear the ice."),
        session,
    )

    assert not evaluation.completed
    assert evaluation.remaining_ice == 2

    session.tiles[1][1] = None
    session.tiles[2][2] = None
    evaluation = evaluate_objectives(
        ObjectiveDefinition(kind="clear_ice", summary="Clear the ice."),
        session,
    )

    assert evaluation.completed
    assert evaluation.remaining_ice == 0


def test_collect_gems_objective_requires_gems_to_be_cleared() -> None:
    session = _session(
        objects=[
            [None, None, None, None],
            [None, GemObject("a"), None, None],
            [None, None, GemObject("b"), None],
            [None, None, None, None],
        ]
    )

    evaluation = evaluate_objectives(
        ObjectiveDefinition(kind="collect_gems", summary="Collect the gems."),
        session,
    )

    assert not evaluation.completed
    assert evaluation.remaining_gems == 2

    session.objects[1][1] = None
    session.objects[2][2] = None
    evaluation = evaluate_objectives(
        ObjectiveDefinition(kind="collect_gems", summary="Collect the gems."),
        session,
    )

    assert evaluation.completed
    assert evaluation.remaining_gems == 0


def test_mixed_objective_requires_all_goals_and_marks_failure_on_top_out() -> None:
    session = _session(
        width=5,
        height=5,
        tiles=[
            [None, None, None, None, None],
            [None, None, None, None, None],
            [None, None, None, None, None],
            [None, None, None, None, None],
            [None, None, DoorTile(), None, None],
        ],
        objects=[
            [None, None, None, None, None],
            [None, None, None, None, None],
            [None, None, None, None, None],
            [None, None, None, GemObject("gem"), None],
            [None, None, KeyObject("key"), None, None],
        ],
    )
    session.game_over = True

    evaluation = evaluate_objectives(
        ObjectiveDefinition(
            kind="mixed",
            summary="Do everything.",
            requirements=(
                ObjectiveRequirement("key_to_door"),
                ObjectiveRequirement("collect_gems"),
            ),
        ),
        session,
    )

    assert not evaluation.completed
    assert evaluation.failed
    assert tuple(result.completed for result in evaluation.results) == (True, False)
