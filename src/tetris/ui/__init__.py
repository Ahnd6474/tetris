from .panels import (
    BoardCellModel,
    GameViewModel,
    ObjectivePanelModel,
    RequirementStatusModel,
    build_game_view,
    build_objective_panel,
)
from .renderers import InteractiveRenderer, NullRenderer, Renderer, UIController


def create_default_renderer(*, headless: bool) -> Renderer:
    if headless:
        return NullRenderer()

    from .tk_renderer import TkRenderer

    return TkRenderer()

__all__ = [
    "BoardCellModel",
    "GameViewModel",
    "InteractiveRenderer",
    "NullRenderer",
    "ObjectivePanelModel",
    "Renderer",
    "RequirementStatusModel",
    "UIController",
    "build_game_view",
    "build_objective_panel",
    "create_default_renderer",
]
