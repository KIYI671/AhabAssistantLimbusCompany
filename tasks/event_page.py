import re
from dataclasses import dataclass
from typing import Literal

import cv2
import numpy as np

OcrBounds = tuple[int, int, int, int]
OcrEntry = tuple[str, OcrBounds]
EVENT_CHOICE_FIRST_SLOT_OFFSET = 105
EVENT_CHOICE_SLOT_HEIGHT = 124
EVENT_CHOICE_SLOT_TOLERANCE = 50

# 以首个选项 OCR 中心为锚点推导 beta 事件按钮区域，避免匹配具体事件文案。
EVENT_CHOICE_BUTTON_LEFT_OFFSET = -112
EVENT_CHOICE_BUTTON_RIGHT_OFFSET = 490
EVENT_CHOICE_BUTTON_TOP_OFFSET = -38
EVENT_CHOICE_BUTTON_BOTTOM_OFFSET = 62
EVENT_CHOICE_HSV_SATURATION_THRESHOLD = 30
EVENT_CHOICE_LOW_SATURATION_RATIO_THRESHOLD = 0.15
EVENT_CHOICE_HSV_VALUE_THRESHOLD = 40
EVENT_CHOICE_VISIBLE_PIXEL_RATIO_THRESHOLD = 0.5


@dataclass(frozen=True)
class EventPageResolution:
    state: Literal["advance", "wait"]
    position: tuple[int, int] | None
    reason: str


def _entry_center(bounds: OcrBounds) -> tuple[int, int]:
    return ((bounds[0] + bounds[2]) // 2, (bounds[1] + bounds[3]) // 2)


def _normalize_entries(entries: list[OcrEntry]) -> list[OcrEntry]:
    return [("".join(text.split()), bounds) for text, bounds in entries]


def is_event_choice_page(entries: list[OcrEntry]) -> bool:
    """识别事件选项页：需“选项”标题且其下存在候选槽位，避免仅凭“选项”文本误判。"""
    if not any(text == "选项" for text, _ in _normalize_entries(entries)):
        return False
    return bool(find_event_choice_slots(entries))


def find_event_choice_slots(entries: list[OcrEntry]) -> list[tuple[int, tuple[int, int]]]:
    """返回事件候选的稳定纵向槽位及其 OCR 中心坐标。"""
    normalized_entries = _normalize_entries(entries)
    headers = [bounds for text, bounds in normalized_entries if text == "选项"]
    slot_positions: dict[int, tuple[int, int]] = {}
    for header_bounds in headers:
        header_x, header_y = _entry_center(header_bounds)
        first_slot_y = header_y + EVENT_CHOICE_FIRST_SLOT_OFFSET
        for text, bounds in normalized_entries:
            center_x, center_y = _entry_center(bounds)
            slot = round((center_y - first_slot_y) / EVENT_CHOICE_SLOT_HEIGHT)
            expected_y = first_slot_y + slot * EVENT_CHOICE_SLOT_HEIGHT
            if (
                not text
                or text == "选项"
                or text.upper() == "SKIP"
                or re.fullmatch(r"[\d:.：]+", text)
                or slot < 0
                or abs(center_y - expected_y) > EVENT_CHOICE_SLOT_TOLERANCE
                or center_x < header_x - 100
                or center_x > header_x + 300
            ):
                continue
            previous_position = slot_positions.get(slot)
            if previous_position is None or abs(center_y - expected_y) < abs(previous_position[1] - expected_y):
                slot_positions[slot] = (center_x, center_y)
    return sorted(slot_positions.items())


def find_event_choice_positions(entries: list[OcrEntry]) -> list[tuple[int, int]]:
    """返回“选项”标题下同栏候选文本的中心坐标，按稳定槽位排序。"""
    return [position for _, position in find_event_choice_slots(entries)]


def is_first_event_choice_disabled(
    image: object,
    first_choice_center: tuple[int, int],
    *,
    choice_slot_spacing: int = EVENT_CHOICE_SLOT_HEIGHT,
) -> bool:
    """仅根据首选项按钮的低饱和外观判断其是否不可用，信息不足时保持不跳过。"""
    try:
        rgb_image = np.asarray(image)
    except (TypeError, ValueError):
        return False

    if rgb_image.ndim != 3 or rgb_image.shape[2] < 3 or rgb_image.size == 0:
        return False

    if choice_slot_spacing <= 0:
        return False

    scale = choice_slot_spacing / EVENT_CHOICE_SLOT_HEIGHT
    center_x, center_y = first_choice_center
    left = round(center_x + EVENT_CHOICE_BUTTON_LEFT_OFFSET * scale)
    right = round(center_x + EVENT_CHOICE_BUTTON_RIGHT_OFFSET * scale)
    top = round(center_y + EVENT_CHOICE_BUTTON_TOP_OFFSET * scale)
    bottom = round(center_y + EVENT_CHOICE_BUTTON_BOTTOM_OFFSET * scale)
    image_height, image_width = rgb_image.shape[:2]
    clipped_left = max(0, left)
    clipped_right = min(image_width, right)
    clipped_top = max(0, top)
    clipped_bottom = min(image_height, bottom)
    if (
        clipped_left != left
        or clipped_right != right
        or clipped_top != top
        or clipped_bottom != bottom
        or clipped_left >= clipped_right
        or clipped_top >= clipped_bottom
    ):
        return False

    button_rgb = rgb_image[clipped_top:clipped_bottom, clipped_left:clipped_right, :3]
    if button_rgb.size == 0:
        return False
    try:
        hsv = cv2.cvtColor(button_rgb, cv2.COLOR_RGB2HSV)
    except cv2.error:
        return False
    visible_ratio = np.count_nonzero(hsv[:, :, 2] > EVENT_CHOICE_HSV_VALUE_THRESHOLD) / hsv[:, :, 2].size
    if visible_ratio < EVENT_CHOICE_VISIBLE_PIXEL_RATIO_THRESHOLD:
        return False
    saturated_ratio = np.count_nonzero(hsv[:, :, 1] > EVENT_CHOICE_HSV_SATURATION_THRESHOLD) / hsv[:, :, 1].size
    return saturated_ratio < EVENT_CHOICE_LOW_SATURATION_RATIO_THRESHOLD


def resolve_event_page(entries: list[OcrEntry]) -> EventPageResolution | None:
    """仅从 OCR 条目判定事件推进、等待或非事件页。"""
    normalized_entries = _normalize_entries(entries)
    result_visible = any("判定成功" in text or "判定失败" in text for text, _ in normalized_entries)

    if result_visible:
        for text, bounds in normalized_entries:
            if "继续" in text:
                return EventPageResolution("advance", _entry_center(bounds), "continue")
        return EventPageResolution("wait", None, "result_animation")

    has_event_context = any(
        "进行判定" not in text and any(keyword in text for keyword in ("事件", "判定", "选项"))
        for text, _ in normalized_entries
    )
    if has_event_context:
        for text, bounds in normalized_entries:
            if "进行判定" in text:
                return EventPageResolution("advance", _entry_center(bounds), "perform_check")

    return None
