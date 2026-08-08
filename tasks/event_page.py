from dataclasses import dataclass
from typing import Literal

OcrBounds = tuple[int, int, int, int]
OcrEntry = tuple[str, OcrBounds]


@dataclass(frozen=True)
class EventPageResolution:
    state: Literal["advance", "wait"]
    position: tuple[int, int] | None
    reason: str


def _entry_center(bounds: OcrBounds) -> tuple[int, int]:
    return ((bounds[0] + bounds[2]) // 2, (bounds[1] + bounds[3]) // 2)


def resolve_event_page(entries: list[OcrEntry]) -> EventPageResolution | None:
    """仅从 OCR 条目判定事件推进、等待或非事件页。"""
    normalized_entries = [("".join(text.split()), bounds) for text, bounds in entries]
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
