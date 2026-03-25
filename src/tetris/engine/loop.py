from __future__ import annotations

from dataclasses import dataclass
from time import sleep
from typing import Protocol

from ..config import AppConfig
from .state import EngineRuntime, EngineState


class FrameSink(Protocol):
    def render(self, state: EngineState) -> None:
        ...


@dataclass(slots=True)
class GameLoop:
    config: AppConfig
    renderer: FrameSink
    runtime: EngineRuntime | None = None

    def __post_init__(self) -> None:
        if self.runtime is None:
            self.runtime = EngineRuntime.from_config(self.config)

    @property
    def state(self) -> EngineState:
        return self.runtime.state

    def start(self) -> None:
        self.state.running = True

    def run(self, frame_limit: int = 1) -> int:
        if frame_limit < 0:
            raise ValueError("frame_limit must be >= 0")
        if not self.state.running:
            raise RuntimeError("game loop must be started before running")

        frames = 0
        while self.state.running and frames < frame_limit:
            self.tick()
            frames += 1
            if not self.config.headless and self.config.target_fps > 0:
                sleep(1 / self.config.target_fps)

        return frames

    def tick(self) -> None:
        if not self.state.running:
            raise RuntimeError("game loop must be started before ticking")

        self.state.tick += 1
        self.renderer.render(self.state)

    def stop(self) -> None:
        self.state.running = False
