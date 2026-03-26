from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path
import sys

from .app import create_app
from .config import AppConfig, RendererStrategy, RuntimeMode, StageSource, StageSourceKind


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the puzzle-adventure Tetris prototype.")
    parser.add_argument(
        "--runtime-mode",
        choices=[mode.value for mode in RuntimeMode],
        default=None,
        help="Explicitly choose source-tree or installed-data startup rules.",
    )
    parser.add_argument(
        "--renderer",
        choices=[strategy.value for strategy in RendererStrategy],
        default=None,
        help="Select the renderer strategy to bootstrap.",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Shortcut for --renderer null.",
    )
    parser.add_argument(
        "--stage-source",
        choices=[kind.value for kind in StageSourceKind],
        default=None,
        help="Select whether stages come from bundled data or an explicit file.",
    )
    parser.add_argument(
        "--stage-file",
        type=Path,
        default=None,
        help="Path to an external stage JSON file.",
    )
    parser.add_argument(
        "--save-path",
        type=Path,
        default=None,
        help="Path used for app-local save data.",
    )
    parser.add_argument(
        "--frames",
        type=int,
        default=None,
        help="Number of frames to advance before exiting.",
    )
    return parser


def _resolve_renderer_strategy(args: argparse.Namespace, parser: argparse.ArgumentParser) -> RendererStrategy | None:
    if args.headless and args.renderer == RendererStrategy.TK.value:
        parser.error("--headless cannot be combined with --renderer tk")
    if args.headless:
        return RendererStrategy.NULL
    if args.renderer is None:
        return None
    return RendererStrategy(args.renderer)


def _resolve_stage_source(args: argparse.Namespace, parser: argparse.ArgumentParser) -> StageSource | None:
    if args.stage_file is not None:
        if args.stage_source == StageSourceKind.BUNDLED.value:
            parser.error("--stage-file cannot be combined with --stage-source bundled")
        return StageSource.file(args.stage_file)
    if args.stage_source == StageSourceKind.FILE.value:
        parser.error("--stage-source file requires --stage-file")
    if args.stage_source == StageSourceKind.BUNDLED.value:
        return StageSource.bundled()
    return None


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    config = AppConfig.bootstrap(
        runtime_mode=RuntimeMode(args.runtime_mode) if args.runtime_mode is not None else None,
        stage_source=_resolve_stage_source(args, parser),
        save_path=args.save_path,
        renderer_strategy=_resolve_renderer_strategy(args, parser),
    )

    frame_limit = args.frames if args.frames is not None else (1 if config.headless else None)

    app = create_app(config=config)
    try:
        app.run(frame_limit=frame_limit)
    finally:
        app.shutdown()

    if app.startup_failure is not None:
        print(app.startup_failure.message, file=sys.stderr)
        return 1

    return 0
