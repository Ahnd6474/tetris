from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from ..actions import AppAction
from ..engine import EngineState
from .panels import GameViewModel

if TYPE_CHECKING:
    from ..engine import GameLoop


class Renderer(Protocol):
    def open(self) -> None:
        ...

    def render(self, state: EngineState) -> None:
        ...

    def close(self) -> None:
        ...


class UIController(Protocol):
    @property
    def game_view(self) -> GameViewModel:
        ...

    def handle_action(self, action: AppAction | str) -> bool:
        ...

    def stop(self) -> None:
        ...


class InteractiveRenderer(Renderer, Protocol):
    def bind(self, controller: UIController) -> None:
        ...

    def run_loop(self, game_loop: "GameLoop", frame_limit: int | None = None) -> int:
        ...


@dataclass(slots=True)
class NullRenderer:
    frames_rendered: int = 0
    is_open: bool = False

    def bind(self, controller: UIController) -> None:
        return None

    def open(self) -> None:
        self.is_open = True

    def render(self, state: EngineState) -> None:
        if not self.is_open:
            raise RuntimeError("renderer must be opened before rendering")

        self.frames_rendered = state.tick

    def close(self) -> None:
        self.is_open = False
