from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AppConfig:
    board_width: int = 10
    board_height: int = 20
    target_fps: int = 60
    headless: bool = False
