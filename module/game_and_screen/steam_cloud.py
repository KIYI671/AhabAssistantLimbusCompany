from __future__ import annotations

import logging
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any, TypeAlias

OcrBounds: TypeAlias = tuple[int, int, int, int]
OcrEntry: TypeAlias = tuple[str, OcrBounds]

_DIALOG_TITLE = "无法同步"
_SAVE_BODY = "未能将您的存档"
_CLOUD_BODY = "Steam云同步"
_CONTINUE_BUTTON = "仍然进行游戏"
_CANCEL_BUTTON = "取消"
_MAX_DIALOG_WIDTH = 1000
_MAX_DIALOG_HEIGHT = 600


@dataclass(frozen=True)
class SteamCloudDialog:
    continue_position: tuple[int, int]
    continue_bounds: OcrBounds


def _normalized_text(text: str) -> str:
    return "".join(text.split())


def _valid_bounds(bounds: object) -> bool:
    if not isinstance(bounds, tuple) or len(bounds) != 4:
        return False
    left, top, right, bottom = bounds
    return all(isinstance(value, int | float) for value in bounds) and left < right and top < bottom


def _entry_with_text(entries: Iterable[OcrEntry], text: str, *, exact: bool = False) -> OcrEntry | None:
    for entry_text, bounds in entries:
        normalized = _normalized_text(entry_text)
        matches = normalized == text if exact else text in normalized
        if matches and _valid_bounds(bounds):
            return entry_text, bounds
    return None


def resolve_steam_cloud_dialog(entries: list[OcrEntry]) -> SteamCloudDialog | None:
    """仅在 Steam 云同步确认的完整中文签名存在时返回“仍然进行游戏”按钮。"""
    title = _entry_with_text(entries, _DIALOG_TITLE, exact=True)
    save_body = _entry_with_text(entries, _SAVE_BODY)
    cloud_body = _entry_with_text(entries, _CLOUD_BODY)
    continue_button = _entry_with_text(entries, _CONTINUE_BUTTON, exact=True)
    cancel_button = _entry_with_text(entries, _CANCEL_BUTTON, exact=True)
    if title is None or save_body is None or cloud_body is None or continue_button is None or cancel_button is None:
        return None

    dialog_entries = (title, save_body, cloud_body, continue_button, cancel_button)
    left_edge = min(entry[1][0] for entry in dialog_entries)
    top_edge = min(entry[1][1] for entry in dialog_entries)
    right_edge = max(entry[1][2] for entry in dialog_entries)
    bottom_edge = max(entry[1][3] for entry in dialog_entries)
    if right_edge - left_edge > _MAX_DIALOG_WIDTH or bottom_edge - top_edge > _MAX_DIALOG_HEIGHT:
        return None

    continue_bounds = continue_button[1]
    cancel_bounds = cancel_button[1]
    body_bottom = max(title[1][3], save_body[1][3], cloud_body[1][3])
    continue_center_y = (continue_bounds[1] + continue_bounds[3]) // 2
    cancel_center_y = (cancel_bounds[1] + cancel_bounds[3]) // 2
    if (
        continue_bounds[1] <= body_bottom
        or cancel_bounds[0] < continue_bounds[2]
        or abs(cancel_center_y - continue_center_y) > 30
    ):
        return None

    left, top, right, bottom = continue_bounds
    return SteamCloudDialog(
        continue_position=((left + right) // 2, (top + bottom) // 2),
        continue_bounds=continue_bounds,
    )


def _entries_from_ocr_result(result: Any) -> list[OcrEntry]:
    if isinstance(result, list):
        return result

    texts = getattr(result, "txts", ())
    boxes = getattr(result, "boxes", ())
    entries: list[OcrEntry] = []
    for text, box in zip(texts, boxes):
        points = list(box)
        if not points:
            continue
        x_values = [point[0] for point in points]
        y_values = [point[1] for point in points]
        entries.append((str(text), (int(min(x_values)), int(min(y_values)), int(max(x_values)), int(max(y_values)))))
    return entries


def _production_dependencies() -> tuple[Callable[[], Any], Callable[[Any], Any], Callable[[int, int], None]]:
    import pyautogui

    from module.ocr import ocr

    return pyautogui.screenshot, ocr.run, pyautogui.click


def handle_steam_cloud_sync_dialog(
    capture: Callable[[], Any] | None = None,
    recognize: Callable[[Any], Any] | None = None,
    click: Callable[[int, int], None] | None = None,
    on_dialog_detected: Callable[[], None] | None = None,
) -> bool:
    """识别并确认唯一获授权的 Steam 云同步弹窗，成功点击时返回 ``True``。"""
    try:
        if capture is None or recognize is None or click is None:
            capture, recognize, click = _production_dependencies()

        screenshot = capture()
        if screenshot is None:
            return False

        dialog = resolve_steam_cloud_dialog(_entries_from_ocr_result(recognize(screenshot)))
        if dialog is None:
            return False

        if on_dialog_detected is not None:
            on_dialog_detected()
        click(*dialog.continue_position)
        return True
    except Exception as error:
        logging.getLogger("AALC").debug("Steam 云同步弹窗识别或确认失败: %s", type(error).__name__)
        return False
