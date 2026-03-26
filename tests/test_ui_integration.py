from __future__ import annotations

from dataclasses import dataclass, field

from tetris import AppConfig, create_app
from tetris.actions import AppAction, ShellState
from tetris.engine import EngineState
from tetris.ui import GameViewModel
from tetris.ui.tk_renderer import TkRenderer


@dataclass(slots=True)
class RecordingRenderer:
    controller: object | None = field(default=None, init=False)
    is_open: bool = field(default=False, init=False)
    frames_rendered: int = field(default=0, init=False)
    views: list[GameViewModel] = field(default_factory=list, init=False)

    def bind(self, controller: object) -> None:
        self.controller = controller

    def open(self) -> None:
        self.is_open = True

    def render(self, state: EngineState) -> None:
        if not self.is_open or self.controller is None:
            raise RuntimeError("renderer must be opened and bound before rendering")
        self.frames_rendered = state.tick
        self.views.append(self.controller.game_view)

    def close(self) -> None:
        self.is_open = False


def test_controller_actions_update_the_shared_game_view() -> None:
    renderer = RecordingRenderer()
    app = create_app(AppConfig(headless=True), renderer=renderer)

    app.boot()

    initial_view = renderer.views[-1]
    assert initial_view.stage_title == "Key Delivery"
    assert initial_view.stage_status == ShellState.TITLE.value
    assert initial_view.status_message == "Press Enter or Start to begin."
    assert initial_view.hold_kind is None
    assert initial_view.next_queue[:4] == ("O", "I", "T", "L")
    assert _count_cells(initial_view, "active") == 0
    assert _action(initial_view, AppAction.START).label == "Start"

    assert app.handle_action(AppAction.START)
    started_view = renderer.views[-1]
    assert started_view.stage_status == ShellState.ACTIVE.value
    assert started_view.status_message.startswith("Arrows move")
    assert _count_cells(started_view, "active") == 4

    session = app.stage_session.piece_session
    assert session is not None
    start_x = session.active.x

    assert app.handle_action(AppAction.PAUSE)
    paused_view = renderer.views[-1]
    assert paused_view.stage_status == ShellState.PAUSED.value
    assert paused_view.status_message == "Game paused. Press Enter to continue or R to restart."
    assert _action(paused_view, AppAction.START).label == "Continue"
    assert not app.handle_action(AppAction.MOVE_LEFT)

    assert app.handle_action(AppAction.START)
    assert app.handle_action(AppAction.MOVE_LEFT)
    moved_view = renderer.views[-1]
    assert session.active is not None
    assert session.active.x == start_x - 1
    assert _count_cells(moved_view, "active") == 4

    assert app.handle_action(AppAction.HOLD)
    held_view = renderer.views[-1]
    assert held_view.hold_kind == "O"
    assert _active_labels(held_view) == {"I"}
    assert held_view.next_queue[:2] == ("T", "L")

    key = session.objects[3][2]
    session.objects[3][2] = None
    session.objects[session.height - 1][2] = key
    app.stage_session.refresh()
    app.run(frame_limit=1)

    cleared_view = renderer.views[-1]
    assert cleared_view.stage_status == ShellState.CLEARED.value
    assert cleared_view.can_advance
    assert "Stage cleared" in cleared_view.status_message
    assert "Key row: 6/6" in cleared_view.progress_lines
    assert _action(cleared_view, AppAction.NEXT_STAGE).enabled

    assert app.handle_action(AppAction.NEXT_STAGE)
    next_stage_view = renderer.views[-1]
    assert next_stage_view.stage_status == ShellState.ACTIVE.value

    session = app.stage_session.piece_session
    assert session is not None
    session.game_over = True
    app.stage_session.refresh()
    app.run(frame_limit=1)

    failed_view = renderer.views[-1]
    assert failed_view.stage_status == ShellState.FAILED.value
    assert failed_view.status_message == "Stage failed. Press R or Restart."
    assert _action(failed_view, AppAction.RESTART_STAGE).enabled

    app.shutdown()
    assert not renderer.is_open


def test_tk_renderer_key_bindings_match_app_actions() -> None:
    assert TkRenderer.KEY_BINDINGS["<Return>"] == AppAction.START
    assert TkRenderer.KEY_BINDINGS["<Escape>"] == AppAction.PAUSE
    assert TkRenderer.KEY_BINDINGS["<Left>"] == AppAction.MOVE_LEFT
    assert TkRenderer.KEY_BINDINGS["<Right>"] == AppAction.MOVE_RIGHT
    assert TkRenderer.KEY_BINDINGS["<Up>"] == AppAction.ROTATE_CLOCKWISE
    assert TkRenderer.KEY_BINDINGS["<Down>"] == AppAction.SOFT_DROP
    assert TkRenderer.KEY_BINDINGS["<space>"] == AppAction.HARD_DROP
    assert TkRenderer.KEY_BINDINGS["<KeyPress-c>"] == AppAction.HOLD
    assert TkRenderer.KEY_BINDINGS["<KeyPress-r>"] == AppAction.RESTART_STAGE
    assert TkRenderer.KEY_BINDINGS["<KeyPress-n>"] == AppAction.NEXT_STAGE


def _count_cells(view: GameViewModel, kind: str) -> int:
    return sum(cell.kind == kind for row in view.board_rows for cell in row)


def _active_labels(view: GameViewModel) -> set[str]:
    return {cell.label for row in view.board_rows for cell in row if cell.kind == "active"}


def _action(view: GameViewModel, target: AppAction):
    for action in view.actions:
        if action.action == target:
            return action
    raise AssertionError(f"missing action {target}")
