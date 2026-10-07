"""没有 Win32 窗口接口的平台（macOS/Linux）上，窗口管理入口必须直接跳过。

macOS 走 PlayCover 时没有可操作的 Win32 窗口，而自动战斗小工具会无条件调用
screen.set_win() / screen.reset_win()：入口不做平台判断就会抛 AttributeError，
在日志里留下 "窗口设置错误" / "重置窗口失败" 的报错（2026-09-19 debugLog 实测）。
"""

import importlib
import logging

import pytest

screen_package = importlib.import_module("module.game_and_screen")
screen_module = importlib.import_module("module.game_and_screen.screen")


@pytest.fixture
def screen_without_win32(monkeypatch):
    """模拟 macOS/Linux：win32 模块为 None、_HAS_WIN32 为 False。"""
    monkeypatch.setattr(screen_module, "_HAS_WIN32", False)
    for name in ("win32api", "win32con", "win32gui"):
        monkeypatch.setattr(screen_module, name, None)
    return screen_package.screen


def test_窗口管理入口在无win32平台上静默跳过(screen_without_win32, caplog):
    with caplog.at_level(logging.ERROR, logger="AALC"):
        screen_without_win32.set_win()
        reset_result = screen_without_win32.reset_win()

    assert [record.getMessage() for record in caplog.records] == []
    # 没有窗口样式需要恢复，视为已处理完成
    assert reset_result is True
