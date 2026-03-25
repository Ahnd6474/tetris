from __future__ import annotations

from dataclasses import dataclass, field

from ..config import AppConfig


@dataclass(frozen=True, slots=True)
class BoardSpec:
    width: int
    height: int


@dataclass(slots=True)
class EngineState:
    tick: int = 0
    running: bool = False


@dataclass(slots=True)
class EngineRuntime:
    board: BoardSpec
    state: EngineState = field(default_factory=EngineState)

    @classmethod
    def from_config(cls, config: AppConfig) -> "EngineRuntime":
        return cls(board=BoardSpec(width=config.board_width, height=config.board_height))
