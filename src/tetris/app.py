from __future__ import annotations

from dataclasses import dataclass, field, replace

from .config import AppConfig
from .game_loop import GameLoop
from .renderers import NullRenderer, Renderer


@dataclass(slots=True)
class TetrisApp:
    """Small application wrapper around the core loop."""

    config: AppConfig
    renderer: Renderer
    loop: GameLoop = field(init=False)
    _booted: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        self.loop = GameLoop(config=self.config, renderer=self.renderer)

    @property
    def is_booted(self) -> bool:
        return self._booted

    def boot(self) -> None:
        if self._booted:
            return

        self.renderer.open()
        self.loop.start()
        self._booted = True

    def run(self, frame_limit: int = 1) -> int:
        if not self._booted:
            self.boot()

        return self.loop.run(frame_limit=frame_limit)

    def shutdown(self) -> None:
        if not self._booted:
            return

        self.loop.stop()
        self.renderer.close()
        self._booted = False


def create_app(config: AppConfig | None = None, *, headless: bool | None = None) -> TetrisApp:
    resolved_config = config or AppConfig()
    if headless is not None and resolved_config.headless != headless:
        resolved_config = replace(resolved_config, headless=headless)

    renderer = NullRenderer()
    return TetrisApp(config=resolved_config, renderer=renderer)
