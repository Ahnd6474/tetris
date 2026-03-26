# tetris

Stage-based puzzle Tetris prototype with a shared headless engine and a `tkinter` UI shell.

## Project Structure

- `src/tetris/engine`: falling-piece rules, bag generation, lock/clear handling, and game loop state.
- `src/tetris/stage`: JSON-backed stage data, tile/object parsing, and objective evaluation.
- `src/tetris/ui`: renderer-facing view models plus the `tkinter` renderer.
- `src/tetris/app_shell.py`: the app controller that connects the engine, stage session, inputs, restart, and stage progression.
- `tests`: engine, stage, UI, and end-to-end tutorial playthrough coverage.

## Run Locally

Use Python 3.12+ from the repository root.

- `python -m tetris` launches the playable `tkinter` build.
- `python -m tetris --headless --frames 30` runs the deterministic headless path.
- `python -m pip install .` installs the packaged build and exposes the same CLI as `tetris`.
- `tetris --headless --frames 30` runs the installed build through the same bootstrap path.
- `python -m pytest` runs the test suite.

## Startup And Save Paths

Both source execution (`python -m tetris`) and installed execution (`tetris`) enter the same CLI bootstrap in `tetris.cli:main`. That bootstrap resolves runtime mode, renderer strategy, stage source, and save path through `AppConfig.bootstrap(...)` before creating the app shell.

- Source-tree defaults:
  - stage source: `src/tetris/stage/stages.json`
  - save path: `.local/save.json`
- Installed defaults:
  - stage source: bundled package data at `tetris.stage:stages.json`
  - save path on Windows: `%LOCALAPPDATA%\\tetris\\save.json`
  - fallback save path when `LOCALAPPDATA` is unset: `~/.local/state/tetris/save.json`
- Override switches:
  - `--runtime-mode {source,installed}`
  - `--renderer {tk,null}` or `--headless`
  - `--stage-source {bundled,file}` with `--stage-file PATH`
  - `--save-path PATH`

## Controls

- `Left` / `Right`: move
- `Up`: rotate
- `Down`: soft drop
- `Space`: hard drop
- `C`: hold
- `R`: restart stage
- `N`: next stage after clearing

## Stage Data

Bundled stages ship from `src/tetris/stage/stages.json`. External content can also be loaded from a standalone JSON file or from a catalog directory passed through `--stage-file`.

Each stage definition is data-driven:

- `piece_queue` seeds the deterministic opening sequence.
- `board` stores pre-placed blocks.
- `tiles` stores persistent terrain such as doors, rocks, walls, and ice.
- `objects` stores mission objects such as keys and gems.
- `objective` declares the requirement set shown in the UI and checked after each lock.

The first five bundled stages are tutorial-style and verified by automated playthrough tests:

- key to bottom
- key to door
- clear ice
- collect gems
- mixed objective

## Extending The Game

To add a new bundled stage, append another entry in `src/tetris/stage/stages.json` with matching `board_width`, `board_height`, `piece_queue`, `board`, `tiles`, and `objects` rows.

To author an external stage pack as a directory, create a `catalog.json` manifest:

```json
{
  "stages": ["stage-001.json", "stage-002.json"]
}
```

Each listed file should contain one stage mapping with the same schema used by the bundled catalog.

To add a new tile or stage object type:

- define the runtime cell in `src/tetris/stage/cells.py`
- teach the JSON loader how to parse its token in `src/tetris/stage/data.py`
- surface it in the board view in `src/tetris/ui/panels.py`

To add a new objective type:

- add the requirement kind and evaluation rule in `src/tetris/stage/objectives.py`
- reference the new objective kind from stage JSON
- add UI labeling in `src/tetris/ui/panels.py`
