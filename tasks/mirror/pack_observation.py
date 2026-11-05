"""Optional theme-pack observation; existing weight files are read-only.

The catalogue uses the same row/column plus swipe approach as gift observation
and ordered team selection.  A swipe's *actual* movement is fitted from card
artwork, so a short final page does not move the target to the wrong row.
"""

import re
from dataclasses import dataclass
from time import sleep

import cv2
import numpy as np


class PackObservationFailed(RuntimeError):
    """The caller must abandon this run and its rewards, and consume one run."""

    def __init__(self, message, *, cancelled=False):
        super().__init__(message)
        self.cancelled = cancelled


@dataclass(frozen=True)
class ObservationRule:
    floor: int
    row: int
    column: int


def rule_for_floor(rules, floor):
    """Do not supply defaults or change the user's floor/row/column choices."""
    found = None
    for values in rules or ():
        if len(values) != 3 or any(type(value) is not int for value in values):
            raise ValueError("卡包观测规则须为三个整数：楼层、行、列")
        rule = ObservationRule(*values)
        if not (1 <= rule.floor <= 5 and 1 <= rule.row <= 10 and 1 <= rule.column <= 5):
            raise ValueError("卡包观测范围：楼层 1～5，行 1～10，列 1～5")
        if rule.floor == floor:
            if found is not None:
                raise ValueError("同一楼层只能配置一个卡包观测目标")
            found = rule
    return found


def refresh_remaining(words):
    match = re.search(r"(?<!\d)(\d+)\s*[/／]\s*(\d+)(?!\d)", "".join(words or ()))
    if not match:
        return None
    remaining, total = map(int, match.groups())
    return remaining if 0 <= remaining <= total <= 9 else None


def read_refresh_remaining(auto):
    width, height = auto.screenshot.size
    # Only the refresh counter; floor numbers elsewhere must not imply zero.
    crop = (int(width * 0.78), 0, int(width * 0.93), int(height * 0.13))
    return refresh_remaining(auto._run_ocr_for_text(my_crop=crop, only_text=True))


def candidate_layout_complete(positions, size):
    """Reject obvious missing badge matches before asserting *all* are negative.

    Offered packs form a centred, evenly spaced row.  A missing interior or
    edge match must not turn an incomplete set into an all-negative decision.
    A single/two-card detection cannot establish a complete offered row.
    """
    if len(positions) < 3:
        return False
    scale = size[1] / 1080
    xs = sorted(point[0] for point in positions)
    gaps = np.diff(xs)
    if min(gaps) <= 0 or max(gaps) > min(gaps) * 1.3:
        return False
    left, right = xs[0] - 210 * scale, xs[-1] + 60 * scale
    return abs((left + right) / 2 - size[0] / 2) <= 110 * scale


def selection_floor(words):
    text = "".join(words or ()).replace(" ", "")
    match = re.search(r"选择第?([1-5])(?:阶层|层)主题(?:卡)?包", text)
    if not match and "select" in text.casefold() and "theme" in text.casefold():
        match = re.search(r"(?:floor|stage|level)([1-5])", text, re.I)
    return int(match[1]) if match else None


def observed_floor(words):
    text = "".join(words or ()).replace(" ", "")
    match = re.search(r"观测第([1-5])(?:阶层|层)主题(?:卡)?包", text)
    if not match and "observ" in text.casefold() and "theme" in text.casefold():
        match = re.search(r"(?:floor|stage|level)([1-5])", text, re.I)
    return int(match[1]) if match else None


def coordinates(size):
    sx, sy = size[0] / 1920, size[1] / 1080
    return {
        "entry": (285 * sx, 70 * sy),
        "cancel": (765 * sx, 870 * sy),
        "confirm": (1185 * sx, 870 * sy),
        "cost_confirm": (1146 * sx, 740 * sy),
        "cost_cancel": (772 * sx, 740 * sy),
        "first": (964 * sx, 470 * sy),
        "column_step": 176 * sx,
        "row_step": 320 * sy,
        # Between columns 2 and 3: do not begin a scroll on a selectable card.
        "swipe": (1228 * sx, 740 * sy),
        "viewport": (860 * sx, 315 * sy, 1780 * sx, 795 * sy),
        "scale": (sx, sy),
    }


def _words(auto):
    return auto._run_ocr_for_text(only_text=True) or []


def replacement_modal(words):
    text = "".join(words or ()).replace(" ", "").casefold()
    # Full-frame OCR may interleave background titles between the wrapped
    # characters 替 / 换. Require the modal's unique replacement sentence.
    return ("主题卡包" in text and "将被" in text and "替" in text and "换" in text) or (
        "themepack" in text and "replace" in text)


def _catalogue_floor(auto, words=None):
    floor = observed_floor(words if words is not None else _words(auto))
    if floor is not None:
        return floor
    width, height = auto.screenshot.size
    crop = (int(width * .10), int(height * .13), int(width * .56), int(height * .24))
    return observed_floor(auto._run_ocr_for_text(my_crop=crop, only_text=True))


def modal_button(auto, confirm):
    """Restrict OCR to the foreground cost modal, never the directory footer."""
    width, height = auto.screenshot.size
    crop = (int(width * .29), int(height * .65), int(width * .71), int(height * .73))
    label = "确认" if confirm else "取消"
    point = auto.find_language_text(label, "Confirm" if confirm else "Cancel", my_crop=crop)
    if point:
        x, y = point[0] + crop[0], point[1] + crop[1]
    else:
        x, y = coordinates((width, height))["cost_confirm" if confirm else "cost_cancel"]
    # Only the cost confirmation moves up; catalogue/cancel targets are separate.
    return x, y - (10 * height / 1080 if confirm else 0)


def _button(auto, zh, en, fallback):
    width, height = auto.screenshot.size
    point = auto.find_language_text(zh, en, my_crop=(0, height * 0.76, width, height))
    # find_language_text returns crop-relative positions.
    if point:
        return point[0], point[1] + height * 0.76
    return fallback


def catalogue_confirm_button(auto):
    """Lift only the first directory confirmation; keep cost/cancel unchanged."""
    x, y = _button(auto, "确认", ["Confirm", "Select"], coordinates(auto.screenshot.size)["confirm"])
    return x, y - 10 * auto.screenshot.height / 1080


def _cancel_and_fail(auto, rule, message, pause, *, catalogue_expected=False):
    words = _words(auto)
    if replacement_modal(words):
        auto.mouse_click(*modal_button(auto, False))
        pause(.2)
        auto.take_screenshot()
        words = _words(auto)
        if replacement_modal(words):
            raise PackObservationFailed(f"{message}；二次确认弹窗未取消", cancelled=False)
    if observed_floor(words) is not None or (catalogue_expected and selection_floor(words) is None):
        point = _button(auto, "取消", "Cancel", coordinates(auto.screenshot.size)["cancel"])
        auto.mouse_click(*point)
    else:
        # Leave replacement mode when the catalogue never opened.
        auto.key_press("esc")
    for _ in range(8):
        pause(0.2)
        if auto.take_screenshot() is None:
            continue
        words = _words(auto)
        if selection_floor(words) == rule.floor and observed_floor(words) is None:
            raise PackObservationFailed(message, cancelled=True)
    raise PackObservationFailed(f"{message}；取消后仍未确认返回选包页", cancelled=False)


def _fitted_scroll(before, after, viewport, scale):
    """Return content displacement in pixels, including clamped final swipes."""
    box = tuple(round(value) for value in viewport)
    a = np.asarray(before.convert("L").crop(box))
    b = np.asarray(after.convert("L").crop(box))
    if a.shape != b.shape:
        return None
    if np.mean(np.abs(a.astype(float) - b.astype(float))) < 0.5:
        return 0.0
    detector = cv2.ORB_create(nfeatures=1400, edgeThreshold=12)
    ka, da = detector.detectAndCompute(a, None)
    kb, db = detector.detectAndCompute(b, None)
    if da is None or db is None:
        return None
    sx, sy = scale
    deltas = []
    for pair in cv2.BFMatcher(cv2.NORM_HAMMING).knnMatch(da, db, k=2):
        if len(pair) != 2 or pair[0].distance >= 0.72 * pair[1].distance:
            continue
        old, new = ka[pair[0].queryIdx].pt, kb[pair[0].trainIdx].pt
        dx, dy = new[0] - old[0], new[1] - old[1]
        if abs(dx) <= 8 * sx and -370 * sy <= dy <= 5 * sy:
            deltas.append(dy)
    if len(deltas) < 6:
        return None
    shift = float(np.median(deltas))
    inliers = [value for value in deltas if abs(value - shift) <= 4 * sy]
    if len(inliers) < 6 or len(inliers) < len(deltas) * 0.6:
        return None
    return float(np.median(inliers))


def _wait_stable(auto, viewport, pause, max_frames=12):
    """Wait for two fresh settled frames, including inertia and modal entry."""
    box = tuple(round(value) for value in viewport)
    previous = np.asarray(auto.screenshot.convert("L").crop(box), dtype=np.int16)
    settled = 0
    for _ in range(max_frames):
        pause(0.2)
        if auto.take_screenshot() is None:
            settled = 0
            continue
        current = np.asarray(auto.screenshot.convert("L").crop(box), dtype=np.int16)
        if current.shape != previous.shape:
            return False
        difference = np.abs(current - previous)
        quiet = difference.mean() <= 2 and np.mean(difference > 20) <= .02
        settled = settled + 1 if quiet else 0
        previous = current
        if settled >= 2:
            return True
    return False


def select_catalogue_card(auto, rule, pause=sleep):
    """Fit the configured grid cell through bounded, measured mouse swipes."""
    layout = coordinates(auto.screenshot.size)
    sx, sy = layout["scale"]
    x = layout["first"][0] + (rule.column - 1) * layout["column_step"]
    y = layout["first"][1] + (rule.row - 1) * layout["row_step"]
    _, top, _, bottom = layout["viewport"]
    for _ in range(20):
        # The second row is already clickable in the initial viewport. Use its
        # visible interior (750 at 1080p), as in the verified faust.11 flow.
        low = max(top + 30 * sy, y - 106 * sy)
        high = min(bottom - 45 * sy, y + 106 * sy)
        if high - low >= 50 * sy:
            click_y = min(max(y, low), high)
            auto.mouse_click(x, click_y)
            return x, click_y
        before = auto.screenshot.copy()
        # Keep overlapping card artwork. A whole-row flick could overshoot the
        # fitting range and leave only a small, ambiguous strip to compare.
        distance = min(240 * sy, max(80 * sy, y - layout["first"][1]))
        auto.mouse_swipe_for_scroll(*layout["swipe"], dy=-distance, duration=0.35)
        if not _wait_stable(auto, layout["viewport"], pause):
            _cancel_and_fail(auto, rule, "卡包目录滑动后未稳定", pause, catalogue_expected=True)
        if _catalogue_floor(auto) != rule.floor:
            _cancel_and_fail(auto, rule, "卡包目录滑动时页面发生变化", pause, catalogue_expected=True)
        shift = _fitted_scroll(before, auto.screenshot, layout["viewport"], (sx, sy))
        if shift is None or shift > -5 * sy:
            _cancel_and_fail(auto, rule, "无法拟合卡包目录滑动位置，未猜测点击其他卡包", pause, catalogue_expected=True)
        y += shift
    _cancel_and_fail(auto, rule, "配置的卡包行不在可达目录中", pause, catalogue_expected=True)


def observe_and_select(auto, log, rule, replace_position, pause=sleep, candidate_count=None):
    """Entry -> replacement slot -> catalogue cell -> confirm -> final drag."""
    words = _words(auto)
    if selection_floor(words) != rule.floor:
        _cancel_and_fail(auto, rule, "观测前未能确认当前选包楼层", pause)
    entry = auto.find_language_text(["主题卡包观测", "观测主题卡包"], ["Theme Pack Observation", "Observe Theme"])
    auto.mouse_click(*(entry or coordinates(auto.screenshot.size)["entry"]))
    replacement_clicked = False
    for _ in range(12):
        pause(0.2)
        if auto.take_screenshot() is None:
            continue
        words = _words(auto)
        if _catalogue_floor(auto, words) is not None:
            break
        if selection_floor(words) == rule.floor and not replacement_clicked:
            # Clicking observation only enables replacement mode.  The current
            # candidate MUST be selected before the catalogue can open.
            auto.mouse_click(*replace_position)
            replacement_clicked = True
    else:
        _cancel_and_fail(auto, rule, "未能进入卡包观测目录", pause)
    if _catalogue_floor(auto, words) != rule.floor:
        _cancel_and_fail(auto, rule, "观测目录楼层与配置不一致", pause, catalogue_expected=True)
    if not _wait_stable(auto, coordinates(auto.screenshot.size)["viewport"], pause):
        _cancel_and_fail(auto, rule, "卡包观测目录未稳定", pause, catalogue_expected=True)
    select_catalogue_card(auto, rule, pause)
    pause(0.2)
    if auto.take_screenshot() is None:
        _cancel_and_fail(auto, rule, "观测卡包选中后截图失败", pause, catalogue_expected=True)
    if _catalogue_floor(auto) != rule.floor:
        _cancel_and_fail(auto, rule, "观测卡包选中后目录状态不明", pause, catalogue_expected=True)
    confirm = catalogue_confirm_button(auto)
    auto.mouse_click(*confirm)  # Exactly one attempt; never pay/confirm twice.
    returned_position = None
    cost_confirmed = False
    for _ in range(16):
        pause(0.2)
        if auto.take_screenshot() is None:
            continue
        words = _words(auto)
        if replacement_modal(words):
            if not cost_confirmed:
                width, height = auto.screenshot.size
                if not _wait_stable(auto, (width * .30, height * .60, width * .70, height * .80), pause):
                    _cancel_and_fail(auto, rule, "二次确认弹窗未稳定", pause, catalogue_expected=True)
                if not replacement_modal(_words(auto)):
                    continue
                auto.mouse_click(*modal_button(auto, True))
                cost_confirmed = True  # Never repeat a star-cost confirmation.
            continue
        if selection_floor(words) == rule.floor and observed_floor(words) is None:
            offers = auto.find_element(
                "mirror/theme_pack/theme_pack_features.png", find_type="image_with_multiple_targets"
            ) or []
            # The replacement animation slides the cards left before restoring
            # the row.  Its visible selection title alone is not sufficient.
            if candidate_count is not None and len(offers) != candidate_count:
                continue
            if not candidate_layout_complete(offers, auto.screenshot.size):
                continue
            closest = min(offers, key=lambda point: abs(point[0] - replace_position[0]))
            if abs(closest[0] - replace_position[0]) <= 70 * auto.screenshot.height / 1080:
                returned_position = closest
                break
    if returned_position is None:
        _cancel_and_fail(auto, rule, "卡包观测确认未成功，取消并放弃本局", pause, catalogue_expected=True)
    # The observed card replaces the chosen candidate in that same slot.  Do
    # not search its user-configured weight or assume a fixed final slot.
    auto.mouse_drag_down(*returned_position)
    for _ in range(30):
        pause(0.2)
        if auto.take_screenshot() is None:
            continue
        if auto.find_element("mirror/road_in_mir/legend_assets.png"):
            log.info(f"已观测并选择第 {rule.floor} 层目录第 {rule.row} 行第 {rule.column} 列卡包")
            return True
    raise PackObservationFailed("观测已替换，但拖入卡包后未确认进入地图", cancelled=False)
