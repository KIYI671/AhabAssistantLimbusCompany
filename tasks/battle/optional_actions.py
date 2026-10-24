"""Prepare an EGO once per TURN, then submit through the shared battle flow."""

import re
import unicodedata
from dataclasses import dataclass
from enum import Enum
from time import sleep

from module.my_error.my_error import userStopError


class BattleEventOutcome(Enum):
    EXCLUDED_EXHAUSTED = "excluded_participants_exhausted"


class EgoAttemptState(set):
    """Persist TURN attempts and an observed combat transition across fight reentry."""

    def __init__(self):
        super().__init__()
        self.last_turn, self.combat_seen = None, False

    def clear(self):
        super().clear()
        self.last_turn, self.combat_seen = None, False

    def ready(self, turn):
        restarted = (self.combat_seen and self.last_turn is not None and turn <= self.last_turn)
        if restarted:
            self.clear()
        self.last_turn, self.combat_seen = turn, False
        return restarted


@dataclass(frozen=True)
class EgoRule:
    turn: int = 1
    name: str = ""
    mode: int = 1
    enabled: bool = True


@dataclass(frozen=True)
class BattleOptions:
    lower_chain: bool = False  # Legacy serialized field, no longer an independent feature.
    ego_enabled: bool = False
    ego_turn: int = 1
    ego_name: str = ""
    ego_mode: int = 1  # 0 awakening, 1 corrosion
    ego_rules: tuple[EgoRule, ...] | None = None  # None supports the previous single-rule format


def configured_ego_rules(options):
    if options.ego_rules is None:
        return (EgoRule(options.ego_turn, options.ego_name, options.ego_mode),)
    result = []
    for value in options.ego_rules:
        if isinstance(value, EgoRule):
            result.append(value)
        elif isinstance(value, dict):
            result.append(EgoRule(**value))
        else:
            result.append(EgoRule(value.turn, value.name, value.mode, value.enabled))
    return tuple(result)


def normalized_name(value):
    return "".join(unicodedata.normalize("NFKC", value).split()).casefold()


def exact_name_position(words, wanted, scale=1):
    """Full equality only; adjacent OCR fragments may form one title."""
    if not isinstance(words, dict) or not normalized_name(wanted):
        return None
    target = normalized_name(wanted)
    items = sorted(words.items(), key=lambda item: (item[1][1], item[1][0]))
    for text, point in items:
        if normalized_name(text) == target:
            return tuple(point)
    for _, anchor in items:
        row = sorted([(text, point) for text, point in items if abs(point[1] - anchor[1]) < 15 * scale],
                     key=lambda item: item[1][0])
        for start in range(len(row)):
            for end in range(start + 2, len(row) + 1):
                part = row[start:end]
                if part[-1][1][0] - part[0][1][0] > 400 * scale or any(
                    part[i + 1][1][0] - part[i][1][0] > 160 * scale for i in range(len(part) - 1)
                ):
                    continue
                if normalized_name("".join(text for text, _ in part)) == target:
                    return (sum(p[0] for _, p in part) / len(part), sum(p[1] for _, p in part) / len(part))
    return None


def lower_row_points(left, right, scale):
    count = int((right[0] - left[0] - 194 * scale) / (145 * scale))
    if not 1 <= count <= 12:
        return []
    return [(left[0] + (220 - 4.5 * count + 161 * i) * scale, left[1] + 250 * scale)
            for i in range(count)]


def general_battle(auto, scale, lower_chain=False, logger=None, pause=sleep):
    """Focused: P+Enter. Normal: optional lower-row chain+Enter, else P+Enter."""
    if lower_chain:
        try:
            left = auto.find_element("battle/gear_left.png", threshold=0.9)
            right = auto.find_element("battle/gear_right.png", threshold=0.9)
            points = lower_row_points(left, right, scale) if left and right else []
            if points:
                auto.mouse_drag_link([left, *points, (right[0] + 5 * len(points) * scale, right[1] + 150 * scale)])
                pause(0.5)  # Original chain submission waits after mouse-up.
                auto.key_press("enter")
                pause(1)
                return
        except userStopError:
            raise
        except Exception as error:
            if logger:
                logger.warning(f"下排连线未完成，转入P+Enter：{error}")
    auto.key_press("p")
    pause(0.5)
    auto.key_press("enter")


class TurnEgoAction:
    def __init__(self, auto, height, options, logger, turn_box, running=lambda: True, pause=sleep, attempted_turns=None):
        self.auto, self.scale, self.options, self.log = auto, height / 1440, options, logger
        self.turn_box, self.running, self.pause = turn_box, running, pause
        self.attempted_turns = attempted_turns if attempted_turns is not None else EgoAttemptState()

    def observe_running(self):
        if isinstance(self.attempted_turns, EgoAttemptState):
            self.attempted_turns.combat_seen = True

    def reset(self):
        self.attempted_turns.clear()

    def _turn(self):
        if not self.turn_box:
            return None
        words = self.auto._run_ocr_for_text(my_crop=self.turn_box, only_text=True)
        numbers = re.findall(r"\d+", " ".join(words or []))
        return int(numbers[0]) if len(numbers) == 1 else None

    def _close_menu(self):
        if not self.running():
            return
        self.auto.mouse_click(20 * self.scale, 20 * self.scale)
        self.pause(0.15)
        self.auto.take_screenshot()

    def _configure(self, rule=None):
        rule = rule or EgoRule(self.options.ego_turn, self.options.ego_name, self.options.ego_mode)
        left = self.auto.find_element("battle/gear_left.png", threshold=0.9)
        right = self.auto.find_element("battle/gear_right.png", threshold=0.9)
        points = lower_row_points(left, right, self.scale) if left and right else []
        width, height = self.auto.screenshot.size
        entry = points[0] if points else (
            (right[0] - 123.5 * self.scale, right[1] + 250 * self.scale) if right
            else (width * 0.5, height * 0.94)
        )
        name = None
        for entry_attempt in range(2):
            self.auto.mouse_hold(*entry, duration=0.8)
            self.pause(0.25)
            menu_seen = False
            for frame in range(2):
                if not self.running():
                    return False
                if self.auto.take_screenshot(gray=False) is None:
                    continue
                width, height = self.auto.screenshot.size
                crop = (0, int(height * 0.18), width, int(height * 0.86))
                words = self.auto._run_ocr_for_text(my_crop=crop)
                point = exact_name_position(words, rule.name, self.scale)
                name = (point[0], point[1] + crop[1]) if point else None
                compact = normalized_name("".join(words or ()))
                menu_seen |= any(token in compact for token in ("侵蚀概率", "侵蝕概率", "overclock", "更多信息", "moreinfo"))
                if name:
                    break
                # Narrower OCR keeps card titles larger than a full-width OCR
                # image. It is a read retry, never a looser identity comparison.
                if menu_seen:
                    crop = (int(width * .2), int(height * .32), int(width * .86), int(height * .8))
                    words = self.auto._run_ocr_for_text(my_crop=crop)
                    point = exact_name_position(words, rule.name, self.scale)
                    if point:
                        name = (point[0] + crop[0], point[1] + crop[1])
                        break
                if frame == 0:
                    self.pause(.15)
            if name or menu_seen or not self.running():
                break
            if entry_attempt == 0:
                self.log.debug("未读到EGO菜单文字，退出后重试一次入口长按")
                self._close_menu()
        if name is None:
            self.log.debug(f"未找到完整EGO名称“{rule.name}”，退出菜单")
            self._close_menu()
            return False
        card = (name[0], name[1] - 170 * self.scale)
        if rule.mode == 1:
            self.auto.mouse_hold(*card, duration=1.2)
            self.pause(0.15)
        if not self.running():
            return False
        self.auto.mouse_click(*card)
        self.pause(0.15)  # Let the single card selection settle before leaving.
        # No OVERCLOCK, color-frame, or selected-slot postcondition is read.
        try:
            self.auto.mouse_click(20 * self.scale, 20 * self.scale)
            self.pause(0.15)
            self.auto.take_screenshot()  # refresh only for the following general battle action
        except userStopError:
            raise
        except Exception as error:
            self.log.debug(f"EGO已点击，菜单收尾或刷新画面失败仍接一般战斗，不再选择备用：{error}")
        return True

    def claim_turn(self):
        """Read/latch TURN before preparing guard; no mouse input or submission."""
        if not self.options.ego_enabled:
            return False, ()
        try:
            turn = self._turn()
            if turn is not None and isinstance(self.attempted_turns, EgoAttemptState):
                if self.attempted_turns.ready(turn):
                    self.log.info("已观察到战斗重新开始，清空EGO回合尝试记录")
            rules = tuple(rule for rule in configured_ego_rules(self.options)
                          if rule.enabled and rule.turn == turn)
            if rules and turn not in self.attempted_turns:
                self.attempted_turns.add(turn)
                return True, rules
        except userStopError:
            raise
        except Exception as error:
            self.log.warning(f"TURN读取失败，接一般战斗：{error}")
            return True, ()
        return False, ()

    def prepare(self, claim=None):
        """Prepare only. True gives this TURN priority over skill preferences."""
        matched, rules = self.claim_turn() if claim is None else claim
        for rule in rules:
            if not self.running():
                break
            try:
                if self._configure(rule):
                    break
            except userStopError:
                raise
            except Exception as error:
                self.log.warning(f"EGO“{rule.name}”配置未完成，退出菜单后尝试下一备用：{error}")
                try:
                    self._close_menu()
                except userStopError:
                    raise
                except Exception:
                    pass
        return matched

    def perform(self):
        """Standalone entry retained for callers; battle orchestrates prepare separately."""
        if not self.running():
            return False
        if self.prepare():
            if self.running():
                general_battle(self.auto, self.scale, True, self.log, self.pause)
            return True
        return False
