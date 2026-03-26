from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path
from typing import Callable, Protocol

from .cells import parse_object_token, parse_tile_token
from .objectives import ObjectiveDefinition

type FrozenBoardRow = tuple[str | None, ...]
type FrozenBoardMatrix = tuple[FrozenBoardRow, ...]
type FrozenStageRow = tuple[object | None, ...]
type FrozenStageMatrix = tuple[FrozenStageRow, ...]


class StageValidationError(ValueError):
    def __init__(self, source_label: str, issues: Sequence[str]) -> None:
        self.source_label = source_label
        self.issues = tuple(issues)
        details = "\n".join(f"- {issue}" for issue in self.issues)
        super().__init__(f"Invalid stage content from {source_label}:\n{details}")


class StageContentSource(Protocol):
    @property
    def description(self) -> str:
        ...

    def load_payload(self) -> Mapping[str, object]:
        ...


@dataclass(frozen=True, slots=True)
class FileSystemStageContentSource:
    path: Path

    @property
    def description(self) -> str:
        return str(self.path)

    def load_payload(self) -> Mapping[str, object]:
        if self.path.is_dir():
            return _load_directory_payload(self.path)
        return _load_json_mapping(self.path)


@dataclass(frozen=True, slots=True)
class BundledStageContentSource:
    package: str = "tetris.stage"
    resource_name: str = "stages.json"

    @property
    def description(self) -> str:
        return f"{self.package}:{self.resource_name}"

    def load_payload(self) -> Mapping[str, object]:
        resource = files(self.package).joinpath(self.resource_name)
        with resource.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if not isinstance(payload, Mapping):
            raise ValueError(f"{self.description} must decode to a mapping payload")
        return payload


def _load_json_mapping(path: Path) -> Mapping[str, object]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, Mapping):
        raise ValueError(f"{path} must decode to a mapping payload")
    return payload


def _load_directory_payload(path: Path) -> Mapping[str, object]:
    manifest_path = path / "catalog.json"
    manifest = _load_json_mapping(manifest_path)
    raw_stage_files = manifest.get("stages")
    if not _is_sequence(raw_stage_files) or not raw_stage_files:
        raise ValueError("stage directory catalog must include a non-empty stages sequence")

    stages: list[Mapping[str, object]] = []
    for index, stage_file in enumerate(raw_stage_files):
        if not isinstance(stage_file, str) or not stage_file:
            raise ValueError(f"catalog.json stages entry {index} must be a non-empty file name")
        stages.append(_load_json_mapping(path / stage_file))
    return {"stages": stages}


def _is_sequence(value: object) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray))


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
    if not _is_sequence(rows) or len(rows) != height:
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
    if not _is_sequence(rows) or len(rows) != height:
        raise ValueError(f"board must include exactly {height} rows")

    parsed_rows: list[FrozenBoardRow] = []
    for row_index, row in enumerate(rows):
        if not isinstance(row, str) or len(row) != width:
            raise ValueError(f"board row {row_index} must be a string with width {width}")
        parsed_rows.append(tuple(None if token == "." else token for token in row))
    return tuple(parsed_rows)


def _parse_piece_queue(raw_queue: object) -> tuple[str, ...]:
    from ..engine.pieces import TETROMINO_KINDS

    if raw_queue is None:
        return ()
    if not _is_sequence(raw_queue):
        raise ValueError("piece_queue must be a sequence")

    queue: list[str] = []
    for index, kind in enumerate(raw_queue):
        if not isinstance(kind, str):
            raise ValueError(f"piece_queue entry {index} must be a string")
        if kind not in TETROMINO_KINDS:
            raise ValueError(f"piece_queue entry {index} has unknown tetromino kind {kind!r}")
        queue.append(kind)
    return tuple(queue)


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


def _parse_stage_definition(raw_stage: Mapping[str, object]) -> StageDefinition:
    identifier = raw_stage.get("id", raw_stage.get("identifier"))
    title = raw_stage.get("title")
    board_width = raw_stage.get("board_width")
    board_height = raw_stage.get("board_height")
    objective_payload = raw_stage.get("objective")

    if not isinstance(identifier, str) or not identifier:
        raise ValueError("stage entries must include a non-empty string id")
    if not isinstance(title, str) or not title:
        raise ValueError("stage entries must include a non-empty string title")
    if not isinstance(board_width, int) or not isinstance(board_height, int):
        raise ValueError("stage entries must include integer board dimensions")
    if board_width <= 0 or board_height <= 0:
        raise ValueError("stage board dimensions must be positive")
    if not isinstance(objective_payload, Mapping):
        raise ValueError("stage entries must include an objective mapping")

    return StageDefinition(
        identifier=identifier,
        title=title,
        objective=ObjectiveDefinition.from_payload(objective_payload),
        board_width=board_width,
        board_height=board_height,
        piece_queue=_parse_piece_queue(raw_stage.get("piece_queue", ())),
        board=_parse_board_layer(raw_stage.get("board"), board_width, board_height),
        tiles=_parse_stage_layer(
            raw_stage.get("tiles"),
            board_width,
            board_height,
            name="tiles",
            token_parser=lambda token, row_index, column_index: parse_tile_token(
                token,
                row_index=row_index,
                column_index=column_index,
            ),
        ),
        objects=_parse_stage_layer(
            raw_stage.get("objects"),
            board_width,
            board_height,
            name="objects",
            token_parser=lambda token, row_index, column_index: parse_object_token(
                token,
                row_index=row_index,
                column_index=column_index,
            ),
        ),
    )


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
    def from_dict(cls, payload: Mapping[str, object], *, source_label: str = "<memory>") -> "StageCatalog":
        raw_stages = payload.get("stages")
        if not _is_sequence(raw_stages) or not raw_stages:
            raise StageValidationError(
                source_label,
                ("stage catalog payload must include a non-empty stages sequence",),
            )

        stages: list[StageDefinition] = []
        issues: list[str] = []
        seen_ids: set[str] = set()
        for index, raw_stage in enumerate(raw_stages):
            if not isinstance(raw_stage, Mapping):
                issues.append(f"stage[{index}]: each stage entry must be a mapping")
                continue

            identifier = raw_stage.get("id", raw_stage.get("identifier"))
            stage_label = f"stage[{index}]"
            if isinstance(identifier, str) and identifier:
                stage_label = f"{stage_label} ({identifier})"

            try:
                stage = _parse_stage_definition(raw_stage)
            except ValueError as error:
                issues.append(f"{stage_label}: {error}")
                continue

            if stage.identifier in seen_ids:
                issues.append(f"{stage_label}: duplicate stage id {stage.identifier!r}")
                continue
            seen_ids.add(stage.identifier)
            stages.append(stage)

        if issues:
            raise StageValidationError(source_label, issues)

        return cls(stages=tuple(stages))

    @classmethod
    def from_source(cls, source: StageContentSource) -> "StageCatalog":
        return cls.from_dict(source.load_payload(), source_label=source.description)

    @classmethod
    def load(cls, path: str | Path) -> "StageCatalog":
        return cls.from_source(FileSystemStageContentSource(path=Path(path)))

    @classmethod
    def bootstrap(cls) -> "StageCatalog":
        return cls.from_source(BundledStageContentSource())
