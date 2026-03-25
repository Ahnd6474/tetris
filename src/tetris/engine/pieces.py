from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from itertools import islice
from random import Random
from typing import Callable


type Cell = tuple[int, int]
type BoardRow = list[str | None]
type BoardMatrix = list[BoardRow]
type StageRow = list[object | None]
type StageMatrix = list[StageRow]
type LineClearHook = Callable[["PieceSession", tuple["ClearedRowSnapshot", ...]], None]
type LockHook = Callable[["PieceSession", "LockResult"], None]

TETROMINO_KINDS = ("I", "J", "L", "O", "S", "T", "Z")
TETROMINOES: dict[str, tuple[tuple[Cell, ...], ...]] = {
    "I": (
        ((0, 1), (1, 1), (2, 1), (3, 1)),
        ((2, 0), (2, 1), (2, 2), (2, 3)),
        ((0, 2), (1, 2), (2, 2), (3, 2)),
        ((1, 0), (1, 1), (1, 2), (1, 3)),
    ),
    "J": (
        ((0, 0), (0, 1), (1, 1), (2, 1)),
        ((1, 0), (2, 0), (1, 1), (1, 2)),
        ((0, 1), (1, 1), (2, 1), (2, 2)),
        ((1, 0), (1, 1), (0, 2), (1, 2)),
    ),
    "L": (
        ((2, 0), (0, 1), (1, 1), (2, 1)),
        ((1, 0), (1, 1), (1, 2), (2, 2)),
        ((0, 1), (1, 1), (2, 1), (0, 2)),
        ((0, 0), (1, 0), (1, 1), (1, 2)),
    ),
    "O": (
        ((0, 0), (1, 0), (0, 1), (1, 1)),
        ((0, 0), (1, 0), (0, 1), (1, 1)),
        ((0, 0), (1, 0), (0, 1), (1, 1)),
        ((0, 0), (1, 0), (0, 1), (1, 1)),
    ),
    "S": (
        ((1, 0), (2, 0), (0, 1), (1, 1)),
        ((1, 0), (1, 1), (2, 1), (2, 2)),
        ((1, 1), (2, 1), (0, 2), (1, 2)),
        ((0, 0), (0, 1), (1, 1), (1, 2)),
    ),
    "T": (
        ((1, 0), (0, 1), (1, 1), (2, 1)),
        ((1, 0), (1, 1), (2, 1), (1, 2)),
        ((0, 1), (1, 1), (2, 1), (1, 2)),
        ((1, 0), (0, 1), (1, 1), (1, 2)),
    ),
    "Z": (
        ((0, 0), (1, 0), (1, 1), (2, 1)),
        ((2, 0), (1, 1), (2, 1), (1, 2)),
        ((0, 1), (1, 1), (1, 2), (2, 2)),
        ((1, 0), (0, 1), (1, 1), (0, 2)),
    ),
}


def create_board(width: int, height: int) -> BoardMatrix:
    if width <= 0 or height <= 0:
        raise ValueError("board dimensions must be positive")
    return [[None for _ in range(width)] for _ in range(height)]


def _create_stage_layer(width: int, height: int) -> StageMatrix:
    return [[None for _ in range(width)] for _ in range(height)]


def _validate_kind(kind: str) -> None:
    if kind not in TETROMINOES:
        raise ValueError(f"unknown tetromino kind: {kind}")


def _validate_layer_dimensions(layer: StageMatrix, width: int, height: int, *, name: str) -> None:
    if len(layer) != height or any(len(row) != width for row in layer):
        raise ValueError(f"{name} dimensions do not match the configured playfield")


@dataclass(frozen=True, slots=True)
class ActivePiece:
    kind: str
    rotation: int = 0
    x: int = 0
    y: int = 0

    def __post_init__(self) -> None:
        _validate_kind(self.kind)
        if self.rotation not in range(4):
            raise ValueError("rotation must be between 0 and 3")

    @property
    def cells(self) -> tuple[Cell, ...]:
        return TETROMINOES[self.kind][self.rotation]

    def translated_cells(self) -> tuple[Cell, ...]:
        return tuple((self.x + offset_x, self.y + offset_y) for offset_x, offset_y in self.cells)

    def moved(self, dx: int = 0, dy: int = 0) -> "ActivePiece":
        return ActivePiece(kind=self.kind, rotation=self.rotation, x=self.x + dx, y=self.y + dy)

    def rotated(self, turns: int = 1) -> "ActivePiece":
        return ActivePiece(kind=self.kind, rotation=(self.rotation + turns) % 4, x=self.x, y=self.y)


@dataclass(frozen=True, slots=True)
class ClearedRowSnapshot:
    index: int
    blocks: tuple[str | None, ...]
    tiles: tuple[object | None, ...]
    objects: tuple[object | None, ...]


@dataclass(frozen=True, slots=True)
class LockResult:
    kind: str
    cells: tuple[Cell, ...]
    landing_row: int
    cleared_rows: tuple[int, ...] = ()
    top_out: bool = False
    game_over: bool = False

    @property
    def lines_cleared(self) -> int:
        return len(self.cleared_rows)


def spawn_piece(kind: str, board_width: int) -> ActivePiece:
    _validate_kind(kind)
    spawn_shape = TETROMINOES[kind][0]
    piece_width = max(cell_x for cell_x, _ in spawn_shape) + 1
    top_padding = min(cell_y for _, cell_y in spawn_shape)
    spawn_x = (board_width - piece_width) // 2
    return ActivePiece(kind=kind, x=spawn_x, y=-top_padding)


@dataclass(slots=True)
class PieceBag:
    seed: int | None = None
    initial_queue: tuple[str, ...] = ()
    _upcoming: deque[str] = field(init=False, repr=False)
    _random: Random = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for kind in self.initial_queue:
            _validate_kind(kind)
        self._upcoming = deque(self.initial_queue)
        self._random = Random(self.seed)

    def _refill(self) -> None:
        bag = list(TETROMINO_KINDS)
        self._random.shuffle(bag)
        self._upcoming.extend(bag)

    def _ensure(self, size: int) -> None:
        while len(self._upcoming) < size:
            self._refill()

    def pop(self) -> str:
        self._ensure(1)
        return self._upcoming.popleft()

    def peek(self, size: int) -> tuple[str, ...]:
        if size < 0:
            raise ValueError("size must be >= 0")
        self._ensure(size)
        return tuple(islice(self._upcoming, 0, size))


@dataclass(slots=True)
class PieceSession:
    width: int
    height: int
    bag: PieceBag = field(default_factory=PieceBag)
    next_queue_size: int = 5
    board: BoardMatrix | None = None
    tiles: StageMatrix | None = None
    objects: StageMatrix | None = None
    active: ActivePiece | None = None
    hold_kind: str | None = None
    hold_used: bool = False
    game_over: bool = False
    on_lines_cleared: LineClearHook | None = None
    on_lock: LockHook | None = None
    last_lock_result: LockResult | None = None

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValueError("board dimensions must be positive")
        if self.next_queue_size < 0:
            raise ValueError("next_queue_size must be >= 0")
        if self.board is None:
            self.board = create_board(self.width, self.height)
        elif len(self.board) != self.height or any(len(row) != self.width for row in self.board):
            raise ValueError("board dimensions do not match the configured playfield")
        if self.tiles is None:
            self.tiles = _create_stage_layer(self.width, self.height)
        else:
            _validate_layer_dimensions(self.tiles, self.width, self.height, name="tiles")
        if self.objects is None:
            self.objects = _create_stage_layer(self.width, self.height)
        else:
            _validate_layer_dimensions(self.objects, self.width, self.height, name="objects")
        if self.active is None and not self.game_over:
            self.spawn_next()

    @property
    def next_queue(self) -> tuple[str, ...]:
        return self.bag.peek(self.next_queue_size)

    @property
    def active_cells(self) -> tuple[Cell, ...]:
        if self.active is None:
            return ()
        return self.active.translated_cells()

    def collides(self, piece: ActivePiece) -> bool:
        for cell_x, cell_y in piece.translated_cells():
            if cell_x < 0 or cell_x >= self.width or cell_y >= self.height:
                return True
            if cell_y >= 0 and self.board[cell_y][cell_x] is not None:
                return True
        return False

    def _spawn(self, kind: str) -> bool:
        candidate = spawn_piece(kind, self.width)
        if self.collides(candidate):
            self.active = None
            self.game_over = True
            return False
        self.active = candidate
        return True

    def spawn_next(self) -> bool:
        if self.game_over:
            return False
        return self._spawn(self.bag.pop())

    def move(self, dx: int = 0, dy: int = 0) -> bool:
        if self.active is None or self.game_over:
            return False
        candidate = self.active.moved(dx=dx, dy=dy)
        if self.collides(candidate):
            return False
        self.active = candidate
        return True

    def move_left(self) -> bool:
        return self.move(dx=-1)

    def move_right(self) -> bool:
        return self.move(dx=1)

    def soft_drop(self) -> bool:
        return self.move(dy=1)

    def rotate_clockwise(self) -> bool:
        if self.active is None or self.game_over:
            return False
        candidate = self.active.rotated(1)
        if self.collides(candidate):
            return False
        self.active = candidate
        return True

    def filled_rows(self) -> tuple[int, ...]:
        return tuple(row_index for row_index, row in enumerate(self.board) if all(cell is not None for cell in row))

    def _collapse_rows(self, cleared_rows: tuple[int, ...]) -> None:
        cleared_row_set = set(cleared_rows)
        for layer in (self.board, self.tiles, self.objects):
            remaining_rows = [row.copy() for row_index, row in enumerate(layer) if row_index not in cleared_row_set]
            empty_rows = [[None for _ in range(self.width)] for _ in range(len(cleared_rows))]
            layer[:] = empty_rows + remaining_rows

    def clear_filled_rows(self) -> tuple[int, ...]:
        cleared_rows = self.filled_rows()
        if not cleared_rows:
            return ()

        snapshots = tuple(
            ClearedRowSnapshot(
                index=row_index,
                blocks=tuple(self.board[row_index]),
                tiles=tuple(self.tiles[row_index]),
                objects=tuple(self.objects[row_index]),
            )
            for row_index in cleared_rows
        )
        if self.on_lines_cleared is not None:
            self.on_lines_cleared(self, snapshots)

        self._collapse_rows(cleared_rows)
        return cleared_rows

    def lock_active(self) -> LockResult:
        if self.active is None:
            raise RuntimeError("no active piece to lock")

        piece = self.active
        piece_cells = piece.translated_cells()
        landing_row = max(cell_y for _, cell_y in piece_cells)
        self.active = None
        top_out = False

        for cell_x, cell_y in piece_cells:
            if cell_y < 0:
                top_out = True
                continue
            self.board[cell_y][cell_x] = piece.kind

        cleared_rows = self.clear_filled_rows()
        self.hold_used = False
        if top_out:
            self.game_over = True
        else:
            self.spawn_next()

        result = LockResult(
            kind=piece.kind,
            cells=piece_cells,
            landing_row=landing_row,
            cleared_rows=cleared_rows,
            top_out=top_out,
            game_over=self.game_over,
        )
        self.last_lock_result = result
        if self.on_lock is not None:
            self.on_lock(self, result)
        return result

    def _lock_active(self) -> LockResult:
        return self.lock_active()

    def hard_drop(self) -> int:
        if self.active is None:
            raise RuntimeError("no active piece to drop")

        while self.move(dy=1):
            continue

        return self.lock_active().landing_row

    def hold(self) -> bool:
        if self.active is None or self.game_over or self.hold_used:
            return False

        current_kind = self.active.kind
        held_kind = self.hold_kind
        self.hold_kind = current_kind
        self.hold_used = True

        if held_kind is None:
            self.active = None
            return self.spawn_next()

        return self._spawn(held_kind)
