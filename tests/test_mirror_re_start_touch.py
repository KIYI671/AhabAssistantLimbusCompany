"""回归测试：镜牢战败重开（Mirror.re_start）在键盘不可用时如何打开暂停浮层。

键盘可用：按 ESC 打开设置浮层。键盘不可用（未授权辅助功能、触摸端等，``supports_key("esc")``
为 False）时没有 ESC 通道，必须点战斗内暂停按钮 ``battle/setting_assets.png``
（与 ``battle.py`` / ``back_init_menu.py`` 中"点设置按钮再点放弃战斗"的配对一致），
否则取不到浮层里的 ``battle/give_up_assets.png``，循环只能空转到 retry 看门狗。
"""

import numpy as np
import pytest

from tasks.mirror import mirror as mirror_module
from tasks.mirror.mirror import Mirror

FORFEIT_CONFIRM = "mirror/road_in_mir/towindow&forfeit_confirm_assets.png"
SETTING_TOUCH = "battle/setting_assets.png"


class LoopDetected(RuntimeError):
    """暂停浮层一直没打开，re_start 在反复空转。"""


class FakeTime:
    """只替换 mirror 模块内的 time，避免真的 sleep。"""

    def __init__(self):
        self.slept = []

    def time(self):
        return 0.0

    def sleep(self, seconds):
        self.slept.append(seconds)


class FakeDevice:
    MAX_ITERATIONS = 20

    def __init__(self, *, supports_keyboard: bool):
        self.supports_keyboard = supports_keyboard
        self.pause_open = False
        self.iterations = 0
        self.setting_clicks = 0
        self.key_presses = []

    def take_screenshot(self):
        self.iterations += 1
        if self.iterations > self.MAX_ITERATIONS:
            raise LoopDetected("暂停浮层未打开，re_start 空转")
        return np.zeros((1080, 1920, 3), dtype=np.uint8)

    def click_element(self, target, *args, **kwargs):
        if target == SETTING_TOUCH:
            self.setting_clicks += 1
            self.pause_open = True
            return True
        if target == FORFEIT_CONFIRM:
            return self.pause_open
        return False

    def supports_key(self, key: str) -> bool:
        return self.supports_keyboard

    def key_press(self, key):
        self.key_presses.append(key)
        if self.supports_keyboard:
            self.pause_open = True


@pytest.fixture
def run_re_start(monkeypatch):
    def _run(*, supports_keyboard: bool):
        device = FakeDevice(supports_keyboard=supports_keyboard)
        monkeypatch.setattr(mirror_module, "auto", device)
        monkeypatch.setattr(mirror_module, "retry", lambda: True)
        monkeypatch.setattr(mirror_module, "time", FakeTime())
        mirror = object.__new__(Mirror)  # 不走 __init__，re_start 只用 start_time
        mirror.start_time = 0.0
        mirror.re_start()
        return device

    return _run


def test_re_start_uses_escape_on_keyboard_device(run_re_start):
    """键盘可用：只按 ESC 打开浮层，不点暂停按钮（Windows 行为不变）。"""
    device = run_re_start(supports_keyboard=True)

    assert device.key_presses == ["esc"]
    assert device.setting_clicks == 0


def test_re_start_clicks_pause_button_on_keyboardless_device(run_re_start):
    """键盘无效：改点战斗内暂停按钮打开浮层，不得空转。"""
    device = run_re_start(supports_keyboard=False)

    assert device.setting_clicks == 1
    assert device.key_presses == []
