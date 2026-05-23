from pathlib import Path

from format_helper.updater import GitHubUpdater, _version_tuple, sha256_file


def test_version_tuple() -> None:
    assert _version_tuple("1.2.10") > _version_tuple("1.2.3")


def test_sha256_file(tmp_path: Path) -> None:
    path = tmp_path / "x.txt"
    path.write_text("abc", encoding="utf-8")
    assert sha256_file(path) == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"


def test_find_manifest_asset() -> None:
    release = {
        "assets": [
            {"name": "demo.zip", "browser_download_url": "https://example.invalid/demo.zip"},
            {"name": "latest.json", "browser_download_url": "https://example.invalid/latest.json"},
        ]
    }

    assert GitHubUpdater._find_manifest_asset(release) == "https://example.invalid/latest.json"
