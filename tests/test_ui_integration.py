from __future__ import annotations

from dataclasses import dataclass, field

from tetris import AppConfig, create_app
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
    assert initial_view.stage_status == "active"
    assert initial_view.status_message.startswith("Arrows move")
    assert initial_view.hold_kind is None
    assert initial_view.next_queue[:3] == ("O", "T", "L")
    assert _count_cells(initial_view, "active") == 4

    session = app.stage_session.piece_session
    assert session is not None
    start_x = session.active.x

    assert app.handle_action("move_left")
    moved_view = renderer.views[-1]
    assert session.active is not None
    assert session.active.x == start_x - 1
    assert _count_cells(moved_view, "active") == 4

    assert app.handle_action("hold")
    held_view = renderer.views[-1]
    assert held_view.hold_kind == "I"
    assert _active_labels(held_view) == {"O"}
    assert held_view.next_queue[:2] == ("T", "L")

    key = session.objects[1][2]
    session.objects[1][2] = None
    session.objects[session.height - 1][2] = key
    app.stage_session.refresh()
    app.run(frame_limit=1)

    cleared_view = renderer.views[-1]
    assert cleared_view.stage_status == "cleared"
    assert cleared_view.can_advance
    assert "Stage cleared" in cleared_view.status_message
    assert "Key row: 6/6" in cleared_view.progress_lines

    app.shutdown()
    assert not renderer.is_open


def test_tk_renderer_key_bindings_match_app_actions() -> None:
    assert TkRenderer.KEY_BINDINGS["<Left>"] == "move_left"
    assert TkRenderer.KEY_BINDINGS["<Right>"] == "move_right"
    assert TkRenderer.KEY_BINDINGS["<Up>"] == "rotate_clockwise"
    assert TkRenderer.KEY_BINDINGS["<Down>"] == "soft_drop"
    assert TkRenderer.KEY_BINDINGS["<space>"] == "hard_drop"
    assert TkRenderer.KEY_BINDINGS["<KeyPress-c>"] == "hold"
    assert TkRenderer.KEY_BINDINGS["<KeyPress-r>"] == "restart_stage"
    assert TkRenderer.KEY_BINDINGS["<KeyPress-n>"] == "advance_stage"


def _count_cells(view: GameViewModel, kind: str) -> int:
    return sum(cell.kind == kind for row in view.board_rows for cell in row)


def _active_labels(view: GameViewModel) -> set[str]:
    return {cell.label for row in view.board_rows for cell in row if cell.kind == "active"}
