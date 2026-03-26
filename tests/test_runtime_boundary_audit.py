from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUDIT_BRIEF = ROOT / "docs" / "runtime_boundary_audit.md"


def test_runtime_boundary_audit_brief_tracks_current_seams_and_targets() -> None:
    assert AUDIT_BRIEF.is_file()

    text = AUDIT_BRIEF.read_text(encoding="utf-8")

    required_phrases = (
        "src/tetris/engine/pieces.py",
        "src/tetris/stage/runtime.py",
        "src/tetris/ui/tk_renderer.py",
        "src/tetris/app_shell.py",
        "Current Subsystem Boundaries",
        "Bootstrap, Persistence, And Entry",
        "Regression Coverage",
        "tests/test_bootstrap.py",
        "tests/test_app_shell.py",
        "tests/test_player_persistence.py",
        "tests/test_stage_loader.py",
    )

    for phrase in required_phrases:
        assert phrase in text
