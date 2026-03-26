from __future__ import annotations

from dataclasses import dataclass

from ..actions import ActionModel
from ..stage import (
    OBJECTIVE_CLEAR_ICE,
    OBJECTIVE_COLLECT_GEMS,
    ObjectiveEvaluation,
    StageSession,
    describe_object,
    describe_tile,
    objective_label,
)


@dataclass(frozen=True, slots=True)
class ObjectivePanelModel:
    stage_title: str
    objective_summary: str
    stage_status: str


@dataclass(frozen=True, slots=True)
class RequirementStatusModel:
    label: str
    completed: bool


@dataclass(frozen=True, slots=True)
class BoardCellModel:
    kind: str
    label: str


@dataclass(frozen=True, slots=True)
class GameViewModel:
    stage_label: str
    stage_title: str
    objective_summary: str
    stage_status: str
    status_message: str
    hold_kind: str | None
    next_queue: tuple[str, ...]
    requirements: tuple[RequirementStatusModel, ...]
    progress_lines: tuple[str, ...]
    board_rows: tuple[tuple[BoardCellModel, ...], ...]
    can_advance: bool
    actions: tuple[ActionModel, ...] = ()

    @property
    def board_width(self) -> int:
        if not self.board_rows:
            return 0
        return len(self.board_rows[0])

    @property
    def board_height(self) -> int:
        return len(self.board_rows)

    def action_for(self, target: object) -> ActionModel | None:
        for action in self.actions:
            if action.action == target:
                return action
        return None


def build_objective_panel(session: StageSession, *, stage_status: str | None = None) -> ObjectivePanelModel:
    stage = session.current_stage
    return ObjectivePanelModel(
        stage_title=stage.title,
        objective_summary=stage.objective.summary,
        stage_status=stage_status or session.state.status,
    )


def build_game_view(
    session: StageSession,
    *,
    stage_status: str | None = None,
    status_message: str | None = None,
    actions: tuple[ActionModel, ...] = (),
) -> GameViewModel:
    stage = session.current_stage
    piece_session = session.piece_session
    evaluation = session.evaluation
    total_stages = len(session.catalog.stages)
    current_index = next(
        (
            stage_index
            for stage_index, catalog_stage in enumerate(session.catalog.stages, start=1)
            if catalog_stage.identifier == stage.identifier
        ),
        1,
    )

    if piece_session is None:
        board = stage.create_board()
        tiles = stage.create_tiles()
        objects = stage.create_objects()
        active_cells: dict[tuple[int, int], str] = {}
        hold_kind = None
        next_queue = stage.piece_queue[:5]
    else:
        board = piece_session.board
        tiles = piece_session.tiles
        objects = piece_session.objects
        active_cells = {
            (cell_x, cell_y): piece_session.active.kind
            for cell_x, cell_y in piece_session.active_cells
            if 0 <= cell_x < piece_session.width and 0 <= cell_y < piece_session.height
        }
        hold_kind = piece_session.hold_kind
        next_queue = piece_session.next_queue

    board_rows = tuple(
        tuple(
            _build_cell(
                tile=tiles[row_index][column_index],
                block=board[row_index][column_index],
                obj=objects[row_index][column_index],
                active_kind=active_cells.get((column_index, row_index)),
            )
            for column_index in range(stage.board_width)
        )
        for row_index in range(stage.board_height)
    )

    can_advance = session.state.status == "cleared" and session.catalog.next_after(stage.identifier) is not None
    return GameViewModel(
        stage_label=f"Stage {current_index}/{total_stages}",
        stage_title=stage.title,
        objective_summary=stage.objective.summary,
        stage_status=stage_status or session.state.status,
        status_message=status_message or _build_status_message(session, can_advance=can_advance),
        hold_kind=hold_kind,
        next_queue=next_queue,
        requirements=_build_requirement_models(session),
        progress_lines=_build_progress_lines(stage.board_height, evaluation),
        board_rows=board_rows,
        can_advance=can_advance,
        actions=actions,
    )


def _build_cell(
    *,
    tile: object | None,
    block: str | None,
    obj: object | None,
    active_kind: str | None,
) -> BoardCellModel:
    if active_kind is not None:
        return BoardCellModel(kind="active", label=active_kind)
    object_presentation = describe_object(obj)
    if object_presentation is not None:
        return BoardCellModel(kind=object_presentation.kind, label=object_presentation.label)
    if block is not None:
        return BoardCellModel(kind="block", label=str(block))
    tile_presentation = describe_tile(tile)
    if tile_presentation is not None:
        return BoardCellModel(kind=tile_presentation.kind, label=tile_presentation.label)
    return BoardCellModel(kind="empty", label="")


def _build_status_message(session: StageSession, *, can_advance: bool) -> str:
    status = session.state.status
    if status == "cleared":
        if can_advance:
            return "Stage cleared. Press N or Next Stage."
        return "Final stage cleared. Press R to replay."
    if status == "failed":
        return "Stage failed. Press R or Restart."
    return "Arrows move, Up rotates, Down soft drops, Space hard drops, C holds."


def _build_requirement_models(session: StageSession) -> tuple[RequirementStatusModel, ...]:
    evaluation = session.evaluation
    stage = session.current_stage
    completed_by_kind = {result.kind: result.completed for result in evaluation.results} if evaluation else {}
    return tuple(
        RequirementStatusModel(
            label=objective_label(requirement.kind),
            completed=completed_by_kind.get(requirement.kind, False),
        )
        for requirement in stage.objective.requirements
    )


def _build_progress_lines(stage_height: int, evaluation: ObjectiveEvaluation | None) -> tuple[str, ...]:
    if evaluation is None:
        return ()

    lines: list[str] = []
    if evaluation.key_positions:
        lowest_key_row = max(row_index for _, row_index in evaluation.key_positions) + 1
        lines.append(f"Key row: {lowest_key_row}/{stage_height}")
        lines.append(f"Key on door: {'yes' if evaluation.key_on_goal else 'no'}")
    if evaluation.remaining_ice or any(result.kind == OBJECTIVE_CLEAR_ICE for result in evaluation.results):
        lines.append(f"Ice remaining: {evaluation.remaining_ice}")
    if evaluation.remaining_gems or any(result.kind == OBJECTIVE_COLLECT_GEMS for result in evaluation.results):
        lines.append(f"Gems remaining: {evaluation.remaining_gems}")
    return tuple(lines)
