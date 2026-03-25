from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .cells import GemObject, IceTile, KeyObject, is_goal_tile

if TYPE_CHECKING:
    from ..engine.pieces import PieceSession


OBJECTIVE_KEY_TO_BOTTOM = "key_to_bottom"
OBJECTIVE_KEY_TO_DOOR = "key_to_door"
OBJECTIVE_CLEAR_ICE = "clear_ice"
OBJECTIVE_COLLECT_GEMS = "collect_gems"

KNOWN_OBJECTIVE_KINDS = frozenset(
    {
        OBJECTIVE_KEY_TO_BOTTOM,
        OBJECTIVE_KEY_TO_DOOR,
        OBJECTIVE_CLEAR_ICE,
        OBJECTIVE_COLLECT_GEMS,
    }
)


@dataclass(frozen=True, slots=True)
class ObjectiveRequirement:
    kind: str

    def __post_init__(self) -> None:
        if self.kind not in KNOWN_OBJECTIVE_KINDS:
            raise ValueError(f"unknown objective kind: {self.kind}")


@dataclass(frozen=True, slots=True)
class ObjectiveDefinition:
    kind: str
    summary: str
    requirements: tuple[ObjectiveRequirement, ...] = ()

    def __post_init__(self) -> None:
        if self.requirements:
            object.__setattr__(self, "requirements", tuple(self.requirements))
            return
        object.__setattr__(self, "requirements", (ObjectiveRequirement(self.kind),))

    @classmethod
    def from_payload(cls, payload: Mapping[str, object]) -> "ObjectiveDefinition":
        kind = payload.get("kind")
        summary = payload.get("summary")
        if not isinstance(kind, str) or not isinstance(summary, str):
            raise ValueError("objective payload must include string kind and summary values")

        raw_requirements = payload.get("requirements", ())
        requirements: list[ObjectiveRequirement] = []
        if not isinstance(raw_requirements, Sequence):
            raise ValueError("objective requirements must be a sequence")
        for raw_requirement in raw_requirements:
            if isinstance(raw_requirement, str):
                requirements.append(ObjectiveRequirement(raw_requirement))
                continue
            if isinstance(raw_requirement, Mapping) and isinstance(raw_requirement.get("kind"), str):
                requirements.append(ObjectiveRequirement(raw_requirement["kind"]))
                continue
            raise ValueError("objective requirements must be strings or mappings with a kind")

        return cls(kind=kind, summary=summary, requirements=tuple(requirements))


@dataclass(frozen=True, slots=True)
class ObjectiveRequirementResult:
    kind: str
    completed: bool


@dataclass(frozen=True, slots=True)
class ObjectiveEvaluation:
    completed: bool
    failed: bool
    results: tuple[ObjectiveRequirementResult, ...]
    remaining_ice: int
    remaining_gems: int
    key_positions: tuple[tuple[int, int], ...]
    key_at_bottom: bool
    key_on_goal: bool


def _is_ice_tile(tile: object | None) -> bool:
    if isinstance(tile, IceTile):
        return True
    return tile in {"ice", "cracked-ice"}


def _is_gem_object(obj: object | None) -> bool:
    if isinstance(obj, GemObject):
        return True
    return obj == "gem"


def _is_key_object(obj: object | None) -> bool:
    if isinstance(obj, KeyObject):
        return True
    return obj == "key"


def evaluate_objectives(definition: ObjectiveDefinition, session: "PieceSession") -> ObjectiveEvaluation:
    remaining_ice = sum(1 for row in session.tiles for tile in row if _is_ice_tile(tile))
    remaining_gems = sum(1 for row in session.objects for obj in row if _is_gem_object(obj))
    key_positions = tuple(
        (column_index, row_index)
        for row_index, row in enumerate(session.objects)
        for column_index, obj in enumerate(row)
        if _is_key_object(obj)
    )
    key_at_bottom = any(row_index == session.height - 1 for _, row_index in key_positions)
    key_on_goal = any(is_goal_tile(session.tiles[row_index][column_index]) for column_index, row_index in key_positions)

    results: list[ObjectiveRequirementResult] = []
    for requirement in definition.requirements:
        completed = False
        if requirement.kind == OBJECTIVE_KEY_TO_BOTTOM:
            completed = key_at_bottom
        elif requirement.kind == OBJECTIVE_KEY_TO_DOOR:
            completed = key_on_goal
        elif requirement.kind == OBJECTIVE_CLEAR_ICE:
            completed = remaining_ice == 0
        elif requirement.kind == OBJECTIVE_COLLECT_GEMS:
            completed = remaining_gems == 0
        results.append(ObjectiveRequirementResult(kind=requirement.kind, completed=completed))

    completed = all(result.completed for result in results)
    failed = session.game_over and not completed
    return ObjectiveEvaluation(
        completed=completed,
        failed=failed,
        results=tuple(results),
        remaining_ice=remaining_ice,
        remaining_gems=remaining_gems,
        key_positions=key_positions,
        key_at_bottom=key_at_bottom,
        key_on_goal=key_on_goal,
    )
