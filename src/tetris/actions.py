from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class AppAction(StrEnum):
    START = "start"
    PAUSE = "pause"
    MOVE_LEFT = "move_left"
    MOVE_RIGHT = "move_right"
    ROTATE_CLOCKWISE = "rotate_clockwise"
    SOFT_DROP = "soft_drop"
    HARD_DROP = "hard_drop"
    HOLD = "hold"
    RESTART_STAGE = "restart_stage"
    NEXT_STAGE = "next_stage"


class ShellState(StrEnum):
    TITLE = "title"
    ACTIVE = "active"
    PAUSED = "paused"
    CLEARED = "cleared"
    FAILED = "failed"
    STARTUP_ERROR = "startup-error"


@dataclass(frozen=True, slots=True)
class ActionModel:
    action: AppAction
    label: str
    shortcut: str | None = None
    enabled: bool = True


ACTION_LABELS = {
    AppAction.START: "Start",
    AppAction.PAUSE: "Pause",
    AppAction.MOVE_LEFT: "Move Left",
    AppAction.MOVE_RIGHT: "Move Right",
    AppAction.ROTATE_CLOCKWISE: "Rotate",
    AppAction.SOFT_DROP: "Soft Drop",
    AppAction.HARD_DROP: "Hard Drop",
    AppAction.HOLD: "Hold",
    AppAction.RESTART_STAGE: "Restart",
    AppAction.NEXT_STAGE: "Next Stage",
}

ACTION_SHORTCUTS = {
    AppAction.START: "Enter",
    AppAction.PAUSE: "Esc",
    AppAction.MOVE_LEFT: "Left",
    AppAction.MOVE_RIGHT: "Right",
    AppAction.ROTATE_CLOCKWISE: "Up",
    AppAction.SOFT_DROP: "Down",
    AppAction.HARD_DROP: "Space",
    AppAction.HOLD: "C",
    AppAction.RESTART_STAGE: "R",
    AppAction.NEXT_STAGE: "N",
}

GAMEPLAY_ACTIONS = (
    AppAction.MOVE_LEFT,
    AppAction.MOVE_RIGHT,
    AppAction.ROTATE_CLOCKWISE,
    AppAction.SOFT_DROP,
    AppAction.HARD_DROP,
    AppAction.HOLD,
)


def build_action_model(
    action: AppAction,
    *,
    label: str | None = None,
    enabled: bool = True,
) -> ActionModel:
    return ActionModel(
        action=action,
        label=label or ACTION_LABELS[action],
        shortcut=ACTION_SHORTCUTS.get(action),
        enabled=enabled,
    )
