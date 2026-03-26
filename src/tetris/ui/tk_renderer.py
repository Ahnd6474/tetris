from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from ..actions import ACTION_LABELS, AppAction
from ..engine import EngineState, GameLoop
from .panels import BoardCellModel, GameViewModel
from .renderers import UIController

if TYPE_CHECKING:
    import tkinter as tk

CELL_FILLS = {
    "empty": "#111111",
    "active": "#f4f1de",
    "block": "#e07a5f",
    "wall": "#3d405b",
    "rock": "#7f5539",
    "ice": "#6ec6ff",
    "cracked-ice": "#9fd8ff",
    "door": "#f2cc8f",
    "key": "#ffd166",
    "gem": "#81b29a",
}

PIECE_FILLS = {
    "I": "#4cc9f0",
    "J": "#4361ee",
    "L": "#f77f00",
    "O": "#ffca3a",
    "S": "#80ed99",
    "T": "#c77dff",
    "Z": "#ff595e",
}


@dataclass(slots=True)
class TkRenderer:
    title: str = "Puzzle Tetris"
    cell_size: int = 32
    controller: UIController | None = field(default=None, init=False, repr=False)
    is_open: bool = field(default=False, init=False)
    _tk: Any = field(default=None, init=False, repr=False)
    _root: Any = field(default=None, init=False, repr=False)
    _canvas: Any = field(default=None, init=False, repr=False)
    _stage_label: Any = field(default=None, init=False, repr=False)
    _objective_label: Any = field(default=None, init=False, repr=False)
    _message_label: Any = field(default=None, init=False, repr=False)
    _hold_label: Any = field(default=None, init=False, repr=False)
    _queue_label: Any = field(default=None, init=False, repr=False)
    _requirements_label: Any = field(default=None, init=False, repr=False)
    _controls_label: Any = field(default=None, init=False, repr=False)
    _progress_label: Any = field(default=None, init=False, repr=False)
    _start_button: Any = field(default=None, init=False, repr=False)
    _pause_button: Any = field(default=None, init=False, repr=False)
    _restart_button: Any = field(default=None, init=False, repr=False)
    _next_button: Any = field(default=None, init=False, repr=False)
    _loop: GameLoop | None = field(default=None, init=False, repr=False)
    _frames: int = field(default=0, init=False, repr=False)

    KEY_BINDINGS = {
        "<Return>": AppAction.START,
        "<KP_Enter>": AppAction.START,
        "<Escape>": AppAction.PAUSE,
        "<KeyPress-p>": AppAction.PAUSE,
        "<KeyPress-P>": AppAction.PAUSE,
        "<Left>": AppAction.MOVE_LEFT,
        "<Right>": AppAction.MOVE_RIGHT,
        "<Up>": AppAction.ROTATE_CLOCKWISE,
        "<Down>": AppAction.SOFT_DROP,
        "<space>": AppAction.HARD_DROP,
        "<KeyPress-c>": AppAction.HOLD,
        "<KeyPress-C>": AppAction.HOLD,
        "<KeyPress-r>": AppAction.RESTART_STAGE,
        "<KeyPress-R>": AppAction.RESTART_STAGE,
        "<KeyPress-n>": AppAction.NEXT_STAGE,
        "<KeyPress-N>": AppAction.NEXT_STAGE,
    }

    def bind(self, controller: UIController) -> None:
        self.controller = controller

    def open(self) -> None:
        if self.is_open:
            return

        import tkinter as tk

        self._tk = tk
        root = tk.Tk()
        root.title(self.title)
        root.configure(bg="#1f1f1f")
        root.protocol("WM_DELETE_WINDOW", self._request_close)

        shell = tk.Frame(root, bg="#1f1f1f", padx=16, pady=16)
        shell.pack(fill=tk.BOTH, expand=True)

        board_frame = tk.Frame(shell, bg="#1f1f1f")
        board_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=False)

        panel = tk.Frame(shell, bg="#1f1f1f", padx=16)
        panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._stage_label = tk.Label(
            panel,
            text="",
            anchor="w",
            justify=tk.LEFT,
            bg="#1f1f1f",
            fg="#f4f1de",
            font=("Consolas", 15, "bold"),
        )
        self._stage_label.pack(fill=tk.X, pady=(0, 8))

        self._objective_label = tk.Label(
            panel,
            text="",
            anchor="w",
            justify=tk.LEFT,
            wraplength=260,
            bg="#1f1f1f",
            fg="#f2cc8f",
            font=("Consolas", 11),
        )
        self._objective_label.pack(fill=tk.X, pady=(0, 8))

        self._message_label = tk.Label(
            panel,
            text="",
            anchor="w",
            justify=tk.LEFT,
            wraplength=260,
            bg="#1f1f1f",
            fg="#81b29a",
            font=("Consolas", 10),
        )
        self._message_label.pack(fill=tk.X, pady=(0, 12))

        self._hold_label = tk.Label(
            panel,
            text="",
            anchor="w",
            justify=tk.LEFT,
            bg="#1f1f1f",
            fg="#f4f1de",
            font=("Consolas", 11, "bold"),
        )
        self._hold_label.pack(fill=tk.X, pady=(0, 8))

        self._queue_label = tk.Label(
            panel,
            text="",
            anchor="w",
            justify=tk.LEFT,
            bg="#1f1f1f",
            fg="#f4f1de",
            font=("Consolas", 11),
        )
        self._queue_label.pack(fill=tk.X, pady=(0, 8))

        self._requirements_label = tk.Label(
            panel,
            text="",
            anchor="w",
            justify=tk.LEFT,
            bg="#1f1f1f",
            fg="#f4f1de",
            font=("Consolas", 10),
        )
        self._requirements_label.pack(fill=tk.X, pady=(0, 8))

        self._controls_label = tk.Label(
            panel,
            text="",
            anchor="w",
            justify=tk.LEFT,
            bg="#1f1f1f",
            fg="#d9d9d9",
            font=("Consolas", 10),
        )
        self._controls_label.pack(fill=tk.X, pady=(0, 8))

        self._progress_label = tk.Label(
            panel,
            text="",
            anchor="w",
            justify=tk.LEFT,
            bg="#1f1f1f",
            fg="#d9d9d9",
            font=("Consolas", 10),
        )
        self._progress_label.pack(fill=tk.X, pady=(0, 12))

        controls = tk.Frame(panel, bg="#1f1f1f")
        controls.pack(fill=tk.X)

        self._start_button = tk.Button(
            controls,
            text="Start (Enter)",
            command=lambda: self._dispatch(AppAction.START),
            width=14,
        )
        self._start_button.pack(side=tk.LEFT, padx=(0, 8))
        self._pause_button = tk.Button(
            controls,
            text="Pause (Esc)",
            command=lambda: self._dispatch(AppAction.PAUSE),
            width=14,
        )
        self._pause_button.pack(side=tk.LEFT, padx=(0, 8))
        self._restart_button = tk.Button(
            controls,
            text="Restart (R)",
            command=lambda: self._dispatch(AppAction.RESTART_STAGE),
            width=14,
        )
        self._restart_button.pack(side=tk.LEFT, padx=(0, 8))
        self._next_button = tk.Button(
            controls,
            text="Next Stage (N)",
            command=lambda: self._dispatch(AppAction.NEXT_STAGE),
            width=14,
        )
        self._next_button.pack(side=tk.LEFT, padx=(0, 8))
        tk.Button(
            controls,
            text="Quit",
            command=self._request_close,
            width=8,
        ).pack(side=tk.LEFT)

        self._canvas = tk.Canvas(
            board_frame,
            width=self.cell_size * 10,
            height=self.cell_size * 20,
            highlightthickness=0,
            bg="#111111",
        )
        self._canvas.pack()

        for event_name, action in self.KEY_BINDINGS.items():
            root.bind(event_name, lambda _event, bound_action=action: self._dispatch(bound_action))

        self._root = root
        self.is_open = True

    def render(self, state: EngineState) -> None:
        if not self.is_open or self._root is None or self.controller is None:
            raise RuntimeError("renderer must be opened and bound before rendering")

        view = self.controller.game_view
        self._root.title(f"{self.title} - {view.stage_label}: {view.stage_title}")
        self._stage_label.configure(text=f"{view.stage_label}  {view.stage_title}  [{view.stage_status}]")
        self._objective_label.configure(text=f"Objective: {view.objective_summary}")
        self._message_label.configure(text=view.status_message)
        self._hold_label.configure(text=f"Hold: {view.hold_kind or '-'}")
        self._queue_label.configure(text="Next:\n" + ("\n".join(view.next_queue) if view.next_queue else "-"))
        self._requirements_label.configure(text=self._format_requirements(view))
        self._controls_label.configure(text=self._format_actions(view))
        self._progress_label.configure(text=self._format_progress(view))
        self._configure_action_button(self._start_button, view, AppAction.START, fallback="Start")
        self._configure_action_button(self._pause_button, view, AppAction.PAUSE)
        self._configure_action_button(self._restart_button, view, AppAction.RESTART_STAGE)
        self._configure_action_button(self._next_button, view, AppAction.NEXT_STAGE)
        self._draw_board(view)

    def run_loop(self, game_loop: GameLoop, frame_limit: int | None = None) -> int:
        if not self.is_open or self._root is None:
            raise RuntimeError("renderer must be opened before entering the UI loop")

        self._loop = game_loop
        self._frames = 0
        interval_ms = max(1, int(1000 / max(1, game_loop.config.target_fps)))

        def step() -> None:
            if not self.is_open or self._root is None or self._loop is None:
                return
            if not game_loop.state.running:
                self._root.quit()
                return

            game_loop.tick()
            self._frames += 1

            if frame_limit is not None and self._frames >= frame_limit:
                game_loop.stop()
                self._root.quit()
                return

            self._root.after(interval_ms, step)

        self._root.after(0, step)
        self._root.mainloop()
        frames = self._frames
        self._loop = None
        return frames

    def close(self) -> None:
        self.is_open = False
        self._loop = None
        if self._root is None:
            return

        root = self._root
        self._root = None
        try:
            root.quit()
        except Exception:
            pass
        try:
            root.destroy()
        except Exception:
            pass

    def _dispatch(self, action: AppAction | str) -> None:
        if self.controller is None:
            return
        self.controller.handle_action(action)

    def _request_close(self) -> None:
        if self.controller is not None:
            self.controller.stop()
        if self._root is not None:
            self._root.quit()

    def _draw_board(self, view: GameViewModel) -> None:
        if self._canvas is None:
            return

        width = max(1, view.board_width) * self.cell_size
        height = max(1, view.board_height) * self.cell_size
        self._canvas.configure(width=width, height=height)
        self._canvas.delete("all")

        for row_index, row in enumerate(view.board_rows):
            for column_index, cell in enumerate(row):
                x0 = column_index * self.cell_size
                y0 = row_index * self.cell_size
                x1 = x0 + self.cell_size
                y1 = y0 + self.cell_size
                fill = self._cell_fill(cell)
                self._canvas.create_rectangle(x0, y0, x1, y1, fill=fill, outline="#2a2a2a", width=1)
                if cell.label:
                    self._canvas.create_text(
                        x0 + self.cell_size / 2,
                        y0 + self.cell_size / 2,
                        text=cell.label,
                        fill="#111111" if cell.kind in {"door", "key", "gem", "active"} else "#f4f1de",
                        font=("Consolas", max(9, self.cell_size // 3), "bold"),
                    )

    def _cell_fill(self, cell: BoardCellModel) -> str:
        if cell.kind in {"active", "block"} and cell.label in PIECE_FILLS:
            return PIECE_FILLS[cell.label]
        return CELL_FILLS.get(cell.kind, "#111111")

    def _format_requirements(self, view: GameViewModel) -> str:
        if not view.requirements:
            return "Requirements:\n-"
        lines = [f"[{'x' if requirement.completed else ' '}] {requirement.label}" for requirement in view.requirements]
        return "Requirements:\n" + "\n".join(lines)

    def _format_progress(self, view: GameViewModel) -> str:
        if not view.progress_lines:
            return "Status:\n-"
        return "Status:\n" + "\n".join(view.progress_lines)

    def _format_actions(self, view: GameViewModel) -> str:
        if not view.actions:
            return "Controls:\n-"
        lines = []
        for action in view.actions:
            label = action.label
            if action.shortcut:
                label = f"{label} ({action.shortcut})"
            lines.append(label)
        return "Controls:\n" + "\n".join(lines)

    def _configure_action_button(
        self,
        button: Any,
        view: GameViewModel,
        action: AppAction,
        *,
        fallback: str | None = None,
    ) -> None:
        if button is None or self._tk is None:
            return

        action_model = view.action_for(action)
        label = action_model.label if action_model is not None else (fallback or ACTION_LABELS[action])
        if action_model is not None and action_model.shortcut:
            label = f"{label} ({action_model.shortcut})"
        button.configure(
            text=label,
            state=self._tk.NORMAL if action_model is not None and action_model.enabled else self._tk.DISABLED,
        )
