from __future__ import annotations

import json
import tomllib
from importlib.resources import files
from pathlib import Path

from tetris import AppConfig, create_app
from tetris.actions import ShellState


ROOT = Path(__file__).resolve().parents[1]


def test_release_metadata_points_console_script_at_the_cli_bootstrap() -> None:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert pyproject["project"]["scripts"]["tetris"] == "tetris.cli:main"
    assert pyproject["tool"]["setuptools"]["package-data"]["tetris.stage"] == ["*.json"]


def test_source_and_installed_entrypoints_share_the_same_cli_bootstrap_story() -> None:
    source_entrypoint = (ROOT / "src" / "tetris" / "__main__.py").read_text(encoding="utf-8")
    repo_entrypoint = (ROOT / "tetris" / "__main__.py").read_text(encoding="utf-8")

    assert source_entrypoint == repo_entrypoint
    assert "from .cli import main" in source_entrypoint


def test_bundled_stage_resource_is_available_through_package_data() -> None:
    resource = files("tetris.stage").joinpath("stages.json")

    with resource.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    assert payload["stages"][0]["id"] == "stage-001"


def test_installed_bootstrap_defaults_can_boot_from_bundled_stage_data(tmp_path: Path) -> None:
    package_root = tmp_path / "installed-layout"
    package_root.mkdir()

    app = create_app(
        AppConfig.bootstrap(
            package_root=package_root,
            headless=True,
        )
    )

    try:
        app.boot()

        assert app.config.stage_source.path is None
        assert app.startup_failure is None
        assert app.objective_panel.stage_title == "Key Delivery"
        assert app.game_view.stage_status == ShellState.TITLE.value
    finally:
        app.shutdown()
