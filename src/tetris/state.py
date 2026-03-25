from dataclasses import dataclass


@dataclass(slots=True)
class GameState:
    tick: int = 0
    running: bool = False
