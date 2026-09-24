"""回归测试：镜牢键盘寻路在触摸端（PlayCover/MaaTools）必须回退为点击寻路。

``cfg.mirror_keyboard_navigation`` / ``cfg.mirror_keyboard_simple_pathfinding`` 是显式的
键盘模式开关，但触摸端的 ``key_press`` 是空实现 —— 直接走键盘分支会原地空转
（方向键送不进游戏），因此要按输入能力判断并回退到既有的点击寻路。
"""

from types import SimpleNamespace

import pytest

from tasks.mirror import search_road as search_road_module
from tasks.mirror.search_road import MirrorMap

ENTER = "mirror/road_in_mir/enter_assets.png"
BUS = "mirror/mybus_default_distance.png"
BUS_POSITION = (1000.0, 700.0)


class FakeDevice:
    def __init__(self, *, supports_keyboard: bool, keyboard_keys: frozenset[str] | None = None):
        self.supports_keyboard = supports_keyboard
        self.keyboard_keys = keyboard_keys
        self.key_presses = []
        self.clicks = []
        self.mouse_to_blank_calls = 0

    def supports_key(self, key: str) -> bool:
        return self.supports_keyboard and (self.keyboard_keys is None or key in self.keyboard_keys)

    def find_element(self, target, *args, **kwargs):
        if target == BUS:
            return BUS_POSITION
        return None

    def click_element(self, target, *args, **kwargs):
        return target == ENTER

    def mouse_click(self, x, y, *args, **kwargs):
        self.clicks.append((x, y))
        return True

    def key_press(self, key):
        self.key_presses.append(key)

    def mouse_to_blank(self, *args, **kwargs):
        self.mouse_to_blank_calls += 1


@pytest.fixture
def env(monkeypatch):
    def _setup(
        *,
        supports_keyboard: bool,
        keyboard_navigation: bool = True,
        keyboard_keys: frozenset[str] | None = None,
    ):
        device = FakeDevice(supports_keyboard=supports_keyboard, keyboard_keys=keyboard_keys)
        monkeypatch.setattr(search_road_module, "auto", device)
        monkeypatch.setattr(search_road_module, "sleep", lambda *_: None)
        monkeypatch.setattr(
            search_road_module,
            "cfg",
            SimpleNamespace(mirror_keyboard_navigation=keyboard_navigation, set_win_size=1080),
        )
        monkeypatch.setattr(search_road_module, "_keyboardless_warned", False, raising=False)
        return device

    return _setup


def test_enter_next_node_uses_arrow_keys_on_keyboard_device(env):
    """键盘可用：与原来一致按方向键选节点。"""
    device = env(supports_keyboard=True)

    assert MirrorMap().enter_next_node("M") is True
    assert device.key_presses == ["right"]
    assert device.clicks == []


def test_enter_next_node_falls_back_to_click_on_keyboardless_device(env):
    """键盘无效：不按方向键，回退到点击寻路。"""
    device = env(supports_keyboard=False)

    assert MirrorMap().enter_next_node("M") is True
    assert device.key_presses == []
    assert len(device.clicks) == 1


def test_simple_keyboard_search_refuses_keyboardless_device(env):
    """键盘无效：简单键盘寻路直接拒绝，不按方向键（调用方回退常规寻路）。"""
    device = env(supports_keyboard=False)

    assert search_road_module.search_road_simple_keyboard() is False
    assert device.key_presses == []
    assert device.mouse_to_blank_calls == 0


def test_simple_keyboard_search_works_on_keyboard_device(env):
    """键盘可用：简单键盘寻路仍按↑并进入节点。"""
    device = env(supports_keyboard=True)

    assert search_road_module.search_road_simple_keyboard() is True
    assert device.key_presses == ["up"]
    assert device.mouse_to_blank_calls == 1


def test_enter_next_node_uses_click_path_when_keyboard_navigation_disabled(env):
    """未开启键盘寻路：仍是点击寻路，且不产生回退警告路径的按键。"""
    device = env(supports_keyboard=False, keyboard_navigation=False)

    assert MirrorMap().enter_next_node("M") is True
    assert device.key_presses == []
    assert len(device.clicks) == 1


PLAYCOVER_KEYS = frozenset({"enter", "return", "p", "esc"})


def test_enter_next_node_falls_back_on_device_without_arrow_keys(env):
    """只送得到 Enter/P/ESC 的设备（PlayCover）：方向键送不进，仍回退到点击寻路。"""
    device = env(supports_keyboard=True, keyboard_keys=PLAYCOVER_KEYS)

    assert MirrorMap().enter_next_node("M") is True
    assert device.key_presses == []
    assert len(device.clicks) == 1


def test_simple_keyboard_search_refuses_device_without_arrow_keys(env):
    """只送得到 Enter/P/ESC 的设备（PlayCover）：简单键盘寻路同样拒绝，不按方向键。"""
    device = env(supports_keyboard=True, keyboard_keys=PLAYCOVER_KEYS)

    assert search_road_module.search_road_simple_keyboard() is False
    assert device.key_presses == []
    assert device.mouse_to_blank_calls == 0
