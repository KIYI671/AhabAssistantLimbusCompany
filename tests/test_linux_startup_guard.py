from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

from PIL import Image

from module.automation import screenshot as screenshot_module
from module.automation.input_handlers import linux_input
from module.game_and_screen.x11_handle import X11Handle


def _set_linux_window(monkeypatch, rect: tuple[int, int, int, int]) -> None:
    handle = SimpleNamespace(
        rect=Mock(return_value=rect),
        bring_window_into_view=Mock(),
    )
    monkeypatch.setattr(screenshot_module.screen, "handle", handle)
    monkeypatch.setattr(linux_input.screen, "handle", handle)


def test_linux_screenshot_returns_none_without_valid_window(monkeypatch) -> None:
    _set_linux_window(monkeypatch, (0, 0, 0, 0))
    monkeypatch.setattr(screenshot_module, "IS_WINDOWS", False)

    capture = Mock(side_effect=AssertionError("截图不应在无窗口时执行"))
    monkeypatch.setattr(screenshot_module.ScreenShot, "take_screenshot_x11", capture)

    assert screenshot_module.ScreenShot.take_screenshot() is None
    capture.assert_not_called()


def test_linux_screenshot_returns_none_for_empty_startup_frame(monkeypatch) -> None:
    _set_linux_window(monkeypatch, (100, 100, 1540, 1180))
    monkeypatch.setattr(screenshot_module, "IS_WINDOWS", False)
    monkeypatch.setattr(
        screenshot_module.ScreenShot,
        "take_screenshot_x11",
        Mock(return_value=Image.new("L", (1440, 1080), 0)),
    )

    assert screenshot_module.ScreenShot.take_screenshot() is None


def test_linux_blank_click_is_skipped_without_window(monkeypatch) -> None:
    _set_linux_window(monkeypatch, (0, 0, 0, 0))
    handler = object.__new__(linux_input.LinuxInput)
    handler.wait_pause = lambda: None
    click = Mock()
    monkeypatch.setattr(linux_input.pyautogui, "click", click)

    assert handler.mouse_click_blank() is False
    click.assert_not_called()


def test_linux_blank_click_is_skipped_when_pointer_move_fails(monkeypatch) -> None:
    _set_linux_window(monkeypatch, (100, 100, 1540, 1180))
    handler = object.__new__(linux_input.LinuxInput)
    handler.wait_pause = lambda: None
    monkeypatch.setattr(linux_input, "_use_pyautogui_mouse", lambda: False)
    monkeypatch.setattr(linux_input, "_abs_move", Mock(return_value=False))
    click = Mock()
    monkeypatch.setattr(linux_input, "_left_click", click)

    assert handler.mouse_click_blank() is False
    click.assert_not_called()


def test_linux_window_match_does_not_accept_aalc_title() -> None:
    expected = X11Handle._normalize_window_name("LimbusCompany")

    assert X11Handle._normalize_window_name("Limbus Company") == expected
    assert X11Handle._normalize_window_name("Ahab Assistant Limbus Company - DEFAULT VERSION") != expected
    assert X11Handle._normalize_window_name("Mofusigil/AhabAssistantLimbusCompany: AALC") != expected


def test_linux_window_lookup_ignores_aalc_window() -> None:
    handle = object.__new__(X11Handle)
    handle._hwnd = 0
    handle._enum_windows_list = []
    handle._enum_windows = lambda: [
        {
            "wid": 101,
            "cls": "AALC.AALC",
            "title": "Ahab Assistant Limbus Company - DEFAULT VERSION",
            "depth": 1,
        },
        {
            "wid": 102,
            "cls": "chromium.Chromium",
            "title": "Mofusigil/AhabAssistantLimbusCompany: AALC",
            "depth": 1,
        },
    ]

    assert X11Handle.init_handle(handle, "LimbusCompany") == 0


def test_linux_init_game_does_not_start_steam_twice(monkeypatch) -> None:
    from tasks.base import script_task_scheme

    game = SimpleNamespace(start_game=Mock())
    screen = SimpleNamespace(init_handle=Mock(return_value=True), set_win=Mock())
    auto = SimpleNamespace(init_input=Mock())
    cfg = SimpleNamespace(simulator=False, set_windows=False)

    monkeypatch.setattr(script_task_scheme, "IS_LINUX", True)
    monkeypatch.setattr(script_task_scheme, "game_process", game)
    monkeypatch.setattr(script_task_scheme, "screen", screen)
    monkeypatch.setattr(script_task_scheme, "auto", auto)
    monkeypatch.setattr(script_task_scheme, "cfg", cfg)

    script_task_scheme.init_game()

    game.start_game.assert_not_called()
    screen.init_handle.assert_called_once_with()
