from __future__ import annotations

from dataclasses import dataclass, field, replace

from .config import AppConfig
from .engine import EngineRuntime, GameLoop
from .stage import StageCatalog, StageSession
from .ui import NullRenderer, ObjectivePanelModel, Renderer, build_objective_panel


@dataclass(slots=True)
class TetrisApp:
    config: AppConfig
    renderer: Renderer
    stage_catalog: StageCatalog = field(default_factory=StageCatalog.bootstrap)
    engine: EngineRuntime = field(init=False)
    stage_session: StageSession = field(init=False)
    loop: GameLoop = field(init=False)
    _booted: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        self.engine = EngineRuntime.from_config(self.config)
        self.stage_session = StageSession(catalog=self.stage_catalog)
        self.loop = GameLoop(config=self.config, renderer=self.renderer, runtime=self.engine)

    @property
    def is_booted(self) -> bool:
        return self._booted

    @property
    def objective_panel(self) -> ObjectivePanelModel:
        return build_objective_panel(self.stage_session)

    def boot(self) -> None:
        if self._booted:
            return

        self.renderer.open()
        self.stage_session.activate()
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
        self.stage_session.reset()
        self.renderer.close()
        self._booted = False


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

    resolved_renderer = renderer or NullRenderer()
    resolved_stage_catalog = stage_catalog or StageCatalog.bootstrap()
    return TetrisApp(
        config=resolved_config,
        renderer=resolved_renderer,
        stage_catalog=resolved_stage_catalog,
    )
