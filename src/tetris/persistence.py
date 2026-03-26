from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path


SAVE_SCHEMA_VERSION = 1


@dataclass(frozen=True, slots=True)
class PlayerSettings:
    show_controls: bool = True


@dataclass(frozen=True, slots=True)
class PlayerProgress:
    unlocked_stage_id: str | None = None
    current_stage_id: str | None = None
    last_selected_stage_id: str | None = None


@dataclass(frozen=True, slots=True)
class PlayerSaveData:
    version: int = SAVE_SCHEMA_VERSION
    progress: PlayerProgress = field(default_factory=PlayerProgress)
    settings: PlayerSettings = field(default_factory=PlayerSettings)

    def to_dict(self) -> dict[str, object]:
        return {
            "version": self.version,
            "progress": {
                "unlocked_stage_id": self.progress.unlocked_stage_id,
                "current_stage_id": self.progress.current_stage_id,
                "last_selected_stage_id": self.progress.last_selected_stage_id,
            },
            "settings": {
                "show_controls": self.settings.show_controls,
            },
        }


def _parse_stage_id(value: object) -> str | None:
    if isinstance(value, str) and value:
        return value
    return None


def _parse_settings(payload: object) -> PlayerSettings:
    if not isinstance(payload, Mapping):
        return PlayerSettings()

    show_controls = payload.get("show_controls")
    if not isinstance(show_controls, bool):
        show_controls = PlayerSettings().show_controls
    return PlayerSettings(show_controls=show_controls)


def _parse_progress(payload: object) -> PlayerProgress:
    if not isinstance(payload, Mapping):
        return PlayerProgress()

    return PlayerProgress(
        unlocked_stage_id=_parse_stage_id(payload.get("unlocked_stage_id")),
        current_stage_id=_parse_stage_id(payload.get("current_stage_id")),
        last_selected_stage_id=_parse_stage_id(payload.get("last_selected_stage_id")),
    )


def parse_player_save_data(payload: object) -> PlayerSaveData:
    if not isinstance(payload, Mapping):
        return PlayerSaveData()

    version = payload.get("version", SAVE_SCHEMA_VERSION)
    if not isinstance(version, int) or version != SAVE_SCHEMA_VERSION:
        return PlayerSaveData()

    return PlayerSaveData(
        version=version,
        progress=_parse_progress(payload.get("progress")),
        settings=_parse_settings(payload.get("settings")),
    )


@dataclass(slots=True)
class PlayerSaveStore:
    path: Path

    def load(self) -> PlayerSaveData:
        try:
            with self.path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except (FileNotFoundError, OSError, json.JSONDecodeError, TypeError, ValueError):
            return PlayerSaveData()
        return parse_player_save_data(payload)

    def save(self, data: PlayerSaveData) -> bool:
        temp_path = self.path.with_suffix(f"{self.path.suffix}.tmp")
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with temp_path.open("w", encoding="utf-8") as handle:
                json.dump(data.to_dict(), handle, ensure_ascii=True, indent=2)
            temp_path.replace(self.path)
        except OSError:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass
            return False
        return True
