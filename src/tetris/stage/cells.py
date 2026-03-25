from __future__ import annotations

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
