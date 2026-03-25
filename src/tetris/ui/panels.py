from __future__ import annotations

from dataclasses import dataclass

from ..stage import StageSession


@dataclass(frozen=True, slots=True)
class ObjectivePanelModel:
    stage_title: str
    objective_summary: str
    stage_status: str


def build_objective_panel(session: StageSession) -> ObjectivePanelModel:
    stage = session.current_stage
    return ObjectivePanelModel(
        stage_title=stage.title,
        objective_summary=stage.objective.summary,
        stage_status=session.state.status,
    )
