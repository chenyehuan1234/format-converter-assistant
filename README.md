# 格式转换助手

一个 Windows 优先的本地 GUI 格式转换软件。第一版使用 Python 3.12 + PySide6，支持拖拽导入、批量队列、图片/音频/视频/文档/PDF/OCR 转换框架、本地历史、依赖检测和 GitHub Releases 更新检查。

## 快速运行

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev,pdf,ocr]"
python -m format_helper.app
```

如果只想跑核心测试，不安装 GUI/OCR 依赖：

```powershell
pip install -e ".[dev]"
pytest
```

## 外部引擎

应用会检测这些本地引擎：

- FFmpeg：音频、视频转换。
- LibreOffice `soffice`：Office 文档转换。
- PaddleOCR：图片/PDF OCR。
- PyMuPDF：PDF 转图片。

第一版提供检测和清晰错误提示；下载/内置二进制的源配置留在 `src/format_helper/dependencies.py`，方便后续绑定可信下载源。

## 打包

```powershell
pip install -e ".[dev]"
powershell -ExecutionPolicy Bypass -File .\packaging\build.ps1
```

NSIS 安装脚本在 `packaging/installer.nsi`。发布到 GitHub Releases 时，建议同时上传：

- `FormatConverterAssistantSetup-<version>.exe`
- `latest.json`

`latest.json` 示例：

```json
{
  "version": "0.1.1",
  "installer_url": "https://github.com/OWNER/REPO/releases/download/v0.1.1/FormatConverterAssistantSetup-0.1.1.exe",
  "sha256": "..."
}
```

