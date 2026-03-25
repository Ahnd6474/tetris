from __future__ import annotations

import argparse
from collections.abc import Sequence

from .app import create_app


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the Tetris MVP bootstrap app.")
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run without a display backend.",
    )
    parser.add_argument(
        "--frames",
        type=int,
        default=1,
        help="Number of frames to advance before exiting.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    app = create_app(headless=args.headless)
    try:
        app.run(frame_limit=args.frames)
    finally:
        app.shutdown()

    return 0
