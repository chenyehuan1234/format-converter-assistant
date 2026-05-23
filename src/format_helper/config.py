from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path

from . import __app_name__


def app_data_dir() -> Path:
    root = os.getenv("APPDATA")
    if root:
        base = Path(root)
    else:
        base = Path.home() / ".config"
    path = base / "FormatConverterAssistant"
    path.mkdir(parents=True, exist_ok=True)
    return path


@dataclass
class AppSettings:
    theme: str = "light"
    max_workers: int = 2
    output_mode: str = "source_converted"
    output_dir: str = ""
    github_owner: str = "OWNER"
    github_repo: str = "REPO"
    auto_update: bool = True


class SettingsStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or app_data_dir() / "settings.json"

    def load(self) -> AppSettings:
        if not self.path.exists():
            return AppSettings()
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            valid = {field.name for field in AppSettings.__dataclass_fields__.values()}
            return AppSettings(**{k: v for k, v in data.items() if k in valid})
        except Exception:
            return AppSettings()

    def save(self, settings: AppSettings) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(asdict(settings), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def logs_dir() -> Path:
    path = app_data_dir() / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path


WINDOW_TITLE = __app_name__

