from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from itertools import islice
from random import Random


type Cell = tuple[int, int]
type BoardRow = list[str | None]
type BoardMatrix = list[BoardRow]

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


def _validate_kind(kind: str) -> None:
    if kind not in TETROMINOES:
        raise ValueError(f"unknown tetromino kind: {kind}")


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
    active: ActivePiece | None = None
    hold_kind: str | None = None
    hold_used: bool = False
    game_over: bool = False

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValueError("board dimensions must be positive")
        if self.next_queue_size < 0:
            raise ValueError("next_queue_size must be >= 0")
        if self.board is None:
            self.board = create_board(self.width, self.height)
        elif len(self.board) != self.height or any(len(row) != self.width for row in self.board):
            raise ValueError("board dimensions do not match the configured playfield")
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

    def _lock_active(self) -> None:
        if self.active is None:
            raise RuntimeError("no active piece to lock")

        piece = self.active
        self.active = None

        for cell_x, cell_y in piece.translated_cells():
            if cell_y < 0:
                self.game_over = True
                return
            self.board[cell_y][cell_x] = piece.kind

        self.hold_used = False
        self.spawn_next()

    def hard_drop(self) -> int:
        if self.active is None:
            raise RuntimeError("no active piece to drop")

        while self.move(dy=1):
            continue

        landing_row = max(cell_y for _, cell_y in self.active_cells)
        self._lock_active()
        return landing_row

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
