"""回归测试：返回主界面（back_init_menu）在触摸端的兜底入口。

键盘端最后手段是按 ESC 打开暂停/设置浮层；触摸端（PlayCover/MaaTools 的 ``key_press``
是空实现）原来在这一步完全空转，只能等 ``loop_count`` 耗尽后重启游戏。现在改为点界面上
的设置/返回入口：

- ``mirror/road_in_mir/setting_assets.png``：它在主循环前面的点击被 ``legend_assets.png``
  识别门控，识别抖动时会漏掉，所以留到最后手段里兜底；
- 通行证界面：领取日常/周常奖励后停留的界面，键盘端靠 ESC 退出；它的返回键与
  ``home/back_assets.png`` 不是同一套样式（同屏相似度约 0.37），识别不到，所以检测到
  该界面后直接点左上角的标准返回键槽位。
"""

import pytest

from tasks.base import back_init_menu as back_init_menu_module

MIRROR_SETTING = "mirror/road_in_mir/setting_assets.png"
PASS_TABS = ("pass/pass_missions_assets.png", "pass/weekly_assets.png")
WINDOW = "home/window_assets.png"
MAIL = "home/mail_assets.png"

# 通行证界面里标准返回键槽位（画布 1920x1080 坐标），与 home/back_assets.png 的 mask 一致
BACK_SLOT_BBOX = (60, 24, 164, 93)


class LoopDetected(RuntimeError):
    """界面一直没推进，说明最后手段没有生效。"""


class FakeImageUtils:
    """只提供 back_init_menu 取标准返回键槽位所需的两个接口。"""

    @staticmethod
    def load_image(path):
        return "fake-image"

    @staticmethod
    def get_bbox(image):
        return BACK_SLOT_BBOX


class FakeDevice:
    MAX_ITERATIONS = 20

    def __init__(self, *, supports_keyboard: bool, screen: str = "mirror_legend"):
        self.supports_keyboard = supports_keyboard
        self.screen = screen
        self.model = "clam"
        self.escaped = False
        self.iterations = 0
        self.setting_clicks = 0
        self.pass_back_clicks = 0
        self.mouse_clicks = []
        self.key_presses = []

    def _tick(self):
        self.iterations += 1
        if self.iterations > self.MAX_ITERATIONS:
            raise LoopDetected("界面未推进，back_init_menu 空转")

    def click_element(self, target, *args, **kwargs):
        self._tick()
        if target == MIRROR_SETTING:
            if self.screen != "mirror_legend":
                return False
            self.setting_clicks += 1
            self.escaped = True  # 浮层打开，主界面随后可识别
            return True
        if target == WINDOW:
            return self.escaped
        return False

    def find_element(self, target, *args, **kwargs):
        if target == MAIL:
            return (100, 100) if self.escaped else None
        if target in PASS_TABS and self.screen == "pass":
            return (559, 87)
        return None

    def mouse_click(self, x, y, *args, **kwargs):
        self._tick()
        self.mouse_clicks.append((x, y))
        if self.screen != "pass":
            return False
        self.pass_back_clicks += 1
        self.escaped = True  # 回到主界面，随后可识别
        return True

    def mouse_click_blank(self, *args, **kwargs):
        return True

    def supports_key(self, key: str) -> bool:
        return self.supports_keyboard

    def key_press(self, key):
        self.key_presses.append(key)
        if self.supports_keyboard:
            self.escaped = True  # ESC 打开浮层


@pytest.fixture
def run_back_init_menu(monkeypatch):
    def _run(*, supports_keyboard: bool, screen: str = "mirror_legend"):
        device = FakeDevice(supports_keyboard=supports_keyboard, screen=screen)
        monkeypatch.setattr(back_init_menu_module, "auto", device)
        monkeypatch.setattr(back_init_menu_module, "ImageUtils", FakeImageUtils)
        monkeypatch.setattr(back_init_menu_module, "ensure_simulator_game_started", lambda: False)
        monkeypatch.setattr(back_init_menu_module, "retry", lambda: True)
        monkeypatch.setattr(back_init_menu_module, "update_model_for_retry", lambda *a, **k: None)
        assert back_init_menu_module.back_init_menu() is True
        return device

    return _run


def test_touch_device_clicks_setting_entry_instead_of_escape(run_back_init_menu):
    """键盘无效：最后手段点界面设置入口，不按 ESC，且不死循环。"""
    device = run_back_init_menu(supports_keyboard=False)

    assert device.setting_clicks == 1
    assert device.key_presses == []


def test_touch_device_clicks_pass_back_button(run_back_init_menu):
    """通行证界面（领取奖励后停留的界面）：主循环点左上角标准返回键槽位回到主界面。"""
    device = run_back_init_menu(supports_keyboard=False, screen="pass")

    assert device.pass_back_clicks == 1
    assert device.setting_clicks == 0
    assert device.key_presses == []
    (x, y), = device.mouse_clicks
    assert BACK_SLOT_BBOX[0] <= x <= BACK_SLOT_BBOX[2]
    assert BACK_SLOT_BBOX[1] <= y <= BACK_SLOT_BBOX[3]


def test_keyboard_device_still_uses_escape(run_back_init_menu):
    """键盘可用：最后手段仍按 ESC，不点界面入口（Windows 行为不变）。"""
    device = run_back_init_menu(supports_keyboard=True)

    assert device.key_presses == ["esc"]
    assert device.setting_clicks == 0


def test_keyboard_device_keeps_escape_on_pass_screen(run_back_init_menu):
    """键盘可用：通行证界面同样交给 ESC，不改动 Windows 行为。"""
    device = run_back_init_menu(supports_keyboard=True, screen="pass")

    assert device.key_presses == ["esc"]
    assert device.mouse_clicks == []
