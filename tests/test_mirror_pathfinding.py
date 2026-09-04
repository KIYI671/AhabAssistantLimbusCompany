from __future__ import annotations

import importlib
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock


def test_x11_mouse_click_uses_pyautogui_for_move_and_click(monkeypatch) -> None:
    """X11 must use the original pyautogui path instead of split XTEST injection."""

    clicks = []
    fake_pyautogui = ModuleType("pyautogui")
    fake_pyautogui.FAILSAFE = False
    fake_pyautogui.click = lambda *args, **_kwargs: clicks.append(args)
    fake_pyautogui.position = lambda: SimpleNamespace(x=0, y=0)
    fake_pyautogui.moveTo = Mock()
    fake_pyautogui.mouseDown = Mock()
    fake_pyautogui.mouseUp = Mock()
    fake_pyautogui.scroll = Mock()
    fake_pyautogui.press = Mock()
    fake_pyperclip = ModuleType("pyperclip")

    automation_module = ModuleType("module.automation")
    automation_module.__path__ = ["module/automation"]
    config_module = ModuleType("module.config")
    config_module.cfg = SimpleNamespace(set_win_size=1080)
    logger_module = ModuleType("module.logger")
    logger_module.log = SimpleNamespace(
        debug=lambda *_args, **_kwargs: None,
        warning=lambda *_args, **_kwargs: None,
        info=lambda *_args, **_kwargs: None,
    )
    screen_module = ModuleType("module.game_and_screen")
    screen_module.screen = SimpleNamespace(
        handle=SimpleNamespace(rect=lambda _client: (100, 200, 1540, 1280))
    )

    monkeypatch.setitem(sys.modules, "pyautogui", fake_pyautogui)
    monkeypatch.setitem(sys.modules, "pyperclip", fake_pyperclip)
    monkeypatch.setitem(sys.modules, "module.automation", automation_module)
    monkeypatch.setitem(sys.modules, "module.config", config_module)
    monkeypatch.setitem(sys.modules, "module.logger", logger_module)
    monkeypatch.setitem(sys.modules, "module.game_and_screen", screen_module)
    monkeypatch.delitem(sys.modules, "module.automation.input_handlers.linux_input", raising=False)

    monkeypatch.setenv("DISPLAY", ":0")
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    monkeypatch.setenv("XDG_SESSION_TYPE", "x11")

    linux_input = importlib.import_module("module.automation.input_handlers.linux_input")
    handler = object.__new__(linux_input.LinuxInput)
    handler.wait_pause = lambda: None
    xtest_move = Mock()
    monkeypatch.setattr(linux_input, "_abs_move", xtest_move)

    assert handler.mouse_click(10, 20) is True
    assert clicks == [(110, 220)]
    xtest_move.assert_not_called()
