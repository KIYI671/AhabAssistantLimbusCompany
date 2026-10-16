"""
updater 纯逻辑单元测试

只覆盖无副作用、可跨平台运行的部分：
- parse_updater_args: 兼容旧版 ``<file>`` / ``--apply-update <file>`` 及新增 flag
- UpdateProgressWindow: 禁用状态必须完全无副作用（不建线程、不触 Win32）
- 增量清单路径安全校验（_normalize_manifest_path）回归
"""

from __future__ import annotations

import os
import threading

import pytest

from updater import UpdateManifestError, UpdateProgressWindow, Updater, parse_updater_args

_ARCHIVE_ROOT = os.path.normpath("C:/temp/update_temp/AALC")


def test_parse_plain_file_name():
    args = parse_updater_args(["AALC.7z"])
    assert args.file_name == "AALC.7z"
    assert args.apply_mode is False
    assert args.parent_pid is None
    assert args.no_progress_ui is False


def test_parse_apply_update_form():
    args = parse_updater_args(["--apply-update", "AALC.7z"])
    assert args.file_name == "AALC.7z"
    assert args.apply_mode is True


def test_parse_extra_flags_any_position():
    args = parse_updater_args(["--parent-pid", "12345", "AALC.7z", "--no-progress-ui"])
    assert args.file_name == "AALC.7z"
    assert args.parent_pid == 12345
    assert args.no_progress_ui is True


def test_parse_invalid_parent_pid_is_ignored():
    args = parse_updater_args(["--parent-pid", "not-a-number", "AALC.7z"])
    assert args.parent_pid is None


def test_parse_empty_argv():
    args = parse_updater_args([])
    assert args.file_name is None
    assert args.apply_mode is False


def test_progress_window_disabled_has_no_side_effect():
    window = UpdateProgressWindow(enabled=False)
    assert window.enabled is False
    window.start()
    window.update(stage="x", value=1, maximum=2)
    window.close()
    assert window._thread is None


def test_progress_window_disabled_on_non_windows(monkeypatch):
    import updater

    monkeypatch.setattr(updater.os, "name", "posix")
    window = UpdateProgressWindow(enabled=True)
    assert window.enabled is False
    window.start()
    assert window._thread is None


def _make_updater_for_manifest_check() -> Updater:
    """绕过 __init__ 的目录创建副作用，仅装配路径校验所需字段。"""
    instance = Updater.__new__(Updater)
    instance.extract_folder_path = _ARCHIVE_ROOT
    instance.cover_folder_path = os.path.normpath("C:/install-root")
    return instance


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("AALC/AALC.exe", "AALC.exe"),
        ("AALC.exe", "AALC.exe"),
        ("AALC/module/a.py", os.path.join("module", "a.py")),
    ],
)
def test_normalize_manifest_path_strips_archive_root(raw, expected):
    instance = _make_updater_for_manifest_check()
    assert instance._normalize_manifest_path(raw) == expected


@pytest.mark.parametrize(
    "raw",
    ["", "/abs/path", "C:/abs/path", "../escape", "ok/../../escape", "bad\x00name"],
)
def test_normalize_manifest_path_rejects_illegal(raw):
    instance = _make_updater_for_manifest_check()
    with pytest.raises(UpdateManifestError):
        instance._normalize_manifest_path(raw)


def test_update_thread_safe_smoke():
    """update 的共享状态在多线程写入下不应抛异常（禁用态走早退分支）。"""
    window = UpdateProgressWindow(enabled=False)
    errors = []

    def worker():
        try:
            for i in range(100):
                window.update(value=i)
        except Exception as exc:  # pragma: no cover
            errors.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert errors == []
