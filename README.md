# tetris

Bootstrap skeleton for a puzzle-driven Tetris MVP.

## Verified behavior

- Core modules are split into `engine`, `stage`, `ui`, and `app_shell` under `src/tetris`.
- The headless bootstrap and shell boundary smoke tests pass with `python -m pytest tests/test_bootstrap.py tests/test_app_shell.py`.
