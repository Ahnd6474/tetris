from __future__ import annotations

from dataclasses import dataclass

from .objectives import ObjectiveDefinition


@dataclass(frozen=True, slots=True)
class StageDefinition:
    identifier: str
    title: str
    objective: ObjectiveDefinition
    board_width: int
    board_height: int


@dataclass(frozen=True, slots=True)
class StageCatalog:
    stages: tuple[StageDefinition, ...]

    def first(self) -> StageDefinition:
        if not self.stages:
            raise ValueError("stage catalog must contain at least one stage")
        return self.stages[0]

    def get(self, identifier: str) -> StageDefinition:
        for stage in self.stages:
            if stage.identifier == identifier:
                return stage
        raise KeyError(identifier)

    @classmethod
    def bootstrap(cls) -> "StageCatalog":
        return cls(
            stages=(
                StageDefinition(
                    identifier="stage-001",
                    title="Bootstrap Stage",
                    objective=ObjectiveDefinition(
                        kind="bootstrap",
                        summary="Advance the shell without a display backend.",
                    ),
                    board_width=10,
                    board_height=20,
                ),
            )
        )
