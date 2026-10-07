"""回归测试：守备（第一回合全员防御/小指良连续守备）在两种设备上如何开始回合。

- 键盘可用：只按 P+Enter，不得点鼠标 —— 界面误点 / 胜率自动选择会把手动守备覆盖掉。
- 键盘不可用（PlayCover/MaaTools 的 ``key_press`` 是空实现）：改用触摸点技能条右端的
  圆形开始按钮（位置以 ``battle/gear_right.png`` 为基准），点不动才退化为胜率自动选择，
  否则会停在技能选择界面反复执行同一套守备操作（无限循环）。

坐标取自实机（1920x1080 画布）实测：gear_right(1258,823)、开始按钮(1290,850)。
"""

import sys

import numpy as np
import pytest

from module.config import cfg
from tasks.battle.battle import Battle

battle_module = sys.modules["tasks.battle.battle"]

GEAR_LEFT = (514, 812)
GEAR_RIGHT = (1258, 823)
MORE_INFORMATION = (1595, 59)
PAUSE = (1768, 62)
WIN_RATE_CARD = (1351, 846)
LEGEND = (1822, 175)
ROUND_BUTTON = (1290, 850)  # 实测：点这里能开始回合
WIN_LABEL = (1453, 827)  # 实测：OCR 到的 "Rate" 文字中心（按钮在其左侧 -163，1080 画布）
DAMAGE_LABEL = (1453, 878)  # 实测：OCR 到的 "Damage" 文字中心
SKILL_BAND = (900, 1060, 380, 1310)  # 技能条上点选技能的位置范围 (y1, y2, x1, x2)


class LoopDetected(RuntimeError):
    """技能选择界面被反复处理，说明回合一直没能开始。"""


class VirtualClock:
    """把 sleep/操作耗时变成虚拟时间，复现“按完键到暂停按钮出现”的延迟。"""

    def __init__(self) -> None:
        self.now = 0.0

    def sleep(self, seconds=0.0) -> None:
        self.now += max(0.0, float(seconds or 0))


class FakeInputHandler:
    def __init__(self, supports_keyboard: bool) -> None:
        self.supports_keyboard = supports_keyboard

    def supports_key(self, key: str) -> bool:
        return self.supports_keyboard


def _win_rate_click_point() -> tuple[float, float]:
    scale = cfg.set_win_size / 1440
    return WIN_RATE_CARD[0] + 50 * scale, WIN_RATE_CARD[1] - 50 * scale


def _auto_select_point() -> tuple[float, float]:
    """胜率面板上触发“自动选择”的点（battle.py: Rate 文字 +(50, -10) @1080 画布）。"""
    scale = cfg.set_win_size / 1080
    return WIN_LABEL[0] + 50 * scale, WIN_LABEL[1] - 10 * scale


def _in_skill_band(x, y) -> bool:
    y1, y2, x1, x2 = SKILL_BAND
    return y1 < y < y2 and x1 < x < x2


class FakeDevice:
    """模拟一台游戏设备：技能选择 -> 交战播片 -> 战斗结束。"""

    MAX_SELECTION_ITERATIONS = 60
    PAUSE_HITS_BEFORE_FINISH = 3
    ROUND_START_DELAY = 1.0  # 真正开始回合到暂停按钮可被识别之间的延迟
    FRAME_COST = 0.15  # 一次截图/识别的时间

    def __init__(
        self,
        *,
        keyboard_works: bool,
        mouse_click_rate: bool,
        start_button_works: bool = True,
        win_rate_card_visible: bool = True,
        ocr_labels_available: bool = True,
        language_gate_stuck: bool = False,
        gear_right_visible: bool = True,
    ):
        self.clock = VirtualClock()
        self.keyboard_works = keyboard_works
        self.start_button_works = start_button_works
        self.win_rate_card_visible = win_rate_card_visible
        self.ocr_labels_available = ocr_labels_available
        self.language_gate_stuck = language_gate_stuck
        self.gear_right_visible = gear_right_visible
        self.input_handler = FakeInputHandler(supports_keyboard=keyboard_works)
        self.supports_keyboard = keyboard_works
        self.model = "clam"
        self.screenshot = np.zeros((1080, 1920, 3), dtype=np.uint8)
        self.round_start_at: float | None = None
        self.finished = False
        # 状态统计
        self.defense_runs = 0
        self.selection_iterations = 0
        self.pause_hits = 0
        self.round_button_taps = 0
        self.win_rate_card_finds = 0
        self.win_rate_clicks = 0
        # 开始按钮的可点前提：手动选过技能（守备/链接战）或点过胜率面板自动选择
        self.skills_assigned = False
        self.auto_selected = False
        self.auto_select_clicks = 0
        self.start_battle = Battle(is_tool=True)
        self.start_battle.mouse_click_rate = mouse_click_rate

    def supports_key(self, key: str) -> bool:
        return self.keyboard_works

    @property
    def phase(self) -> str:
        if self.finished:
            return "finished"
        if self.round_start_at is not None and self.clock.now >= self.round_start_at + self.ROUND_START_DELAY:
            return "battle"
        return "selection"

    # --- 图像识别 ---
    def find_element(
        self,
        target,
        find_type="image",
        threshold=0.8,
        max_retries=1,
        take_screenshot=False,
        model=None,
        my_crop=None,
        min_dist=10,
        additional_stack=0,
    ):
        if take_screenshot:
            self.take_screenshot()
        if target == "battle/gear_left.png" and threshold != 0.9:
            # _defense_this_round 内部的定位，说明真的执行了一轮守备
            self.defense_runs += 1
        if self.phase == "selection":
            if target == "battle/more_information_assets.png":
                self.selection_iterations += 1
                if self.selection_iterations > self.MAX_SELECTION_ITERATIONS:
                    raise LoopDetected("技能选择界面未推进，守备被反复执行")
                return MORE_INFORMATION
            if target == "battle/gear_left.png":
                return GEAR_LEFT
            if target == "battle/gear_right.png":
                return GEAR_RIGHT if self.gear_right_visible else None
            if target == "battle/win_rate_card.png":
                if not self.win_rate_card_visible:
                    return None
                self.win_rate_card_finds += 1
                return WIN_RATE_CARD
            return None
        if self.phase == "battle":
            if target == "battle/pause_assets.png":
                self.pause_hits += 1
                if self.pause_hits >= self.PAUSE_HITS_BEFORE_FINISH:
                    self.finished = True
                return PAUSE
            return None
        if target == "mirror/road_in_mir/legend_assets.png":
            return LEGEND
        return None

    def find_language_text(self, zh_text, en_text, *args, **kwargs):
        # 面板文字只在技能选择界面存在；按钮位置由它们推算（见 Battle._click_round_start_button）
        if self.phase != "selection" or not self.ocr_labels_available or self.language_gate_stuck:
            return False
        if en_text == "rate":
            return WIN_LABEL
        if en_text == "damage":
            return DAMAGE_LABEL
        return False

    def find_text_element(self, target, *args, **kwargs):
        # 语言无关取词：不查 current_language，中英都试
        if self.phase != "selection" or not self.ocr_labels_available:
            return False
        if isinstance(target, list):
            if "rate" in target or "胜率" in target:
                return WIN_LABEL
            if "damage" in target or "伤害" in target:
                return DAMAGE_LABEL
        return False

    def click_element(self, target, *args, **kwargs):
        return False

    # --- 输入 ---
    def key_press(self, key):
        # 键盘不可用时按键不生效（如未授权辅助功能/触摸端）
        self.clock.sleep(0.05)
        if self.keyboard_works and key == "enter" and self.phase == "selection":
            self._start_round()

    def mouse_click(self, x, y, times=1, move_back=False):
        self.clock.sleep(0.05)
        if self.phase != "selection":
            return True
        if self._near(x, y, ROUND_BUTTON, 30) or self._near(x, y, GEAR_RIGHT, 30):
            # 圆形开始按钮：没选技能时是灰的，点了也不开战（实机实测）
            self.round_button_taps += 1
            if self.start_button_works and (self.skills_assigned or self.auto_selected):
                self._start_round()
        elif self._near(x, y, _auto_select_point(), 30):
            # 点胜率面板 = 自动选择技能（自动战斗）
            self.auto_select_clicks += 1
            self.auto_selected = True
        elif self._near(x, y, _win_rate_click_point(), 25):
            # 老兜底（胜率卡模板 + 齿轮）：同样是自动选择，会顶掉手动守备
            self.win_rate_clicks += 1
            self.auto_selected = True
            self._start_round()
        elif _in_skill_band(x, y):
            # 守备/链接战在技能条上手动点选
            self.skills_assigned = True
        return True

    def _start_round(self) -> None:
        if self.round_start_at is None:
            self.round_start_at = self.clock.now

    @staticmethod
    def _near(x, y, target, tol) -> bool:
        return abs(x - target[0]) <= tol and abs(y - target[1]) <= tol

    def mouse_click_blank(self, coordinate=(1, 1), times=1, move_back=False):
        self.clock.sleep(0.02)
        return True

    def mouse_to_blank(self, coordinate=(1, 1), move_back=False) -> None:
        return None

    def mouse_drag_link(self, position, drag_time=0.1, move_back=False) -> None:
        self.clock.sleep(0.02)

    # --- 截图 ---
    def take_screenshot(self, save=False):
        self.clock.sleep(self.FRAME_COST)
        return self.screenshot

    def get_restore_time(self):
        return None


@pytest.fixture
def run_fight(monkeypatch):
    def _run(
        *,
        keyboard_works: bool,
        mouse_click_rate: bool,
        start_button_works: bool = True,
        win_rate_card_visible: bool = True,
        ocr_labels_available: bool = True,
        language_gate_stuck: bool = False,
        gear_right_visible: bool = True,
        defense_first_round: bool = True,
    ):
        device = FakeDevice(
            keyboard_works=keyboard_works,
            mouse_click_rate=mouse_click_rate,
            start_button_works=start_button_works,
            win_rate_card_visible=win_rate_card_visible,
            ocr_labels_available=ocr_labels_available,
            language_gate_stuck=language_gate_stuck,
            gear_right_visible=gear_right_visible,
        )
        monkeypatch.setattr(battle_module, "auto", device)
        monkeypatch.setattr(battle_module, "sleep", device.clock.sleep)
        monkeypatch.setattr(battle_module, "retry", lambda *args, **kwargs: True)
        monkeypatch.setattr("tasks.base.retry.check_times", lambda *args, **kwargs: False)
        device.start_battle.fight(defense_first_round=defense_first_round)
        return device

    return _run


def test_defense_keeps_keyboard_flow_in_mouse_rate_mode(run_fight):
    """键盘可用（即使曾判定为鼠标模式）：只按 P+Enter，不点鼠标。"""
    device = run_fight(keyboard_works=True, mouse_click_rate=True)

    # 回合开始前允许重试守备（改前语义），但不得无限重复
    assert 1 <= device.defense_runs <= 3
    assert device.round_button_taps == 0
    assert device.win_rate_card_finds == 0
    assert device.win_rate_clicks == 0
    assert device.phase == "finished"


def test_defense_uses_keyboard_without_mouse_mode(run_fight):
    """键盘可用且未进入鼠标模式：同样不点击鼠标。"""
    device = run_fight(keyboard_works=True, mouse_click_rate=False)

    assert 1 <= device.defense_runs <= 3
    assert device.round_button_taps == 0
    assert device.win_rate_card_finds == 0
    assert device.phase == "finished"


def test_defense_starts_round_with_round_button_on_keyboardless_device(run_fight):
    """键盘无效：点圆形开始按钮确认守备，不碰胜率面板，且不进入无限循环。"""
    device = run_fight(keyboard_works=False, mouse_click_rate=True)

    assert device.defense_runs == 1
    assert device.round_button_taps >= 1
    assert device.auto_select_clicks == 0
    assert device.win_rate_card_finds == 0
    assert device.win_rate_clicks == 0
    assert device.phase == "finished"


def test_keyboardless_device_falls_back_to_win_rate(run_fight):
    """键盘无效且开始按钮点不动：退化为胜率自动选择，仍不得死循环。"""
    device = run_fight(keyboard_works=False, mouse_click_rate=True, start_button_works=False)

    assert device.win_rate_card_finds >= 1
    assert device.phase == "finished"


def test_keyboardless_plain_battle_auto_selects_then_starts(run_fight):
    """键盘无效的普通战斗（刷经验本）：必须先自动选择技能，再点开始按钮。

    实机探针结论（PlayCover 1080 画布）：没选技能时圆形开始按钮是灰的，单点 5 个候选
    坐标全都不开战；只有"点胜率面板(自动选择) → 点开始按钮"这个组合能开战
    （pause 0.62 → 0.96，more_information 0.97 → 0.22）。旧实现只按 P+Enter 再等
    胜率卡模板命中，触摸端既送不进按键、模板也打不中（实测 0.42），所以一直卡住。
    """
    device = run_fight(
        keyboard_works=False,
        mouse_click_rate=True,
        win_rate_card_visible=False,
        defense_first_round=False,
    )

    assert device.auto_select_clicks >= 1
    assert device.round_button_taps >= 1
    assert device.phase == "finished"


def test_round_start_button_falls_back_to_gear_anchor_without_ocr_labels(monkeypatch):
    """没有面板文字时，开始按钮锚点仍靠 battle/gear_right.png（实机命中 0.967）。

    只测锚点本身：把按钮设为可点（已有技能）后，仅凭齿轮锚点也要点中。
    """
    device = FakeDevice(keyboard_works=False, mouse_click_rate=False, ocr_labels_available=False)
    monkeypatch.setattr(battle_module, "auto", device)
    monkeypatch.setattr(battle_module, "sleep", device.clock.sleep)
    device.skills_assigned = True

    assert Battle._click_round_start_button() is True
    assert device.round_button_taps >= 1


def test_defense_keeps_selection_when_ocr_labels_missing(run_fight):
    """键盘无效且面板文字识别不到：守备仍用开始按钮确认，不得退化成自动选择。

    自动选择会覆盖刚点好的全员守备，所以守备路径只能点按钮本身，不能点齿轮/胜率面板。
    """
    device = run_fight(
        keyboard_works=False,
        mouse_click_rate=True,
        ocr_labels_available=False,
        defense_first_round=True,
    )

    assert device.defense_runs == 1
    assert device.round_button_taps >= 1
    assert device.auto_select_clicks == 0
    assert device.win_rate_card_finds == 0
    assert device.win_rate_clicks == 0
    assert device.phase == "finished"


def test_keyboardless_plain_battle_survives_language_misdetection(run_fight):
    """实机根因：current_language 被误判成 zh_cn 时 find_language_text 只找中文，英文面板认不出。

    此时 ``find_text_element`` 用不查语言表的取词仍能找到 ``Win Rate``/``Damage``，
    必须靠它把按钮点出来 —— 两个图片锚点都不可用时也得能开战。
    """
    device = run_fight(
        keyboard_works=False,
        mouse_click_rate=True,
        language_gate_stuck=True,
        gear_right_visible=False,
        win_rate_card_visible=False,
        defense_first_round=False,
    )

    assert device.round_button_taps >= 1
    assert device.phase == "finished"
