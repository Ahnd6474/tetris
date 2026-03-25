from __future__ import annotations

import json

from tetris.stage import DoorTile, IceTile, KeyObject, StageCatalog


def test_bootstrap_catalog_loads_bundled_stage_data() -> None:
    catalog = StageCatalog.bootstrap()

    assert tuple(stage.identifier for stage in catalog.stages) == (
        "stage-001",
        "stage-002",
        "stage-003",
        "stage-004",
        "stage-005",
    )

    first_stage = catalog.first()
    assert first_stage.title == "Key Delivery"
    assert first_stage.objective.kind == "key_to_bottom"
    assert first_stage.piece_queue[:2] == ("O", "I")
    assert first_stage.board[4] == ("O", "O", None, None, "O", "O")
    assert isinstance(first_stage.objects[3][2], KeyObject)

    door_stage = catalog.get("stage-002")
    assert isinstance(door_stage.tiles[5][2], DoorTile)
    assert door_stage.board[5] == ("T", "T", None, "T", "T", "T")

    ice_stage = catalog.get("stage-003")
    assert ice_stage.board_height == 8
    assert ice_stage.tiles[6][1] == IceTile()
    assert ice_stage.tiles[7][1] == IceTile()


def test_catalog_loads_from_external_json_file(tmp_path) -> None:
    stage_path = tmp_path / "custom-stages.json"
    stage_path.write_text(
        json.dumps(
            {
                "stages": [
                    {
                        "id": "custom-001",
                        "title": "Custom Stage",
                        "objective": {
                            "kind": "mixed",
                            "summary": "Bring the key home and clear the ice.",
                            "requirements": ["key_to_bottom", "clear_ice"]
                        },
                        "board_width": 4,
                        "board_height": 4,
                        "piece_queue": ["I", "O"],
                        "board": [
                            "....",
                            ".X..",
                            "....",
                            "...."
                        ],
                        "tiles": [
                            "....",
                            ".I..",
                            "....",
                            "...."
                        ],
                        "objects": [
                            "....",
                            ".K..",
                            "....",
                            "...."
                        ]
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    catalog = StageCatalog.load(stage_path)
    stage = catalog.first()

    assert stage.identifier == "custom-001"
    assert tuple(requirement.kind for requirement in stage.objective.requirements) == (
        "key_to_bottom",
        "clear_ice",
    )
    assert stage.create_board() == [
        [None, None, None, None],
        [None, "X", None, None],
        [None, None, None, None],
        [None, None, None, None],
    ]
    assert stage.create_tiles()[1][1] == IceTile()
    assert isinstance(stage.create_objects()[1][1], KeyObject)
