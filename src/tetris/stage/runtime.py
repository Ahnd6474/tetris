from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .data import StageCatalog, StageDefinition
from .objectives import ObjectiveEvaluation, evaluate_objectives

if TYPE_CHECKING:
    from ..engine.pieces import PieceSession


@dataclass(slots=True)
class StageState:
    current_stage_id: str | None = None
    status: str = "ready"
    last_evaluation: ObjectiveEvaluation | None = None


@dataclass(slots=True)
class StageSession:
    catalog: StageCatalog
    state: StageState = field(default_factory=StageState)
    piece_session: PieceSession | None = None

    def activate(self, stage_id: str | None = None) -> StageDefinition:
        from ..engine.pieces import PieceBag, PieceSession

        stage = self.catalog.first() if stage_id is None else self.catalog.get(stage_id)
        self.state.current_stage_id = stage.identifier
        self.piece_session = PieceSession(
            width=stage.board_width,
            height=stage.board_height,
            bag=PieceBag(initial_queue=stage.piece_queue),
            board=stage.create_board(),
            tiles=stage.create_tiles(),
            objects=stage.create_objects(),
            on_lock=lambda _session, _result: self.refresh(),
        )
        self.state.status = "active"
        self.refresh()
        return stage

    @property
    def current_stage(self) -> StageDefinition:
        stage_id = self.state.current_stage_id or self.catalog.first().identifier
        return self.catalog.get(stage_id)

    @property
    def objective_summary(self) -> str:
        return self.current_stage.objective.summary

    @property
    def evaluation(self) -> ObjectiveEvaluation | None:
        return self.state.last_evaluation

    def activate_next(self) -> StageDefinition | None:
        next_stage = self.catalog.next_after(self.current_stage.identifier)
        if next_stage is None:
            return None
        return self.activate(next_stage.identifier)

    def refresh(self) -> ObjectiveEvaluation | None:
        if self.piece_session is None:
            self.state.last_evaluation = None
            self.state.status = "ready"
            return None

        evaluation = evaluate_objectives(self.current_stage.objective, self.piece_session)
        self.state.last_evaluation = evaluation
        if evaluation.completed:
            self.state.status = "cleared"
        elif evaluation.failed:
            self.state.status = "failed"
        else:
            self.state.status = "active"
        return evaluation

    def restart(self) -> StageDefinition:
        return self.activate(self.current_stage.identifier)

    def reset(self) -> None:
        self.piece_session = None
        self.state.current_stage_id = None
        self.state.status = "ready"
        self.state.last_evaluation = None
