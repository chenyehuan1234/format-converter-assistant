from pathlib import Path

from format_helper.models import MediaKind, detect_kind


def test_detects_ocr_for_image_to_txt() -> None:
    assert detect_kind(Path("scan.png"), "txt") == MediaKind.OCR


def test_detects_video() -> None:
    assert detect_kind(Path("clip.mp4"), "mkv") == MediaKind.VIDEO

