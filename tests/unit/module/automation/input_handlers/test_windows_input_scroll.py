import importlib.util
import sys
import types
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[5]


def _module(name, **attributes):
    module = types.ModuleType(name)
    module.__dict__.update(attributes)
    return module


def _load_windows_input_module(monkeypatch):
    class Constants(types.ModuleType):
        def __getattr__(self, name):
            return hash(name)

    class SingletonMeta(type):
        pass

    class AbstractInput:
        pass

    class FakePyAutoGUI(types.ModuleType):
        FAILSAFE = True

        def __getattr__(self, name):
            return lambda *args, **kwargs: None

    stubs = {
        "pyautogui": FakePyAutoGUI("pyautogui"),
        "pyperclip": _module("pyperclip"),
        "win32api": _module("win32api"),
        "win32con": Constants("win32con"),
        "win32gui": _module("win32gui"),
        "pywintypes": _module("pywintypes", error=OSError),
        "module.config": _module("module.config", cfg=types.SimpleNamespace()),
        "module.game_and_screen": _module(
            "module.game_and_screen", screen=types.SimpleNamespace()
        ),
        "module.logger": _module("module.logger", log=types.SimpleNamespace()),
        "utils.singletonmeta": _module(
            "utils.singletonmeta", SingletonMeta=SingletonMeta
        ),
    }
    for name, module in stubs.items():
        monkeypatch.setitem(sys.modules, name, module)

    package = _module(
        "module.automation.input_handlers", AbstractInput=AbstractInput
    )
    package.__path__ = []
    monkeypatch.setitem(sys.modules, package.__name__, package)

    scroll_spec = importlib.util.spec_from_file_location(
        "module.automation.input_handlers.scroll_swipe",
        REPO_ROOT / "module/automation/input_handlers/scroll_swipe.py",
    )
    scroll_module = importlib.util.module_from_spec(scroll_spec)
    monkeypatch.setitem(sys.modules, scroll_spec.name, scroll_module)
    scroll_spec.loader.exec_module(scroll_module)

    input_spec = importlib.util.spec_from_file_location(
        "module.automation.input_handlers.input_under_test",
        REPO_ROOT / "module/automation/input_handlers/input.py",
    )
    input_module = importlib.util.module_from_spec(input_spec)
    monkeypatch.setitem(sys.modules, input_spec.name, input_module)
    input_spec.loader.exec_module(input_module)
    return input_module


@pytest.mark.parametrize("use_post_message", [True, False])
def test_background_scroll_brakes_at_endpoint_before_mouse_up(
    monkeypatch, use_post_message
):
    input_module = _load_windows_input_module(monkeypatch)
    control = object.__new__(input_module.BackgroundInput)
    events = []

    control.use_post_message = use_post_message
    monkeypatch.setattr(
        input_module, "sleep", lambda duration: events.append(("settle", duration))
    )
    control.get_mouse_position = lambda: None
    control.set_mouse_pos = lambda x, y, duration=0: events.append(
        ("move", x, y, duration)
    )
    control.set_active = lambda: events.append(("active",))
    control.mouse_down = lambda x, y: events.append(("down", x, y))
    control.mouse_up = lambda x, y: events.append(("up", x, y))
    control.mouse_swipe_for_scroll(100, 500, dy=-300, duration=0.3)

    assert events[-4:] == [
        ("move", 100.0, 230.0, 0.29),
        ("move", 100, 200, 0.5),
        ("settle", 0.3),
        ("up", 100, 200),
    ]


def test_foreground_scroll_brakes_at_endpoint(monkeypatch):
    input_module = _load_windows_input_module(monkeypatch)
    control = object.__new__(input_module.Input)
    events = []

    monkeypatch.setattr(
        input_module, "sleep", lambda duration: events.append(("settle", duration))
    )
    control.get_mouse_position = lambda: None
    control.pos_offset = lambda x, y: (x, y)
    monkeypatch.setattr(
        input_module.pyautogui,
        "moveTo",
        lambda x, y, duration=0: events.append(("move", x, y, duration)),
    )
    monkeypatch.setattr(
        input_module.pyautogui, "mouseDown", lambda: events.append(("down",))
    )
    monkeypatch.setattr(
        input_module.pyautogui, "mouseUp", lambda: events.append(("up",))
    )
    control.mouse_swipe_for_scroll(100, 500, dy=-300, duration=0.3)

    assert events[-4:] == [
        ("move", 100.0, 230.0, 0.29),
        ("move", 100, 200, 0.5),
        ("settle", 0.3),
        ("up",),
    ]


def test_window_move_scroll_brakes_at_endpoint(monkeypatch):
    input_module = _load_windows_input_module(monkeypatch)
    control = object.__new__(input_module.WindowMoveInput)
    events = []

    monkeypatch.setattr(
        input_module, "sleep", lambda duration: events.append(("settle", duration))
    )
    control._set_window_pos = lambda x, y: events.append(
        ("position", x, y)
    ) or (10, 20)
    control._window_move_to = lambda x, y, duration=0: events.append(
        ("move", x, y, duration)
    )
    control.set_active = lambda: events.append(("active",))
    control.mouse_down = lambda x, y: events.append(("down", x, y))
    control.mouse_up = lambda x, y: events.append(("up", x, y))
    input_module.screen.handle = types.SimpleNamespace(
        set_window_pos=lambda x, y: events.append(("restore", x, y))
    )
    control.mouse_swipe_for_scroll(100, 500, dy=-300, duration=0.3)

    up_index = events.index(("up", 100, 200))
    assert events[up_index - 3 : up_index] == [
        ("move", 100.0, 230.0, 0.29),
        ("move", 100, 200, 0.5),
        ("settle", 0.3),
    ]
    assert events[up_index + 1] == ("restore", 10, 20)
