from __future__ import annotations

import sqlite3
from pathlib import Path

from .config import app_data_dir
from .models import ConversionJob


class HistoryStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or app_data_dir() / "history.sqlite3"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path)

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    input_path TEXT NOT NULL,
                    output_path TEXT NOT NULL,
                    target_format TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    status TEXT NOT NULL,
                    error TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    started_at REAL,
                    finished_at REAL,
                    duration_seconds REAL
                )
                """
            )

    def save_job(self, job: ConversionJob) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO jobs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job.id,
                    str(job.input_path),
                    str(job.output_path),
                    job.preset.target_format,
                    job.kind.value,
                    job.status.value,
                    job.error,
                    job.created_at,
                    job.started_at,
                    job.finished_at,
                    job.duration_seconds,
                ),
            )

    def recent(self, limit: int = 100) -> list[dict[str, str]]:
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def clear(self) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM jobs")

