# Runtime Boundary Audit

This brief reflects the verified runtime seams for the current runnable release prototype.

## Current Subsystem Boundaries

### Headless Engine

- `src/tetris/engine/pieces.py` owns piece state, collision checks, lock resolution, hold rules, and board mutation.
- `src/tetris/engine/loop.py` owns frame ticks and delegates rendering plus shell callbacks.
- `src/tetris/engine/state.py` keeps runtime tick state and the active `BoardSpec`.
- The active playfield size is synchronized from authored stage dimensions by `TetrisApp`, not from a separate global board default once a stage catalog is available.

### Stage System

- `src/tetris/stage/data.py` defines the content-source contract for bundled package data, standalone JSON files, and directory catalogs with `catalog.json`.
- `StageCatalog.from_source(...)` performs the validation pass and raises `StageValidationError` with aggregated stage-local issues before activation.
- `src/tetris/stage/runtime.py` owns `StageSession`, stage activation, restart, next-stage progression, and the authoritative current stage identifier.
- `src/tetris/stage/objectives.py` evaluates clear and failure conditions from the mutable gameplay layers after each lock.

### UI And Shell

- `src/tetris/ui/panels.py` translates `StageSession` plus shell state into renderer-facing view models.
- `src/tetris/ui/renderers.py` defines the renderer protocol and ships `NullRenderer` for headless tests and fallback startup recovery.
- `src/tetris/ui/tk_renderer.py` owns the local `tkinter` window, bindings, and event loop.
- `src/tetris/actions.py` centralizes shell states and action identifiers so the renderer and controller do not share duplicated string literals.

### Bootstrap, Persistence, And Entry

- `src/tetris/cli.py` is the authoritative CLI bootstrap for both `python -m tetris` and the installed `tetris` console script.
- `src/tetris/config.py` resolves runtime mode, renderer strategy, stage source, and save path explicitly through `AppConfig.bootstrap(...)`.
- `src/tetris/app_shell.py` owns the app-shell boundary that joins bootstrap assets, shell-state transitions, save recovery, and stage-dimension synchronization.
- Source-tree defaults resolve stages from `src/tetris/stage/stages.json` and saves from `.local/save.json`.
- Installed defaults resolve stages from bundled package data and saves from `%LOCALAPPDATA%\\tetris\\save.json`, falling back to `~/.local/state/tetris/save.json` when `LOCALAPPDATA` is unset.
- `src/tetris/persistence.py` owns the JSON save schema for unlocked or current stage and player settings, and malformed or missing files fall back to defaults.
- The repo-root `tetris/` shim only exists so `python -m tetris` works from the source tree; both source and installed runs end up in the same CLI bootstrap.

## Regression Coverage

- `tests/test_bootstrap.py` covers explicit bootstrap choices, source vs installed defaults, source-tree module startup, and controlled startup-failure states.
- `tests/test_app_shell.py` covers shell-state transitions, renderer fallback behavior, and stage-dimension synchronization.
- `tests/test_player_persistence.py` covers malformed-save recovery, immediate settings writes, and persisted progression across restarts.
- `tests/test_stage_loader.py` covers bundled content loading, directory catalogs, and aggregated content-validation errors.
