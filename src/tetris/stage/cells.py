from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class WallTile:
    kind: str = "wall"
    solid: bool = True

    def on_line_clear(self) -> "WallTile":
        return self


@dataclass(frozen=True, slots=True)
class RockTile:
    kind: str = "rock"
    solid: bool = True

    def on_line_clear(self) -> "RockTile":
        return self


@dataclass(frozen=True, slots=True)
class IceTile:
    cracked: bool = False
    kind: str = "ice"
    solid: bool = True

    def on_line_clear(self) -> "IceTile | None":
        if self.cracked:
            return None
        return IceTile(cracked=True)


@dataclass(frozen=True, slots=True)
class DoorTile:
    kind: str = "door"
    solid: bool = False

    def on_line_clear(self) -> "DoorTile":
        return self


GoalTile = DoorTile

type StageTile = WallTile | RockTile | IceTile | DoorTile
type TileCell = StageTile | str | None


@dataclass(frozen=True, slots=True)
class KeyObject:
    identifier: str | None = None
    kind: str = "key"
    clears_with_line: bool = False


@dataclass(frozen=True, slots=True)
class GemObject:
    identifier: str | None = None
    kind: str = "gem"
    clears_with_line: bool = True


type StageObject = KeyObject | GemObject
type ObjectCell = StageObject | str | None


@dataclass(frozen=True, slots=True)
class CellPresentation:
    kind: str
    label: str


type TileFactory = Callable[[], StageTile]
type ObjectFactory = Callable[[str], StageObject]


_TILE_FACTORIES: dict[str, TileFactory] = {
    "#": WallTile,
    "R": RockTile,
    "I": IceTile,
    "C": lambda: IceTile(cracked=True),
    "D": DoorTile,
}

_OBJECT_FACTORIES: dict[str, ObjectFactory] = {
    "K": lambda identifier: KeyObject(identifier=f"key-{identifier}"),
    "G": lambda identifier: GemObject(identifier=f"gem-{identifier}"),
}


def parse_tile_token(token: str, *, row_index: int, column_index: int) -> StageTile | None:
    if token == ".":
        return None
    factory = _TILE_FACTORIES.get(token)
    if factory is None:
        raise ValueError(f"unknown tile token {token!r} at ({row_index}, {column_index})")
    return factory()


def parse_object_token(token: str, *, row_index: int, column_index: int) -> StageObject | None:
    if token == ".":
        return None
    identifier = f"{row_index}-{column_index}"
    factory = _OBJECT_FACTORIES.get(token)
    if factory is None:
        raise ValueError(f"unknown object token {token!r} at ({row_index}, {column_index})")
    return factory(identifier)


def describe_tile(tile: TileCell) -> CellPresentation | None:
    if isinstance(tile, WallTile) or tile == "wall":
        return CellPresentation(kind="wall", label="#")
    if isinstance(tile, RockTile) or tile == "rock":
        return CellPresentation(kind="rock", label="R")
    if isinstance(tile, IceTile):
        return CellPresentation(kind="cracked-ice" if tile.cracked else "ice", label="C" if tile.cracked else "I")
    if tile == "ice":
        return CellPresentation(kind="ice", label="I")
    if tile == "cracked-ice":
        return CellPresentation(kind="cracked-ice", label="C")
    if isinstance(tile, DoorTile) or tile in {"door", "goal"}:
        return CellPresentation(kind="door", label="D")
    return None


def describe_object(obj: ObjectCell) -> CellPresentation | None:
    if isinstance(obj, KeyObject) or obj == "key":
        return CellPresentation(kind="key", label="K")
    if isinstance(obj, GemObject) or obj == "gem":
        return CellPresentation(kind="gem", label="G")
    return None


def is_solid_tile(tile: TileCell) -> bool:
    if isinstance(tile, (WallTile, RockTile, IceTile)):
        return True
    return tile in {"wall", "rock", "ice", "cracked-ice"}


def is_goal_tile(tile: TileCell) -> bool:
    if isinstance(tile, DoorTile):
        return True
    return tile in {"door", "goal"}


def apply_line_clear_to_tile(tile: TileCell) -> TileCell:
    if isinstance(tile, IceTile):
        return tile.on_line_clear()
    if tile == "ice":
        return "cracked-ice"
    if tile == "cracked-ice":
        return None
    return tile


def clears_with_line(obj: ObjectCell) -> bool:
    if isinstance(obj, GemObject):
        return True
    if isinstance(obj, KeyObject):
        return False
    return obj == "gem"
