from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from ..engine import EngineState


class Renderer(Protocol):
    def open(self) -> None:
        ...

    def render(self, state: EngineState) -> None:
        ...

    def close(self) -> None:
        ...


@dataclass(slots=True)
class NullRenderer:
    frames_rendered: int = 0
    is_open: bool = False

    def open(self) -> None:
        self.is_open = True

    def render(self, state: EngineState) -> None:
        if not self.is_open:
            raise RuntimeError("renderer must be opened before rendering")

        self.frames_rendered = state.tick

    def close(self) -> None:
        self.is_open = False
