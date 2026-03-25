from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path
from typing import Callable

from .cells import DoorTile, GemObject, IceTile, KeyObject, RockTile, WallTile
from .objectives import ObjectiveDefinition

type FrozenBoardRow = tuple[str | None, ...]
type FrozenBoardMatrix = tuple[FrozenBoardRow, ...]
type FrozenStageRow = tuple[object | None, ...]
type FrozenStageMatrix = tuple[FrozenStageRow, ...]


def _empty_board(width: int, height: int) -> FrozenBoardMatrix:
    return tuple(tuple(None for _ in range(width)) for _ in range(height))


def _empty_stage_layer(width: int, height: int) -> FrozenStageMatrix:
    return tuple(tuple(None for _ in range(width)) for _ in range(height))


def _parse_stage_layer(
    rows: object,
    width: int,
    height: int,
    *,
    name: str,
    token_parser: Callable[[str, int, int], object | None],
) -> FrozenStageMatrix:
    if rows is None:
        return _empty_stage_layer(width, height)
    if not isinstance(rows, Sequence) or len(rows) != height:
        raise ValueError(f"{name} must include exactly {height} rows")

    parsed_rows: list[FrozenStageRow] = []
    for row_index, row in enumerate(rows):
        if not isinstance(row, str) or len(row) != width:
            raise ValueError(f"{name} row {row_index} must be a string with width {width}")
        parsed_rows.append(
            tuple(token_parser(token, row_index, column_index) for column_index, token in enumerate(row))
        )
    return tuple(parsed_rows)


def _parse_board_layer(rows: object, width: int, height: int) -> FrozenBoardMatrix:
    if rows is None:
        return _empty_board(width, height)
    if not isinstance(rows, Sequence) or len(rows) != height:
        raise ValueError(f"board must include exactly {height} rows")

    parsed_rows: list[FrozenBoardRow] = []
    for row_index, row in enumerate(rows):
        if not isinstance(row, str) or len(row) != width:
            raise ValueError(f"board row {row_index} must be a string with width {width}")
        parsed_rows.append(tuple(None if token == "." else token for token in row))
    return tuple(parsed_rows)


def _parse_tile_token(token: str, row_index: int, column_index: int) -> object | None:
    if token == ".":
        return None
    if token == "#":
        return WallTile()
    if token == "R":
        return RockTile()
    if token == "I":
        return IceTile()
    if token == "C":
        return IceTile(cracked=True)
    if token == "D":
        return DoorTile()
    raise ValueError(f"unknown tile token {token!r} at ({row_index}, {column_index})")


def _parse_object_token(token: str, row_index: int, column_index: int) -> object | None:
    identifier = f"{row_index}-{column_index}"
    if token == ".":
        return None
    if token == "K":
        return KeyObject(identifier=f"key-{identifier}")
    if token == "G":
        return GemObject(identifier=f"gem-{identifier}")
    raise ValueError(f"unknown object token {token!r} at ({row_index}, {column_index})")


@dataclass(frozen=True, slots=True)
class StageDefinition:
    identifier: str
    title: str
    objective: ObjectiveDefinition
    board_width: int
    board_height: int
    piece_queue: tuple[str, ...] = ()
    board: FrozenBoardMatrix = ()
    tiles: FrozenStageMatrix = ()
    objects: FrozenStageMatrix = ()

    def create_board(self) -> list[list[str | None]]:
        source = self.board or _empty_board(self.board_width, self.board_height)
        return [list(row) for row in source]

    def create_tiles(self) -> list[list[object | None]]:
        source = self.tiles or _empty_stage_layer(self.board_width, self.board_height)
        return [list(row) for row in source]

    def create_objects(self) -> list[list[object | None]]:
        source = self.objects or _empty_stage_layer(self.board_width, self.board_height)
        return [list(row) for row in source]


@dataclass(frozen=True, slots=True)
class StageCatalog:
    stages: tuple[StageDefinition, ...]

    def first(self) -> StageDefinition:
        if not self.stages:
            raise ValueError("stage catalog must contain at least one stage")
        return self.stages[0]

    def get(self, identifier: str) -> StageDefinition:
        for stage in self.stages:
            if stage.identifier == identifier:
                return stage
        raise KeyError(identifier)

    def next_after(self, identifier: str) -> StageDefinition | None:
        for index, stage in enumerate(self.stages):
            if stage.identifier != identifier:
                continue
            next_index = index + 1
            if next_index >= len(self.stages):
                return None
            return self.stages[next_index]
        raise KeyError(identifier)

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> "StageCatalog":
        raw_stages = payload.get("stages")
        if not isinstance(raw_stages, Sequence) or not raw_stages:
            raise ValueError("stage catalog payload must include a non-empty stages sequence")

        stages: list[StageDefinition] = []
        for raw_stage in raw_stages:
            if not isinstance(raw_stage, Mapping):
                raise ValueError("each stage entry must be a mapping")

            identifier = raw_stage.get("id", raw_stage.get("identifier"))
            title = raw_stage.get("title")
            board_width = raw_stage.get("board_width")
            board_height = raw_stage.get("board_height")
            objective_payload = raw_stage.get("objective")
            raw_queue = raw_stage.get("piece_queue", ())

            if not isinstance(identifier, str) or not isinstance(title, str):
                raise ValueError("stage entries must include string id and title values")
            if not isinstance(board_width, int) or not isinstance(board_height, int):
                raise ValueError("stage entries must include integer board dimensions")
            if not isinstance(objective_payload, Mapping):
                raise ValueError("stage entries must include an objective mapping")
            if not isinstance(raw_queue, Sequence):
                raise ValueError("piece_queue must be a sequence")

            piece_queue = tuple(kind for kind in raw_queue if isinstance(kind, str))
            if len(piece_queue) != len(raw_queue):
                raise ValueError("piece_queue entries must be strings")

            stages.append(
                StageDefinition(
                    identifier=identifier,
                    title=title,
                    objective=ObjectiveDefinition.from_payload(objective_payload),
                    board_width=board_width,
                    board_height=board_height,
                    piece_queue=piece_queue,
                    board=_parse_board_layer(raw_stage.get("board"), board_width, board_height),
                    tiles=_parse_stage_layer(
                        raw_stage.get("tiles"),
                        board_width,
                        board_height,
                        name="tiles",
                        token_parser=_parse_tile_token,
                    ),
                    objects=_parse_stage_layer(
                        raw_stage.get("objects"),
                        board_width,
                        board_height,
                        name="objects",
                        token_parser=_parse_object_token,
                    ),
                )
            )

        return cls(stages=tuple(stages))

    @classmethod
    def load(cls, path: str | Path) -> "StageCatalog":
        with Path(path).open("r", encoding="utf-8") as handle:
            return cls.from_dict(json.load(handle))

    @classmethod
    def bootstrap(cls) -> "StageCatalog":
        bundled_path = files("tetris.stage").joinpath("stages.json")
        with bundled_path.open("r", encoding="utf-8") as handle:
            return cls.from_dict(json.load(handle))
