from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Callable

from .config import AppConfig, RendererStrategy, StageSource, StageSourceKind
from .engine import EngineRuntime, EngineState, GameLoop, PieceSession
from .stage import StageCatalog, StageSession
from .ui import (
    BoardCellModel,
    GameViewModel,
    NullRenderer,
    ObjectivePanelModel,
    Renderer,
    build_game_view,
    build_objective_panel,
)


class StartupFailureKind(StrEnum):
    STAGE_LOAD = "stage_load"
    TKINTER_UNAVAILABLE = "tkinter_unavailable"
    DISPLAY_UNAVAILABLE = "display_unavailable"
    RENDERER_UNAVAILABLE = "renderer_unavailable"


@dataclass(frozen=True, slots=True)
class StartupFailure:
    kind: StartupFailureKind
    message: str
    detail: str


def _load_stage_catalog(stage_source: StageSource) -> StageCatalog:
    if stage_source.kind == StageSourceKind.BUNDLED:
        return StageCatalog.bootstrap()
    if stage_source.path is None:
        raise ValueError("file stage sources must include a path")
    return StageCatalog.load(stage_source.path)


def _create_renderer(strategy: RendererStrategy) -> Renderer:
    if strategy == RendererStrategy.NULL:
        return NullRenderer()
    if strategy == RendererStrategy.TK:
        from .ui.tk_renderer import TkRenderer

        return TkRenderer()
    raise ValueError(f"unsupported renderer strategy: {strategy}")


def _classify_renderer_failure(error: Exception) -> StartupFailure:
    if isinstance(error, ModuleNotFoundError) and error.name == "tkinter":
        return StartupFailure(
            kind=StartupFailureKind.TKINTER_UNAVAILABLE,
            message="Tk UI is unavailable because tkinter is not installed.",
            detail=str(error),
        )
    if error.__class__.__name__ == "TclError":
        return StartupFailure(
            kind=StartupFailureKind.DISPLAY_UNAVAILABLE,
            message="Tk UI could not open a local display.",
            detail=str(error),
        )
    return StartupFailure(
        kind=StartupFailureKind.RENDERER_UNAVAILABLE,
        message="The configured renderer could not be started.",
        detail=str(error),
    )


def _build_stage_failure(stage_source: StageSource, error: Exception) -> StartupFailure:
    source_label = "bundled stage data" if stage_source.kind == StageSourceKind.BUNDLED else str(stage_source.path)
    return StartupFailure(
        kind=StartupFailureKind.STAGE_LOAD,
        message=f"Unable to load stages from {source_label}.",
        detail=str(error),
    )


@dataclass(frozen=True, slots=True)
class BootstrapAssets:
    renderer: Renderer
    stage_catalog: StageCatalog | None
    startup_failure: StartupFailure | None = None


def resolve_bootstrap_assets(
    config: AppConfig,
    *,
    stage_catalog: StageCatalog | None = None,
    renderer: Renderer | None = None,
) -> BootstrapAssets:
    resolved_renderer = renderer or _create_renderer(config.renderer_strategy)
    if stage_catalog is not None:
        return BootstrapAssets(renderer=resolved_renderer, stage_catalog=stage_catalog)

    try:
        resolved_catalog = _load_stage_catalog(config.stage_source)
    except Exception as error:
        return BootstrapAssets(
            renderer=resolved_renderer,
            stage_catalog=None,
            startup_failure=_build_stage_failure(config.stage_source, error),
        )

    return BootstrapAssets(renderer=resolved_renderer, stage_catalog=resolved_catalog)


@dataclass(slots=True)
class TetrisApp:
    config: AppConfig
    renderer: Renderer
    stage_catalog: StageCatalog | None = None
    startup_failure: StartupFailure | None = None
    engine: EngineRuntime = field(init=False)
    stage_session: StageSession | None = field(init=False, default=None)
    loop: GameLoop = field(init=False)
    _booted: bool = field(default=False, init=False)
    _last_gravity_tick: int = field(default=0, init=False)

    def __post_init__(self) -> None:
        if self.stage_catalog is None and self.startup_failure is None:
            assets = resolve_bootstrap_assets(
                self.config,
                stage_catalog=None,
                renderer=self.renderer,
            )
            self.stage_catalog = assets.stage_catalog
            self._remember_startup_failure(assets.startup_failure)

        self.engine = EngineRuntime.from_config(self.config)
        if self.stage_catalog is not None:
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
        if self.startup_failure is not None or self.stage_session is None:
            return ObjectivePanelModel(
                stage_title="Startup Error",
                objective_summary="Resolve the startup problem and relaunch the app.",
                stage_status="startup-error",
            )
        return build_objective_panel(self.stage_session)

    @property
    def game_view(self) -> GameViewModel:
        if self.startup_failure is not None or self.stage_session is None:
            return self._build_startup_error_view()
        return build_game_view(self.stage_session)

    @property
    def gravity_interval(self) -> int:
        return max(1, self.config.target_fps // 2)

    def boot(self) -> None:
        if self._booted:
            return

        if self.stage_session is not None and self.startup_failure is None:
            try:
                self.stage_session.activate()
            except Exception as error:
                self.stage_session.reset()
                self._remember_startup_failure(_build_stage_failure(self.config.stage_source, error))

        try:
            self.renderer.open()
        except Exception as error:
            self._remember_startup_failure(_classify_renderer_failure(error))
            fallback_renderer = NullRenderer()
            bind = getattr(fallback_renderer, "bind", None)
            if callable(bind):
                bind(self)
            self.renderer = fallback_renderer
            self.loop.renderer = fallback_renderer
            self.renderer.open()

        self._booted = True
        self._last_gravity_tick = 0
        self._render_now()
        if self.startup_failure is None:
            self.loop.start()

    def run(self, frame_limit: int | None = 1) -> int:
        if not self._booted:
            self.boot()

        if self.startup_failure is not None:
            return 0

        run_loop = getattr(self.renderer, "run_loop", None)
        if callable(run_loop) and not self.config.headless:
            return run_loop(self.loop, frame_limit=frame_limit)

        return self.loop.run(frame_limit=frame_limit)

    def shutdown(self) -> None:
        if not self._booted:
            return

        self.loop.stop()
        if self.stage_session is not None:
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
        if not self._booted or self.startup_failure is not None or self.stage_session is None:
            return False

        self.stage_session.restart()
        self._last_gravity_tick = self.loop.state.tick
        self._render_now()
        return True

    def advance_stage(self) -> bool:
        if (
            not self._booted
            or self.startup_failure is not None
            or self.stage_session is None
            or self.stage_session.state.status != "cleared"
        ):
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
        if self.stage_session is None:
            return None

        session = self.stage_session.piece_session
        if (
            not self._booted
            or self.startup_failure is not None
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

    def _remember_startup_failure(self, failure: StartupFailure) -> None:
        if self.startup_failure is None:
            self.startup_failure = failure

    def _build_startup_error_view(self) -> GameViewModel:
        board_rows = tuple(
            tuple(BoardCellModel(kind="empty", label="") for _ in range(self.config.board_width))
            for _ in range(self.config.board_height)
        )
        progress_lines = (
            f"Mode: {self.config.runtime_mode}",
            f"Renderer: {self.config.renderer_strategy}",
            f"Stage source: {self.config.stage_source.kind}",
            f"Save path: {self.config.save_path}",
        )
        if self.startup_failure is not None and self.startup_failure.detail:
            progress_lines = progress_lines + (f"Detail: {self.startup_failure.detail}",)
        return GameViewModel(
            stage_label="Bootstrap",
            stage_title="Startup Error",
            objective_summary="The app could not finish startup.",
            stage_status="startup-error",
            status_message=(
                self.startup_failure.message
                if self.startup_failure is not None
                else "Startup is not ready."
            ),
            hold_kind=None,
            next_queue=(),
            requirements=(),
            progress_lines=progress_lines,
            board_rows=board_rows,
            can_advance=False,
        )


AppShell = TetrisApp


def create_app(
    config: AppConfig | None = None,
    *,
    headless: bool | None = None,
    stage_catalog: StageCatalog | None = None,
    renderer: Renderer | None = None,
) -> TetrisApp:
    resolved_config = config or AppConfig.bootstrap()
    if headless is not None and resolved_config.headless != headless:
        resolved_config = AppConfig.bootstrap(
            board_width=resolved_config.board_width,
            board_height=resolved_config.board_height,
            target_fps=resolved_config.target_fps,
            runtime_mode=resolved_config.runtime_mode,
            stage_source=resolved_config.stage_source,
            save_path=resolved_config.save_path,
            renderer_strategy=RendererStrategy.NULL if headless else RendererStrategy.TK,
        )

    assets = resolve_bootstrap_assets(
        resolved_config,
        stage_catalog=stage_catalog,
        renderer=renderer,
    )
    return TetrisApp(
        config=resolved_config,
        renderer=assets.renderer,
        stage_catalog=assets.stage_catalog,
        startup_failure=assets.startup_failure,
    )
