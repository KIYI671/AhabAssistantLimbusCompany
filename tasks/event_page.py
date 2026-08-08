import re
from dataclasses import dataclass
from typing import Literal

OcrBounds = tuple[int, int, int, int]
OcrEntry = tuple[str, OcrBounds]
EVENT_CHOICE_FIRST_SLOT_OFFSET = 105
EVENT_CHOICE_SLOT_HEIGHT = 124
EVENT_CHOICE_SLOT_TOLERANCE = 50


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
    """仅凭 OCR 的“选项”标题识别事件选项页。"""
    return any(text == "选项" for text, _ in _normalize_entries(entries))


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
            if previous_position is None or abs(center_y - expected_y) < abs(
                previous_position[1] - expected_y
            ):
                slot_positions[slot] = (center_x, center_y)
    return sorted(slot_positions.items())


def find_event_choice_positions(entries: list[OcrEntry]) -> list[tuple[int, int]]:
    """返回“选项”标题下同栏候选文本的中心坐标，按稳定槽位排序。"""
    return [position for _, position in find_event_choice_slots(entries)]


def resolve_event_page(entries: list[OcrEntry]) -> EventPageResolution | None:
    """仅从 OCR 条目判定事件推进、等待或非事件页。"""
    normalized_entries = _normalize_entries(entries)
    result_visible = any(
        "判定成功" in text or "判定失败" in text
        for text, _ in normalized_entries
    )

    if result_visible:
        for text, bounds in normalized_entries:
            if "继续" in text:
                return EventPageResolution("advance", _entry_center(bounds), "continue")
        return EventPageResolution("wait", None, "result_animation")

    has_event_context = any(
        "进行判定" not in text
        and any(keyword in text for keyword in ("事件", "判定", "选项"))
        for text, _ in normalized_entries
    )
    if has_event_context:
        for text, bounds in normalized_entries:
            if "进行判定" in text:
                return EventPageResolution(
                    "advance", _entry_center(bounds), "perform_check"
                )

    return None
