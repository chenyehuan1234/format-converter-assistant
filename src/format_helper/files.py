from __future__ import annotations

from pathlib import Path

from .models import SUPPORTED_EXTENSIONS


def scan_inputs(paths: list[Path], recursive: bool = True) -> list[Path]:
    files: list[Path] = []
    for path in paths:
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
            files.append(path)
        elif path.is_dir():
            iterator = path.rglob("*") if recursive else path.glob("*")
            files.extend(p for p in iterator if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS)
    return sorted(dict.fromkeys(files))


def default_output_path(input_path: Path, target_format: str, output_dir: Path | None = None) -> Path:
    directory = output_dir or input_path.parent / "converted"
    directory.mkdir(parents=True, exist_ok=True)
    return unique_path(directory / f"{input_path.stem}.{target_format.lstrip('.').lower()}")


def unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    parent = path.parent
    index = 1
    while True:
        candidate = parent / f"{stem}_{index}{suffix}"
        if not candidate.exists():
            return candidate
        index += 1
