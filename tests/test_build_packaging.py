from __future__ import annotations

import runpy
import sys
import tarfile
from pathlib import Path

import PyInstaller.__main__
import pytest

BUILD_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "build.py"
IS_WINDOWS = sys.platform == "win32"


@pytest.mark.parametrize(
    "github_actions,arguments,packaged",
    [(False, [], False), (False, ["--package"], True), (True, [], True)],
)
def test_build_packages_explicit_requests_and_existing_ci_calls(monkeypatch, tmp_path, github_actions, arguments, packaged):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", [str(BUILD_SCRIPT), "--version", "test", *arguments])
    if github_actions:
        monkeypatch.setenv("GITHUB_ACTIONS", "true")
    else:
        monkeypatch.delenv("GITHUB_ACTIONS", raising=False)

    for name in ("README.md", "LICENSE"):
        (tmp_path / name).write_text(name, encoding="utf-8")
    (tmp_path / "assets" / "config").mkdir(parents=True)
    (tmp_path / "i18n").mkdir()

    def fake_pyinstaller(arguments):
        if arguments[0] == "main.spec":
            app = tmp_path / "dist" / "AALC"
            (app / "_internal").mkdir(parents=True)
            (app / ("AALC.exe" if IS_WINDOWS else "AALC")).write_bytes(b"application")
        else:
            updater = "AALC Updater.exe" if IS_WINDOWS else "AALC-Updater"
            (tmp_path / "dist" / updater).write_bytes(b"updater")

    monkeypatch.setattr(PyInstaller.__main__, "run", fake_pyinstaller)
    # Exercise the real tar archive path without relying on a local 7z installation.
    monkeypatch.setattr("shutil.which", lambda _command: None)

    if packaged:
        runpy.run_path(str(BUILD_SCRIPT), run_name="__main__")
    else:
        with pytest.raises(SystemExit) as result:
            runpy.run_path(str(BUILD_SCRIPT), run_name="__main__")
        assert result.value.code == 0

    app = tmp_path / "dist" / "AALC"
    assert (app / "assets" / "config" / "version.txt").read_text() == "test"
    updater = "AALC Updater.exe" if IS_WINDOWS else "AALC-Updater"
    assert (app / updater).read_bytes() == b"updater"
    archive_name = "AALC_test.tar.gz" if IS_WINDOWS else "AALC_test_linux.tar.gz"
    archive_path = tmp_path / "dist" / archive_name
    assert archive_path.exists() is packaged
    if packaged:
        with tarfile.open(archive_path) as archive:
            assert archive.extractfile("AALC/assets/config/version.txt").read() == b"test"
            assert archive.extractfile(f"AALC/{updater}").read() == b"updater"
