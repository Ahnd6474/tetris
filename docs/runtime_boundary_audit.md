# Runtime Boundary Audit

This brief captures the current runtime seams before productization changes land.

## Current Subsystem Boundaries

### Headless Engine

- `src/tetris/engine/pieces.py` contains the real gameplay runtime in `PieceSession`: active piece state, hold logic, collision checks, lock resolution, line clears, and board or layer mutation.
- `src/tetris/engine/loop.py` contains `GameLoop`, which only advances ticks, calls an optional `on_tick`, and asks a renderer to draw.
- `src/tetris/engine/state.py` contains `EngineRuntime` and `EngineState`, which currently hold tick state plus a board spec from `AppConfig`.
- The engine does not import `tkinter`, but it is not fully generic either: `PieceSession` depends directly on `src/tetris/stage/cells.py` helpers for solid-tile and line-clear behavior.

### Stage System

- `src/tetris/stage/data.py` loads immutable `StageDefinition` data from `src/tetris/stage/stages.json` via `StageCatalog.bootstrap()`.
- `src/tetris/stage/runtime.py` owns `StageSession`, which chooses the active stage, instantiates a fresh `PieceSession`, tracks stage status, and handles restart or next-stage activation.
- `src/tetris/stage/objectives.py` evaluates stage completion or failure from the mutable `PieceSession` layers after each lock.
- The stage layer is the source of authored board width and height, piece queues, terrain, objects, and objective definitions.

### Tkinter UI

- `src/tetris/ui/panels.py` is the read-model seam. It translates `StageSession` state into `GameViewModel` and objective panel data for a renderer.
- `src/tetris/ui/renderers.py` defines the renderer and controller protocols plus `NullRenderer` for headless tests.
- `src/tetris/ui/tk_renderer.py` owns widget creation, key bindings, canvas drawing, and the interactive event loop.
- The UI does not mutate gameplay state directly. It dispatches string action names back to the controller.

### App Shell And Entry

- `src/tetris/app_shell.py` contains `TetrisApp`, the integration seam that composes `AppConfig`, `EngineRuntime`, `StageSession`, `GameLoop`, and a renderer.
- `TetrisApp` owns boot and shutdown, gravity timing, action routing, restart, next-stage progression, and the current renderer-facing snapshot.
- `src/tetris/cli.py` is a thin entrypoint that only parses `--headless` and `--frames`, then calls `create_app()`.
- The repository also includes a top-level `tetris/` shim package so `python -m tetris` works from the repo root without installation.

## Cross-Subsystem Seams

- Engine to stage: `StageSession.activate()` creates `PieceSession` with authored board, tile, and object layers, and `PieceSession` calls back into `StageSession.refresh()` through `on_lock`.
- Stage to UI: `build_game_view()` and `build_objective_panel()` read `StageSession` directly, so renderer data is coupled to the session shape instead of a narrower facade.
- App shell to UI: `TetrisApp` exposes `game_view` and accepts plain string actions from `TkRenderer.KEY_BINDINGS`.
- App shell to startup: `create_app()` fills in default renderer and catalog choices implicitly, so startup behavior is mostly convention rather than explicit configuration.

## Product Gaps Visible Today

### Startup And Packaging Assumptions

- `AppConfig` only carries board dimensions, FPS, and `headless`; it does not describe stage source, asset lookup, save paths, or runtime mode selection beyond a boolean.
- `create_app()` always falls back to bundled stages and a default renderer, which makes packaged startup behavior implicit.
- `TkRenderer.open()` assumes `tkinter` and a working display are available and has no player-facing startup error path.
- The repo-root `tetris/` shim is useful for local source execution, but it means source layout and packaged layout are not yet unified behind one authoritative startup path.

### Persistence Gaps

- There is no persistence module, save file schema, or app data location.
- Stage progression, restart state, player settings, and any future unlock data are lost on every shutdown because `StageSession` is rebuilt from defaults on boot.
- Malformed or missing user data is not handled because no durable user data path exists yet.

### Brittle UI Flow

- Boot goes straight into the first playable stage. There is no title flow, continue flow, stage select, pause state, or post-run summary screen.
- `TkRenderer` action dispatch depends on duplicated string literals shared with `TetrisApp.handle_action()`.
- Stage clear and failure feedback are only label text plus buttons; there is no stronger shell-level status or recoverable error presentation.
- Window-close behavior stops the loop, but there is no confirmation or explicit save-before-exit hook.

### Content Scaling Risks

- All authored content currently lives in one `src/tetris/stage/stages.json` file, so stage growth will turn one file into the content bottleneck.
- Adding a new tile, object, or objective requires coordinated edits across `cells.py`, `data.py`, `objectives.py`, `panels.py`, and tests.
- `EngineRuntime.board` still comes from global `AppConfig` defaults while actual playfield dimensions come from stage data, so there is no single authoritative runtime playfield contract.
- Stage validation happens at load time plus tests; there is no separate authoring validation pass or tooling for larger content sets.

## Implementation Targets For Remaining Productization Work

### ST2 Stabilize App Startup

- Make startup explicit in `create_app()` or an equivalent bootstrap path: runtime mode, stage source, asset lookup, and failure handling should be chosen deliberately instead of by hidden defaults.
- Remove or formalize the repo-only startup assumptions so local execution and packaged execution share one predictable initialization story.
- Add a player-visible failure path when `tkinter`, display creation, or bundled content loading fails.

### ST3 Add Player Persistence

- Introduce a small persistence service and schema for progression plus settings.
- Load defaults safely, recover from malformed files, and let the app shell own when user state is read and written.
- Persist at least current or unlocked stage and basic renderer-facing preferences.

### ST4 Polish Core UX

- Move from immediate stage boot into a coherent shell flow with clear start, restart, stage-clear, and failure states.
- Replace brittle stringly action wiring with a more centralized action contract while preserving the current controller boundary.
- Surface stronger status, control guidance, and error feedback inside the shell instead of relying on source knowledge.

### ST5 Harden Stage Content Pipeline

- Establish a scalable stage source layout and validation path instead of growing a single JSON file indefinitely.
- Make the playfield contract explicit so stage dimensions, renderer sizing, and runtime board metadata stay aligned.
- Reduce the number of modules that must change for routine content work by centralizing registries or validation helpers around tiles, objects, and objectives.
