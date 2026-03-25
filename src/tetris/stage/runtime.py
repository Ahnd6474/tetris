from __future__ import annotations

from dataclasses import dataclass, field

from .data import StageCatalog, StageDefinition


@dataclass(slots=True)
class StageState:
    current_stage_id: str | None = None
    status: str = "ready"


@dataclass(slots=True)
class StageSession:
    catalog: StageCatalog
    state: StageState = field(default_factory=StageState)

    def activate(self, stage_id: str | None = None) -> StageDefinition:
        stage = self.catalog.first() if stage_id is None else self.catalog.get(stage_id)
        self.state.current_stage_id = stage.identifier
        self.state.status = "active"
        return stage

    @property
    def current_stage(self) -> StageDefinition:
        stage_id = self.state.current_stage_id or self.catalog.first().identifier
        return self.catalog.get(stage_id)

    @property
    def objective_summary(self) -> str:
        return self.current_stage.objective.summary

    def reset(self) -> None:
        self.state.current_stage_id = None
        self.state.status = "ready"
