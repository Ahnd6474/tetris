from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import StrEnum
from typing import Callable

from .actions import AppAction, ShellState, build_action_model
from .config import AppConfig, RendererStrategy, StageSource, StageSourceKind
from .engine import EngineRuntime, EngineState, GameLoop, PieceSession
from .persistence import PlayerProgress, PlayerSaveData, PlayerSaveStore, PlayerSettings
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
    player_settings: PlayerSettings = field(init=False)
    _shell_state: ShellState = field(init=False, default=ShellState.TITLE)
    _booted: bool = field(default=False, init=False)
    _last_gravity_tick: int = field(default=0, init=False)
    _save_store: PlayerSaveStore = field(init=False, repr=False)
    _player_save_data: PlayerSaveData = field(init=False, repr=False)
    _last_saved_snapshot: PlayerSaveData | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        self._save_store = PlayerSaveStore(path=self.config.save_path)
        self._player_save_data = self._save_store.load()
        self.player_settings = self._player_save_data.settings

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
            self._restore_player_state()
        self.loop = GameLoop(
            config=self.config,
            renderer=self.renderer,
            runtime=self.engine,
            on_tick=self._advance_gameplay,
        )
        self._sync_shell_state_from_session()
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
                stage_status=ShellState.STARTUP_ERROR.value,
            )
        return build_objective_panel(self.stage_session, stage_status=self.shell_state.value)

    @property
    def game_view(self) -> GameViewModel:
        if self.startup_failure is not None or self.stage_session is None:
            return self._build_startup_error_view()
        return build_game_view(
            self.stage_session,
            stage_status=self.shell_state.value,
            status_message=self._status_message(),
            actions=self._available_actions(),
        )

    @property
    def shell_state(self) -> ShellState:
        return self._shell_state

    @property
    def gravity_interval(self) -> int:
        return max(1, self.config.target_fps // 2)

    def boot(self) -> None:
        if self._booted:
            return

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
        self._persist_player_state()
        if self.stage_session is not None:
            self.stage_session.reset()
        self._sync_shell_state_from_session()
        self.renderer.close()
        self._booted = False
        self._last_gravity_tick = 0

    def stop(self) -> None:
        if self._booted:
            self.loop.stop()

    def update_player_settings(self, *, show_controls: bool | None = None) -> bool:
        updated_settings = replace(
            self.player_settings,
            show_controls=self.player_settings.show_controls if show_controls is None else show_controls,
        )
        if updated_settings == self.player_settings:
            return False

        self.player_settings = updated_settings
        self._persist_player_state()
        if self._booted:
            self._render_now()
        return True

    def handle_action(self, action: AppAction | str) -> bool:
        try:
            resolved_action = AppAction(action)
        except ValueError:
            return False

        handlers = {
            AppAction.START: self.start,
            AppAction.PAUSE: self.pause,
            AppAction.MOVE_LEFT: self.move_left,
            AppAction.MOVE_RIGHT: self.move_right,
            AppAction.ROTATE_CLOCKWISE: self.rotate_clockwise,
            AppAction.SOFT_DROP: self.soft_drop,
            AppAction.HARD_DROP: self.hard_drop,
            AppAction.HOLD: self.hold,
            AppAction.RESTART_STAGE: self.restart_stage,
            AppAction.NEXT_STAGE: self.advance_stage,
        }
        handler = handlers.get(resolved_action)
        if handler is None:
            return False
        return handler()

    def start(self) -> bool:
        if not self._booted or self.startup_failure is not None or self.stage_session is None:
            return False

        if self.shell_state == ShellState.PAUSED:
            self._shell_state = ShellState.ACTIVE
            self._render_now()
            return True

        if self.shell_state != ShellState.TITLE:
            return False

        try:
            self.stage_session.activate(self.stage_session.current_stage.identifier)
        except Exception as error:
            self.stage_session.reset()
            self._remember_startup_failure(_build_stage_failure(self.config.stage_source, error))
            self._render_now()
            return False

        self._last_gravity_tick = self.loop.state.tick
        self._sync_shell_state_from_session()
        self._render_now()
        return True

    def pause(self) -> bool:
        if self._active_piece_session() is None:
            return False

        self._shell_state = ShellState.PAUSED
        self._render_now()
        return True

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
            self._sync_shell_state_from_session()
            self._render_now()
        return moved

    def hard_drop(self) -> bool:
        session = self._active_piece_session()
        if session is None or session.active is None:
            return False

        session.hard_drop()
        self._last_gravity_tick = self.loop.state.tick
        self._sync_shell_state_from_session()
        self._render_now()
        return True

    def hold(self) -> bool:
        return self._apply_move(lambda session: session.hold())

    def restart_stage(self) -> bool:
        if (
            not self._booted
            or self.startup_failure is not None
            or self.stage_session is None
            or self.stage_session.piece_session is None
        ):
            return False

        self.stage_session.restart()
        self._last_gravity_tick = self.loop.state.tick
        self._sync_shell_state_from_session()
        self._render_now()
        self._persist_player_state()
        return True

    def advance_stage(self) -> bool:
        if (
            not self._booted
            or self.startup_failure is not None
            or self.stage_session is None
            or self.shell_state != ShellState.CLEARED
        ):
            return False

        next_stage = self.stage_session.activate_next()
        if next_stage is None:
            return False

        self._last_gravity_tick = self.loop.state.tick
        self._sync_shell_state_from_session()
        self._render_now()
        self._persist_player_state()
        return True

    def _apply_move(self, action: Callable[[PieceSession], bool]) -> bool:
        session = self._active_piece_session()
        if session is None:
            return False

        changed = action(session)
        if changed:
            self._sync_shell_state_from_session()
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
            or self.shell_state != ShellState.ACTIVE
            or self.stage_session.state.status != "active"
        ):
            return None
        return session

    def _advance_gameplay(self, state: EngineState) -> None:
        self._sync_shell_state_from_session()
        session = self._active_piece_session()
        if session is None:
            return
        if state.tick - self._last_gravity_tick < self.gravity_interval:
            return

        self._last_gravity_tick = state.tick
        if not session.soft_drop():
            session.lock_active()
        self._sync_shell_state_from_session()

    def _render_now(self) -> None:
        if self._booted:
            self.renderer.render(self.loop.state)

    def _remember_startup_failure(self, failure: StartupFailure | None) -> None:
        if failure is None:
            return
        if self.startup_failure is None:
            self.startup_failure = failure
        self._shell_state = ShellState.STARTUP_ERROR

    def _status_message(self) -> str:
        if not self.player_settings.show_controls:
            if self.shell_state == ShellState.TITLE:
                return "Ready to begin."
            if self.shell_state == ShellState.PAUSED:
                return "Game paused."
            if self.shell_state == ShellState.CLEARED:
                if self._can_advance():
                    return "Stage cleared."
                return "Final stage cleared."
            if self.shell_state == ShellState.FAILED:
                return "Stage failed."
            return "Stage in progress."
        if self.shell_state == ShellState.TITLE:
            return "Press Enter or Start to begin."
        if self.shell_state == ShellState.PAUSED:
            return "Game paused. Press Enter to continue or R to restart."
        if self.shell_state == ShellState.CLEARED:
            if self._can_advance():
                return "Stage cleared. Press N or Next Stage."
            return "Final stage cleared. Press R to replay."
        if self.shell_state == ShellState.FAILED:
            return "Stage failed. Press R or Restart."
        return "Arrows move, Up rotates, Down soft drops, Space hard drops, C holds."

    def _available_actions(self) -> tuple:
        if self.startup_failure is not None or self.stage_session is None:
            return ()

        if self.shell_state == ShellState.TITLE:
            return (build_action_model(AppAction.START),)
        if self.shell_state == ShellState.PAUSED:
            return (
                build_action_model(AppAction.START, label="Continue"),
                build_action_model(AppAction.RESTART_STAGE),
            )
        if self.shell_state == ShellState.CLEARED:
            actions = [build_action_model(AppAction.RESTART_STAGE)]
            if self._can_advance():
                actions.append(build_action_model(AppAction.NEXT_STAGE))
            return tuple(actions)
        if self.shell_state == ShellState.FAILED:
            return (build_action_model(AppAction.RESTART_STAGE),)
        return (
            build_action_model(AppAction.PAUSE),
            build_action_model(AppAction.RESTART_STAGE),
            build_action_model(AppAction.MOVE_LEFT),
            build_action_model(AppAction.MOVE_RIGHT),
            build_action_model(AppAction.ROTATE_CLOCKWISE),
            build_action_model(AppAction.SOFT_DROP),
            build_action_model(AppAction.HARD_DROP),
            build_action_model(AppAction.HOLD),
        )

    def _can_advance(self) -> bool:
        if self.stage_session is None:
            return False
        return self.stage_session.catalog.next_after(self.stage_session.current_stage.identifier) is not None

    def _sync_shell_state_from_session(self) -> None:
        previous_shell_state = self._shell_state
        if self.startup_failure is not None:
            self._shell_state = ShellState.STARTUP_ERROR
            return
        if self.stage_session is None or self.stage_session.piece_session is None:
            self._shell_state = ShellState.TITLE
            return
        if self.stage_session.state.status == "cleared":
            self._shell_state = ShellState.CLEARED
            if previous_shell_state != self._shell_state:
                self._persist_player_state()
            return
        if self.stage_session.state.status == "failed":
            self._shell_state = ShellState.FAILED
            if previous_shell_state != self._shell_state:
                self._persist_player_state()
            return
        if self._shell_state != ShellState.PAUSED:
            self._shell_state = ShellState.ACTIVE

    def _restore_player_state(self) -> None:
        if self.stage_session is None:
            return

        progress = self._player_save_data.progress
        current_stage_id = self._resolve_catalog_stage_id(progress.current_stage_id)
        selected_stage_id = self._resolve_catalog_stage_id(progress.last_selected_stage_id)
        unlocked_stage_id = self._furthest_stage_id(
            self._resolve_catalog_stage_id(progress.unlocked_stage_id),
            current_stage_id,
            selected_stage_id,
        )
        if unlocked_stage_id is None:
            unlocked_stage_id = self.stage_session.catalog.first().identifier

        restored_stage_id = selected_stage_id or current_stage_id or unlocked_stage_id
        if self._stage_index(restored_stage_id) > self._stage_index(unlocked_stage_id):
            restored_stage_id = unlocked_stage_id

        self.stage_session.state.current_stage_id = restored_stage_id
        self._player_save_data = PlayerSaveData(
            progress=PlayerProgress(
                unlocked_stage_id=unlocked_stage_id,
                current_stage_id=restored_stage_id,
                last_selected_stage_id=restored_stage_id,
            ),
            settings=self.player_settings,
        )

    def _persist_player_state(self) -> bool:
        snapshot = self._build_player_save_data()
        if snapshot == self._last_saved_snapshot:
            return True
        if not self._save_store.save(snapshot):
            return False
        self._player_save_data = snapshot
        self._last_saved_snapshot = snapshot
        return True

    def _build_player_save_data(self) -> PlayerSaveData:
        progress = self._player_save_data.progress
        if self.stage_session is None:
            return PlayerSaveData(progress=progress, settings=self.player_settings)

        current_stage_id = self._resolve_catalog_stage_id(self.stage_session.current_stage.identifier)
        last_selected_stage_id = current_stage_id
        unlocked_stage_id = self._furthest_stage_id(progress.unlocked_stage_id, current_stage_id)

        if self.stage_session.state.status == "cleared":
            next_stage_id = self._next_stage_id(current_stage_id)
            if next_stage_id is not None:
                last_selected_stage_id = next_stage_id
                unlocked_stage_id = self._furthest_stage_id(unlocked_stage_id, next_stage_id)

        if unlocked_stage_id is None:
            unlocked_stage_id = self.stage_session.catalog.first().identifier
        if current_stage_id is None:
            current_stage_id = unlocked_stage_id
        if last_selected_stage_id is None:
            last_selected_stage_id = unlocked_stage_id

        return PlayerSaveData(
            progress=PlayerProgress(
                unlocked_stage_id=unlocked_stage_id,
                current_stage_id=current_stage_id,
                last_selected_stage_id=last_selected_stage_id,
            ),
            settings=self.player_settings,
        )

    def _resolve_catalog_stage_id(self, stage_id: str | None) -> str | None:
        if self.stage_session is None or stage_id is None:
            return None
        try:
            self.stage_session.catalog.get(stage_id)
        except KeyError:
            return None
        return stage_id

    def _stage_index(self, stage_id: str) -> int:
        if self.stage_session is None:
            return -1
        for index, stage in enumerate(self.stage_session.catalog.stages):
            if stage.identifier == stage_id:
                return index
        return -1

    def _furthest_stage_id(self, *stage_ids: str | None) -> str | None:
        valid_stage_ids = [stage_id for stage_id in stage_ids if self._resolve_catalog_stage_id(stage_id) is not None]
        if not valid_stage_ids:
            return None
        return max(valid_stage_ids, key=self._stage_index)

    def _next_stage_id(self, stage_id: str | None) -> str | None:
        if self.stage_session is None or stage_id is None:
            return None
        try:
            next_stage = self.stage_session.catalog.next_after(stage_id)
        except KeyError:
            return None
        return next_stage.identifier if next_stage is not None else None

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
            stage_status=ShellState.STARTUP_ERROR.value,
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
            actions=(),
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
