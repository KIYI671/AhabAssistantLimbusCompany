"""utils/app_data_dir.py：macOS 打包版数据目录的程序文件同步。

关键约定：程序文件随版本刷新，用户数据（配置、日志、镜像同步状态与图片）必须保留。
"""

from __future__ import annotations

import sys
from pathlib import Path

from utils.app_data_dir import prepare_macos_data_dir


def _make_app_dir(tmp_path: Path, version: str) -> Path:
    """造一个最小的程序目录（相当于 AALC.app/Contents/MacOS）。"""
    app_dir = tmp_path / "bundle"
    (app_dir / "assets" / "config").mkdir(parents=True)
    (app_dir / "assets" / "config" / "version.txt").write_text(version, encoding="utf-8")
    (app_dir / "assets" / "config" / "image_resource_state.json").write_text('{"revision": 1}', encoding="utf-8")
    (app_dir / "assets" / "images" / "default").mkdir(parents=True)
    (app_dir / "assets" / "images" / "default" / "start.png").write_text("v1", encoding="utf-8")
    (app_dir / "i18n").mkdir()
    (app_dir / "i18n" / "myapp_en.qm").write_text("qm1", encoding="utf-8")
    (app_dir / "AALC").write_text("exe", encoding="utf-8")
    (app_dir / "LICENSE").write_text("license", encoding="utf-8")
    return app_dir


def _upgrade_app_dir(app_dir: Path, version: str) -> None:
    """模拟换了一份新版本的 AALC.app。"""
    (app_dir / "assets" / "config" / "version.txt").write_text(version, encoding="utf-8")
    (app_dir / "assets" / "images" / "default" / "start.png").write_text("v2", encoding="utf-8")
    (app_dir / "i18n" / "myapp_en.qm").write_text("qm2", encoding="utf-8")


def _make_read_only(app_dir: Path) -> None:
    """把程序目录变成只读（App Translocation 下应用包就是只读的）。"""
    for path in [app_dir, *app_dir.rglob("*")]:
        path.chmod(0o755 if path.is_dir() else 0o644)
    for path in sorted(app_dir.rglob("*"), reverse=True):
        path.chmod(0o555 if path.is_dir() else 0o444)
    app_dir.chmod(0o555)


def _upgrade_read_only_app_dir(app_dir: Path, version: str) -> None:
    """在只读的程序目录里升级版本（先放开写权限，改完恢复只读）。"""
    for path in [app_dir, *app_dir.rglob("*")]:
        path.chmod(0o755 if path.is_dir() else 0o644)
    _upgrade_app_dir(app_dir, version)
    _make_read_only(app_dir)


def test_first_run_creates_data_dir_with_program_files(tmp_path: Path) -> None:
    app_dir = _make_app_dir(tmp_path, "1.0.0")
    data_dir = tmp_path / "data"

    assert prepare_macos_data_dir(app_dir, data_dir) == data_dir

    assert (data_dir / "LICENSE").read_text(encoding="utf-8") == "license"
    assert (data_dir / "i18n" / "myapp_en.qm").read_text(encoding="utf-8") == "qm1"
    assert (data_dir / "assets" / "images" / "default" / "start.png").read_text(encoding="utf-8") == "v1"


def test_new_version_refreshes_program_files_and_keeps_user_data(tmp_path: Path) -> None:
    app_dir = _make_app_dir(tmp_path, "1.0.0")
    data_dir = tmp_path / "data"
    prepare_macos_data_dir(app_dir, data_dir)

    # 运行时产生的用户数据
    (data_dir / "config.yaml").write_text("my teams", encoding="utf-8")
    (data_dir / "logs").mkdir()
    (data_dir / "logs" / "debugLog.log").write_text("runtime log", encoding="utf-8")
    # 镜像同步留下的额外图片与同步状态
    (data_dir / "assets" / "images" / "default" / "synced.png").write_text("synced", encoding="utf-8")
    (data_dir / "assets" / "config" / "image_resource_state.json").write_text('{"revision": 2}', encoding="utf-8")

    _upgrade_app_dir(app_dir, "1.1.0")
    prepare_macos_data_dir(app_dir, data_dir)

    # 程序文件被新版本覆盖
    assert (data_dir / "assets" / "config" / "version.txt").read_text(encoding="utf-8") == "1.1.0"
    assert (data_dir / "assets" / "images" / "default" / "start.png").read_text(encoding="utf-8") == "v2"
    assert (data_dir / "i18n" / "myapp_en.qm").read_text(encoding="utf-8") == "qm2"
    # 用户数据保留：配置、日志、同步状态，以及同步下来的额外图片
    assert (data_dir / "config.yaml").read_text(encoding="utf-8") == "my teams"
    assert (data_dir / "logs" / "debugLog.log").read_text(encoding="utf-8") == "runtime log"
    assert (data_dir / "assets" / "config" / "image_resource_state.json").read_text(encoding="utf-8") == (
        '{"revision": 2}'
    )
    assert (data_dir / "assets" / "images" / "default" / "synced.png").read_text(encoding="utf-8") == "synced"


def test_same_version_leaves_data_dir_untouched(tmp_path: Path) -> None:
    app_dir = _make_app_dir(tmp_path, "1.0.0")
    data_dir = tmp_path / "data"
    prepare_macos_data_dir(app_dir, data_dir)
    (data_dir / "assets" / "images" / "default" / "start.png").write_text("patched", encoding="utf-8")

    prepare_macos_data_dir(app_dir, data_dir)

    assert (data_dir / "assets" / "images" / "default" / "start.png").read_text(encoding="utf-8") == "patched"


def test_running_executable_is_not_copied(tmp_path: Path, monkeypatch) -> None:
    app_dir = _make_app_dir(tmp_path, "1.0.0")
    data_dir = tmp_path / "data"
    monkeypatch.setattr(sys, "executable", str(app_dir / "AALC"))

    prepare_macos_data_dir(app_dir, data_dir)

    assert not (data_dir / "AALC").exists()
    assert (data_dir / "LICENSE").is_file()


def test_bundle_without_version_file_still_seeds_data_dir(tmp_path: Path) -> None:
    app_dir = _make_app_dir(tmp_path, "1.0.0")
    (app_dir / "assets" / "config" / "version.txt").unlink()
    data_dir = tmp_path / "data"

    prepare_macos_data_dir(app_dir, data_dir)

    assert (data_dir / "LICENSE").read_text(encoding="utf-8") == "license"
    assert (data_dir / "assets" / "images" / "default" / "start.png").is_file()


def test_read_only_app_dir_stays_syncable(tmp_path: Path) -> None:
    """程序目录只读时，同步出来的权限位不能挡住下一次同步，也不能把数据目录变成只读。"""
    app_dir = _make_app_dir(tmp_path, "1.0.0")
    data_dir = tmp_path / "data"
    _make_read_only(app_dir)

    prepare_macos_data_dir(app_dir, data_dir)
    _upgrade_read_only_app_dir(app_dir, "1.1.0")
    prepare_macos_data_dir(app_dir, data_dir)

    assert (data_dir / "assets" / "config" / "version.txt").read_text(encoding="utf-8") == "1.1.0"
    assert (data_dir / "assets" / "images" / "default" / "start.png").read_text(encoding="utf-8") == "v2"
    # 镜像同步要往 assets/images 里写新文件，数据目录里的目录必须是可写的
    (data_dir / "assets" / "images" / "default" / "synced.png").write_text("synced", encoding="utf-8")
