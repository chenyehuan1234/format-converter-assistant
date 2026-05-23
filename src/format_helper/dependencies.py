from __future__ import annotations

import importlib.util
import shutil
from dataclasses import dataclass
from pathlib import Path

from .config import app_data_dir


@dataclass(frozen=True)
class DependencyStatus:
    name: str
    available: bool
    detail: str
    path: str = ""


class DependencyManager:
    def __init__(self, tools_dir: Path | None = None) -> None:
        self.tools_dir = tools_dir or app_data_dir() / "tools"
        self.tools_dir.mkdir(parents=True, exist_ok=True)

    def all_statuses(self) -> list[DependencyStatus]:
        return [
            self.ffmpeg_status(),
            self.libreoffice_status(),
            self.paddleocr_status(),
            self.pymupdf_status(),
        ]

    def ffmpeg_status(self) -> DependencyStatus:
        return self._exe_status("FFmpeg", "ffmpeg")

    def libreoffice_status(self) -> DependencyStatus:
        return self._exe_status("LibreOffice", "soffice")

    def paddleocr_status(self) -> DependencyStatus:
        return self._module_status("PaddleOCR", "paddleocr")

    def pymupdf_status(self) -> DependencyStatus:
        return self._module_status("PyMuPDF", "fitz")

    def _exe_status(self, name: str, exe: str) -> DependencyStatus:
        bundled = next(self.tools_dir.rglob(f"{exe}.exe"), None) if self.tools_dir.exists() else None
        found = str(bundled) if bundled else shutil.which(exe)
        if found:
            return DependencyStatus(name, True, "可用", found)
        return DependencyStatus(name, False, "未找到，请在首次运行向导中准备或手动安装")

    def _module_status(self, name: str, module: str) -> DependencyStatus:
        spec = importlib.util.find_spec(module)
        if spec is not None:
            return DependencyStatus(name, True, "可用")
        return DependencyStatus(name, False, "Python 模块未安装")

    def prepare_missing(self) -> list[str]:
        messages: list[str] = []
        for status in self.all_statuses():
            if not status.available:
                messages.append(f"{status.name}: {status.detail}")
        if messages:
            messages.append("自动下载源尚未配置；请先安装缺失组件或在依赖管理器中配置可信下载源。")
        return messages or ["所有依赖已经可用。"]

