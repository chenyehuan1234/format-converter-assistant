from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from time import time


class JobStatus(str, Enum):
    PENDING = "等待中"
    RUNNING = "转换中"
    SUCCESS = "成功"
    FAILED = "失败"
    CANCELED = "已取消"


class MediaKind(str, Enum):
    IMAGE = "图片"
    AUDIO = "音频"
    VIDEO = "视频"
    DOCUMENT = "文档"
    PDF = "PDF"
    OCR = "OCR"
    UNKNOWN = "未知"


@dataclass
class ConversionPreset:
    target_format: str
    quality: str = "balanced"
    resize: str = ""
    dpi: int | None = None
    bitrate: str = ""
    extra: dict[str, str] = field(default_factory=dict)


@dataclass
class ConversionJob:
    input_path: Path
    preset: ConversionPreset
    output_path: Path
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    kind: MediaKind = MediaKind.UNKNOWN
    status: JobStatus = JobStatus.PENDING
    progress: int = 0
    error: str = ""
    created_at: float = field(default_factory=time)
    started_at: float | None = None
    finished_at: float | None = None

    @property
    def duration_seconds(self) -> float | None:
        if self.started_at is None or self.finished_at is None:
            return None
        return max(0.0, self.finished_at - self.started_at)


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff", ".gif"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".aac", ".flac", ".ogg", ".m4a"}
VIDEO_EXTENSIONS = {".mp4", ".mkv", ".mov", ".webm", ".avi"}
DOCUMENT_EXTENSIONS = {".docx", ".doc", ".xlsx", ".xls", ".pptx", ".ppt", ".odt", ".ods", ".odp"}
PDF_EXTENSIONS = {".pdf"}
SUPPORTED_EXTENSIONS = (
    IMAGE_EXTENSIONS | AUDIO_EXTENSIONS | VIDEO_EXTENSIONS | DOCUMENT_EXTENSIONS | PDF_EXTENSIONS
)


def detect_kind(path: Path, target_format: str | None = None) -> MediaKind:
    suffix = path.suffix.lower()
    if target_format == "txt" and suffix in IMAGE_EXTENSIONS | PDF_EXTENSIONS:
        return MediaKind.OCR
    if suffix in IMAGE_EXTENSIONS:
        return MediaKind.IMAGE
    if suffix in AUDIO_EXTENSIONS:
        return MediaKind.AUDIO
    if suffix in VIDEO_EXTENSIONS:
        return MediaKind.VIDEO
    if suffix in DOCUMENT_EXTENSIONS:
        return MediaKind.DOCUMENT
    if suffix in PDF_EXTENSIONS:
        return MediaKind.PDF
    return MediaKind.UNKNOWN

