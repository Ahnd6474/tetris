# tetris

Puzzle-driven Tetris prototype with a shared headless engine and `tkinter` UI shell.

## Run

- `python -m tetris` launches the playable `tkinter` UI.
- `python -m tetris --headless --frames 2` runs the deterministic headless path.

## Controls

- `Left` / `Right`: move
- `Up`: rotate
- `Down`: soft drop
- `Space`: hard drop
- `C`: hold
- `R`: restart stage
- `N`: next stage after clearing

## Verified behavior

- Core modules are split into `engine`, `stage`, `ui`, and `app_shell` under `src/tetris`.
- The playable UI path launches through `python -m tetris --frames 1`.
- The UI/CLI integration tests pass with `python -m pytest tests/test_ui_integration.py tests/test_cli.py`.
