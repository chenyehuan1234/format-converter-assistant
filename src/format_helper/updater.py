from __future__ import annotations

import hashlib
import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

import requests

from . import __version__


@dataclass(frozen=True)
class UpdateInfo:
    available: bool
    current_version: str
    latest_version: str = ""
    installer_url: str = ""
    sha256: str = ""
    message: str = ""


class GitHubUpdater:
    def __init__(self, owner: str, repo: str) -> None:
        self.owner = owner
        self.repo = repo

    def check(self) -> UpdateInfo:
        if self.owner in {"", "OWNER"} or self.repo in {"", "REPO"}:
            return UpdateInfo(False, __version__, message="GitHub 发布源尚未配置。")
        url = f"https://api.github.com/repos/{self.owner}/{self.repo}/releases/latest"
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        release = response.json()
        latest = str(release.get("tag_name", "")).lstrip("v")
        if not latest or _version_tuple(latest) <= _version_tuple(__version__):
            return UpdateInfo(False, __version__, latest, message="已经是最新版。")
        asset = self._find_manifest_asset(release)
        if not asset:
            return UpdateInfo(False, __version__, latest, message="未找到 latest.json 更新清单。")
        manifest = requests.get(asset, timeout=15).json()
        installer_url = manifest.get("installer_url", "")
        sha256 = manifest.get("sha256", "")
        return UpdateInfo(True, __version__, latest, installer_url, sha256, "发现新版本。")

    def download_and_install(self, info: UpdateInfo) -> Path:
        if not info.available or not info.installer_url or not info.sha256:
            raise ValueError("更新信息不完整，无法安装。")
        target = Path(tempfile.gettempdir()) / f"FormatConverterAssistantSetup-{info.latest_version}.exe"
        with requests.get(info.installer_url, stream=True, timeout=60) as response:
            response.raise_for_status()
            with target.open("wb") as file:
                for chunk in response.iter_content(chunk_size=1024 * 256):
                    if chunk:
                        file.write(chunk)
        actual = sha256_file(target)
        if actual.lower() != info.sha256.lower():
            target.unlink(missing_ok=True)
            raise ValueError("安装包 SHA256 校验失败，已拒绝安装。")
        subprocess.Popen([str(target), "/S"], close_fds=True)
        os._exit(0)

    @staticmethod
    def _find_manifest_asset(release: dict) -> str:
        for asset in release.get("assets", []):
            if asset.get("name") == "latest.json":
                return asset.get("browser_download_url", "")
        return ""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _version_tuple(version: str) -> tuple[int, ...]:
    parts: list[int] = []
    for part in version.split("."):
        try:
            parts.append(int(part))
        except ValueError:
            parts.append(0)
    return tuple(parts)
