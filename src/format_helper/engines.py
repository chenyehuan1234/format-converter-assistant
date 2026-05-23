from __future__ import annotations

import logging
import shutil
import subprocess
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path

from PIL import Image
from pypdf import PdfReader

from .models import ConversionJob, MediaKind

LOGGER = logging.getLogger(__name__)


class ConversionError(RuntimeError):
    pass


class EngineAdapter(ABC):
    @abstractmethod
    def can_handle(self, job: ConversionJob) -> bool:
        raise NotImplementedError

    @abstractmethod
    def convert(self, job: ConversionJob) -> None:
        raise NotImplementedError


class ImageEngine(EngineAdapter):
    def can_handle(self, job: ConversionJob) -> bool:
        return job.kind == MediaKind.IMAGE

    def convert(self, job: ConversionJob) -> None:
        job.output_path.parent.mkdir(parents=True, exist_ok=True)
        target = job.preset.target_format.lower()
        with Image.open(job.input_path) as image:
            if target in {"jpg", "jpeg"} and image.mode in {"RGBA", "LA", "P"}:
                background = Image.new("RGB", image.size, "white")
                if image.mode == "P":
                    image = image.convert("RGBA")
                background.paste(image, mask=image.getchannel("A") if "A" in image.getbands() else None)
                image = background
            elif target not in {"png", "webp", "gif", "tiff", "tif"}:
                image = image.convert("RGB")
            save_kwargs: dict[str, int | str] = {}
            if target in {"jpg", "jpeg", "webp"}:
                save_kwargs["quality"] = {"small": 72, "balanced": 86, "high": 95}.get(
                    job.preset.quality, 86
                )
            image.save(job.output_path, **save_kwargs)


class FFmpegEngine(EngineAdapter):
    def __init__(self, ffmpeg_path: str | None = None) -> None:
        self.ffmpeg = ffmpeg_path or shutil.which("ffmpeg") or _imageio_ffmpeg_path()

    def can_handle(self, job: ConversionJob) -> bool:
        return job.kind in {MediaKind.AUDIO, MediaKind.VIDEO}

    def convert(self, job: ConversionJob) -> None:
        if not self.ffmpeg:
            raise ConversionError("FFmpeg 不可用，无法转换音频/视频。")
        job.output_path.parent.mkdir(parents=True, exist_ok=True)
        cmd = [self.ffmpeg, "-y", "-i", str(job.input_path)]
        if job.kind == MediaKind.VIDEO:
            if job.preset.quality == "small":
                cmd += ["-crf", "30"]
            elif job.preset.quality == "high":
                cmd += ["-crf", "18"]
            else:
                cmd += ["-crf", "23"]
        if job.preset.bitrate:
            cmd += ["-b:a", job.preset.bitrate]
        cmd.append(str(job.output_path))
        _run(cmd)


class LibreOfficeEngine(EngineAdapter):
    def __init__(self, soffice_path: str | None = None) -> None:
        self.soffice = soffice_path or shutil.which("soffice")

    def can_handle(self, job: ConversionJob) -> bool:
        return job.kind == MediaKind.DOCUMENT

    def convert(self, job: ConversionJob) -> None:
        if not self.soffice:
            raise ConversionError("LibreOffice 不可用，无法转换 Office 文档。")
        job.output_path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory() as temp_dir:
            cmd = [
                self.soffice,
                "--headless",
                "--convert-to",
                job.preset.target_format,
                "--outdir",
                temp_dir,
                str(job.input_path),
            ]
            _run(cmd)
            generated = next(Path(temp_dir).glob(f"{job.input_path.stem}.*"), None)
            if generated is None:
                raise ConversionError("LibreOffice 未生成输出文件。")
            shutil.move(str(generated), str(job.output_path))


class PdfEngine(EngineAdapter):
    def can_handle(self, job: ConversionJob) -> bool:
        return job.kind == MediaKind.PDF

    def convert(self, job: ConversionJob) -> None:
        target = job.preset.target_format.lower()
        job.output_path.parent.mkdir(parents=True, exist_ok=True)
        if target == "txt":
            reader = PdfReader(str(job.input_path))
            text = "\n\n".join(page.extract_text() or "" for page in reader.pages)
            job.output_path.write_text(text, encoding="utf-8")
            return
        if target in {"png", "jpg", "jpeg"}:
            try:
                import fitz
            except ImportError as exc:
                raise ConversionError("PyMuPDF 不可用，无法将 PDF 转图片。") from exc
            doc = fitz.open(str(job.input_path))
            for index, page in enumerate(doc, start=1):
                pix = page.get_pixmap(dpi=job.preset.dpi or 160)
                output = job.output_path
                if len(doc) > 1:
                    output = job.output_path.with_name(
                        f"{job.output_path.stem}_{index}{job.output_path.suffix}"
                    )
                pix.save(str(output))
            return
        raise ConversionError(f"PDF 暂不支持转换为 {target}。")


class OcrEngine(EngineAdapter):
    def can_handle(self, job: ConversionJob) -> bool:
        return job.kind == MediaKind.OCR

    def convert(self, job: ConversionJob) -> None:
        try:
            from paddleocr import PaddleOCR
        except ImportError as exc:
            raise ConversionError("PaddleOCR 不可用，无法执行 OCR。") from exc
        job.output_path.parent.mkdir(parents=True, exist_ok=True)
        ocr = PaddleOCR(use_angle_cls=True, lang="ch", show_log=False)
        result = ocr.ocr(str(job.input_path), cls=True)
        lines: list[str] = []
        for page in result or []:
            for item in page or []:
                if len(item) >= 2 and item[1]:
                    lines.append(str(item[1][0]))
        job.output_path.write_text("\n".join(lines), encoding="utf-8")


class EngineRegistry:
    def __init__(self, engines: list[EngineAdapter] | None = None) -> None:
        self.engines = engines or [
            ImageEngine(),
            FFmpegEngine(),
            LibreOfficeEngine(),
            PdfEngine(),
            OcrEngine(),
        ]

    def convert(self, job: ConversionJob) -> None:
        for engine in self.engines:
            if engine.can_handle(job):
                engine.convert(job)
                return
        raise ConversionError(f"暂不支持此转换：{job.input_path.suffix} -> {job.preset.target_format}")


def _run(cmd: list[str]) -> None:
    LOGGER.info("Running command: %s", " ".join(cmd))
    completed = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        raise ConversionError((completed.stderr or completed.stdout or "外部命令执行失败").strip())


def _imageio_ffmpeg_path() -> str | None:
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None
