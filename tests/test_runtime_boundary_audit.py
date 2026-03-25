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
        "Product Gaps Visible Today",
        "Startup And Packaging Assumptions",
        "Persistence Gaps",
        "Brittle UI Flow",
        "Content Scaling Risks",
        "ST2 Stabilize App Startup",
        "ST3 Add Player Persistence",
        "ST4 Polish Core UX",
        "ST5 Harden Stage Content Pipeline",
    )

    for phrase in required_phrases:
        assert phrase in text
