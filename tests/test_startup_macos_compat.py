"""启动链路必须在 macOS 上可用（不依赖 Win32 扩展）。

线上问题：应用在 macOS 上直接启动失败，报
    ModuleNotFoundError: No module named 'win32gui'

原因：module/game_and_screen/game.py 裸导入 win32gui，而它位于启动链路上
（main → app.my_app → app.farming_interface → app.base_combination →
 module.update.check_update → utils.utils → module.automation → ... →
 module.game_and_screen）。只要这一处导入失败，整个应用就起不来。

修复：win32gui 改为可选导入；没有 Win32 接口时按进程名判断游戏是否存活，
并跳过仅 Windows 存在的 os.startfile。
"""

import importlib
import sys

import pytest

# 启动链路中会触发模块加载的入口
STARTUP_CHAIN = [
    "module.game_and_screen.game",
    "module.game_and_screen",
    "module.automation",
    "app.base_combination",
]


@pytest.mark.parametrize("module_name", STARTUP_CHAIN)
def test_startup_modules_import_without_win32(module_name):
    """这些模块必须能在没有 pywin32 的环境导入。"""
    module = importlib.import_module(module_name)
    assert module is not None


def test_game_module_tolerates_missing_win32gui():
    """win32gui 缺失时应降级为 None，而不是让导入崩溃。"""
    game_module = importlib.import_module("module.game_and_screen.game")
    # 非 Windows 上应为 None；Windows 上为真实模块。两者都不应抛异常。
    assert hasattr(game_module, "win32gui")


@pytest.mark.skipif(sys.platform == "win32", reason="仅在非 Windows 上校验降级行为")
def test_check_game_alive_falls_back_to_process_name():
    """没有窗口接口时，按进程名判断即可，不应抛异常。"""
    from module.logger import log

    game_module = importlib.import_module("module.game_and_screen.game")
    game = game_module.Game(logger=log)

    # 用一个必然不存在的进程名，确认走的是"进程名"分支而不是崩溃
    game.process_name = "__no_such_process_for_test__"
    assert game.check_game_alive() is False


@pytest.mark.skipif(sys.platform == "win32", reason="os.startfile 仅 Windows 存在")
def test_missing_startfile_does_not_crash_start_game():
    """start_game 在没有 os.startfile 的平台上不应抛异常。"""
    from unittest.mock import patch

    from module.logger import log

    game_module = importlib.import_module("module.game_and_screen.game")
    game = game_module.Game(logger=log)

    with patch.object(game, "check_game_alive", return_value=False), \
         patch.object(game_module, "sleep"), \
         patch.object(game_module.webbrowser, "open", return_value=True):
        assert game.start_game() is True
