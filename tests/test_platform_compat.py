from __future__ import annotations

import os
from unittest.mock import Mock

import module.platform_compat as platform_compat


def test_open_url_uses_linux_desktop_opener(monkeypatch) -> None:
    monkeypatch.setattr(platform_compat, "IS_WINDOWS", False)
    monkeypatch.setattr(platform_compat.sys, "platform", "linux")
    monkeypatch.setattr(
        platform_compat.shutil,
        "which",
        lambda command: "/usr/bin/xdg-open" if command == "xdg-open" else None,
    )
    popen = Mock()
    monkeypatch.setattr(platform_compat.subprocess, "Popen", popen)

    assert platform_compat.open_url("https://example.com") is True
    args, kwargs = popen.call_args
    assert args == (["/usr/bin/xdg-open", "https://example.com"],)
    assert kwargs["stdout"] is platform_compat.subprocess.DEVNULL
    assert kwargs["stderr"] is platform_compat.subprocess.DEVNULL
    assert kwargs["start_new_session"] is True
    assert kwargs["env"] == os.environ


def test_open_url_removes_pyinstaller_library_path(monkeypatch) -> None:
    monkeypatch.setattr(platform_compat, "IS_WINDOWS", False)
    monkeypatch.setattr(platform_compat.sys, "platform", "linux")
    monkeypatch.setattr(platform_compat.sys, "frozen", True, raising=False)
    monkeypatch.setenv("LD_LIBRARY_PATH", "/path/to/aalc/_internal")
    monkeypatch.delenv("LD_LIBRARY_PATH_ORIG", raising=False)
    monkeypatch.setattr(
        platform_compat.shutil,
        "which",
        lambda command: "/usr/bin/xdg-open" if command == "xdg-open" else None,
    )
    popen = Mock()
    monkeypatch.setattr(platform_compat.subprocess, "Popen", popen)

    assert platform_compat.open_url("https://example.com") is True
    assert "LD_LIBRARY_PATH" not in popen.call_args.kwargs["env"]


def test_open_url_returns_false_without_desktop_opener(monkeypatch) -> None:
    monkeypatch.setattr(platform_compat, "IS_WINDOWS", False)
    monkeypatch.setattr(platform_compat.sys, "platform", "linux")
    monkeypatch.setattr(platform_compat.shutil, "which", lambda _command: None)

    assert platform_compat.open_url("https://example.com") is False
