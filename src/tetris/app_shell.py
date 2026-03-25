from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Callable

from .config import AppConfig
from .engine import EngineRuntime, EngineState, GameLoop, PieceSession
from .stage import StageCatalog, StageSession
from .ui import (
    GameViewModel,
    ObjectivePanelModel,
    Renderer,
    build_game_view,
    build_objective_panel,
    create_default_renderer,
)


@dataclass(slots=True)
class TetrisApp:
    config: AppConfig
    renderer: Renderer
    stage_catalog: StageCatalog = field(default_factory=StageCatalog.bootstrap)
    engine: EngineRuntime = field(init=False)
    stage_session: StageSession = field(init=False)
    loop: GameLoop = field(init=False)
    _booted: bool = field(default=False, init=False)
    _last_gravity_tick: int = field(default=0, init=False)

    def __post_init__(self) -> None:
        self.engine = EngineRuntime.from_config(self.config)
        self.stage_session = StageSession(catalog=self.stage_catalog)
        self.loop = GameLoop(
            config=self.config,
            renderer=self.renderer,
            runtime=self.engine,
            on_tick=self._advance_gameplay,
        )
        bind = getattr(self.renderer, "bind", None)
        if callable(bind):
            bind(self)

    @property
    def is_booted(self) -> bool:
        return self._booted

    @property
    def objective_panel(self) -> ObjectivePanelModel:
        return build_objective_panel(self.stage_session)

    @property
    def game_view(self) -> GameViewModel:
        return build_game_view(self.stage_session)

    @property
    def gravity_interval(self) -> int:
        return max(1, self.config.target_fps // 2)

    def boot(self) -> None:
        if self._booted:
            return

        self.stage_session.activate()
        self.renderer.open()
        self._booted = True
        self._last_gravity_tick = 0
        self._render_now()
        self.loop.start()

    def run(self, frame_limit: int | None = 1) -> int:
        if not self._booted:
            self.boot()

        run_loop = getattr(self.renderer, "run_loop", None)
        if callable(run_loop) and not self.config.headless:
            return run_loop(self.loop, frame_limit=frame_limit)

        return self.loop.run(frame_limit=frame_limit)

    def shutdown(self) -> None:
        if not self._booted:
            return

        self.loop.stop()
        self.stage_session.reset()
        self.renderer.close()
        self._booted = False
        self._last_gravity_tick = 0

    def stop(self) -> None:
        if self._booted:
            self.loop.stop()

    def handle_action(self, action: str) -> bool:
        handlers = {
            "move_left": self.move_left,
            "move_right": self.move_right,
            "rotate_clockwise": self.rotate_clockwise,
            "soft_drop": self.soft_drop,
            "hard_drop": self.hard_drop,
            "hold": self.hold,
            "restart_stage": self.restart_stage,
            "advance_stage": self.advance_stage,
        }
        handler = handlers.get(action)
        if handler is None:
            return False
        return handler()

    def move_left(self) -> bool:
        return self._apply_move(lambda session: session.move_left())

    def move_right(self) -> bool:
        return self._apply_move(lambda session: session.move_right())

    def rotate_clockwise(self) -> bool:
        return self._apply_move(lambda session: session.rotate_clockwise())

    def soft_drop(self) -> bool:
        session = self._active_piece_session()
        if session is None:
            return False

        moved = session.soft_drop()
        if moved:
            self._last_gravity_tick = self.loop.state.tick
            self._render_now()
        return moved

    def hard_drop(self) -> bool:
        session = self._active_piece_session()
        if session is None or session.active is None:
            return False

        session.hard_drop()
        self._last_gravity_tick = self.loop.state.tick
        self._render_now()
        return True

    def hold(self) -> bool:
        return self._apply_move(lambda session: session.hold())

    def restart_stage(self) -> bool:
        if not self._booted:
            return False

        self.stage_session.restart()
        self._last_gravity_tick = self.loop.state.tick
        self._render_now()
        return True

    def advance_stage(self) -> bool:
        if not self._booted or self.stage_session.state.status != "cleared":
            return False

        next_stage = self.stage_session.activate_next()
        if next_stage is None:
            return False

        self._last_gravity_tick = self.loop.state.tick
        self._render_now()
        return True

    def _apply_move(self, action: Callable[[PieceSession], bool]) -> bool:
        session = self._active_piece_session()
        if session is None:
            return False

        changed = action(session)
        if changed:
            self._render_now()
        return changed

    def _active_piece_session(self) -> PieceSession | None:
        session = self.stage_session.piece_session
        if (
            not self._booted
            or session is None
            or session.active is None
            or session.game_over
            or self.stage_session.state.status != "active"
        ):
            return None
        return session

    def _advance_gameplay(self, state: EngineState) -> None:
        session = self._active_piece_session()
        if session is None:
            return
        if state.tick - self._last_gravity_tick < self.gravity_interval:
            return

        self._last_gravity_tick = state.tick
        if not session.soft_drop():
            session.lock_active()

    def _render_now(self) -> None:
        if self._booted:
            self.renderer.render(self.loop.state)


AppShell = TetrisApp


def create_app(
    config: AppConfig | None = None,
    *,
    headless: bool | None = None,
    stage_catalog: StageCatalog | None = None,
    renderer: Renderer | None = None,
) -> TetrisApp:
    resolved_config = config or AppConfig()
    if headless is not None and resolved_config.headless != headless:
        resolved_config = replace(resolved_config, headless=headless)

    resolved_renderer = renderer or create_default_renderer(headless=resolved_config.headless)
    resolved_stage_catalog = stage_catalog or StageCatalog.bootstrap()
    return TetrisApp(
        config=resolved_config,
        renderer=resolved_renderer,
        stage_catalog=resolved_stage_catalog,
    )
