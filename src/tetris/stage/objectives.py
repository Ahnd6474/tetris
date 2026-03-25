from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ObjectiveDefinition:
    kind: str
    summary: str
