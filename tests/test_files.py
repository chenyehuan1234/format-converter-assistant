from pathlib import Path

from format_helper.files import scan_inputs, unique_path


def test_scan_inputs_recurses_supported_files(tmp_path: Path) -> None:
    nested = tmp_path / "nested"
    nested.mkdir()
    supported = nested / "a.png"
    unsupported = nested / "a.exe"
    supported.write_bytes(b"x")
    unsupported.write_bytes(b"x")

    assert scan_inputs([tmp_path]) == [supported]


def test_unique_path_adds_suffix(tmp_path: Path) -> None:
    existing = tmp_path / "demo.txt"
    existing.write_text("x")

    assert unique_path(existing) == tmp_path / "demo_1.txt"

