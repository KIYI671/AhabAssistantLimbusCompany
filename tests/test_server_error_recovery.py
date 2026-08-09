from __future__ import annotations

import importlib

import numpy as np
import pytest

import tasks.base.retry as retry_module
from module.automation.automation import Automation
from tasks.base.retry import find_server_error_dialog, is_retry_button_enabled


def _ocr_entry(text: str, box: tuple[int, int, int, int]) -> tuple[str, tuple[int, int, int, int]]:
    return text, box


def test_find_server_error_dialog_requires_message_and_ordered_buttons() -> None:
    dialog = find_server_error_dialog(
        [
            _ocr_entry("服务器发生错误。", (600, 300, 900, 340)),
            _ocr_entry("请稍后再试。", (650, 350, 850, 390)),
            _ocr_entry("关闭", (400, 600, 500, 650)),
            _ocr_entry("重试", (700, 600, 800, 650)),
        ]
    )

    assert dialog is not None
    assert dialog.close_position == (450, 625)
    assert dialog.retry_position == (750, 625)
    assert find_server_error_dialog([]) is None
    assert find_server_error_dialog(
        [
            _ocr_entry("服务器发生错误。", (600, 300, 900, 340)),
            _ocr_entry("请稍后再试。", (650, 350, 850, 390)),
            _ocr_entry("关闭", (700, 600, 800, 650)),
            _ocr_entry("重试", (400, 600, 500, 650)),
        ]
    ) is None


def test_is_retry_button_enabled_accepts_gold_text_and_rejects_gray_text() -> None:
    gold = np.zeros((20, 40, 3), dtype=np.uint8)
    gold[5:15, 10:30] = (236, 203, 163)
    gray = np.zeros((20, 40, 3), dtype=np.uint8)
    gray[5:15, 10:30] = (180, 180, 180)

    assert is_retry_button_enabled(gold, (0, 0, 40, 20)) is True
    assert is_retry_button_enabled(gray, (0, 0, 40, 20)) is False


class FakeAuto:
    def __init__(self, entries: list[tuple[str, tuple[int, int, int, int]]], image: np.ndarray) -> None:
        self.entries = entries
        self.color_screenshot = image
        self.clicks: list[tuple[int, int]] = []

    def get_ocr_entries(self) -> list[tuple[str, tuple[int, int, int, int]]]:
        return self.entries

    def mouse_click(self, x: int, y: int) -> None:
        self.clicks.append((x, y))


def test_handle_server_error_dialog_waits_for_game_countdown_and_delayed_gray_timeout(monkeypatch) -> None:
    entries = [
        ("服务器发生错误。", (60, 10, 180, 30)),
        ("请稍后再试。", (70, 35, 170, 55)),
        ("关闭", (20, 80, 60, 100)),
        ("重试4", (100, 80, 140, 100)),
    ]
    gold = np.zeros((120, 200, 3), dtype=np.uint8)
    gold[80:100, 100:140] = (236, 203, 163)
    fake_auto = FakeAuto(entries, gold)
    monkeypatch.setattr(retry_module, "auto", fake_auto)
    monkeypatch.setattr(retry_module, "_last_server_error_retry_time", 0.0)
    monkeypatch.setattr(retry_module, "_server_error_disabled_since", None)

    assert retry_module.handle_server_error_dialog(now=10.0) is True
    assert fake_auto.clicks == []

    fake_auto.entries[-1] = ("重试", (100, 80, 140, 100))
    gray = np.zeros((120, 200, 3), dtype=np.uint8)
    gray[80:100, 100:140] = (180, 180, 180)
    fake_auto.color_screenshot = gray
    calls: list[str] = []
    monkeypatch.setattr(retry_module, "kill_game", lambda: calls.append("kill"))
    monkeypatch.setattr(retry_module, "restart_game", lambda: calls.append("restart"))

    assert retry_module.handle_server_error_dialog(now=20.0) is True
    assert fake_auto.clicks == []
    assert calls == []
    assert retry_module.handle_server_error_dialog(now=20.0 + retry_module.SERVER_ERROR_DISABLED_TIMEOUT) is False
    assert fake_auto.clicks == [(40, 90)]
    assert calls == ["kill", "restart"]


def test_handle_server_error_dialog_throttles_available_retry(monkeypatch) -> None:
    entries = [
        ("服务器发生错误。", (60, 10, 180, 30)),
        ("请稍后再试。", (70, 35, 170, 55)),
        ("关闭", (20, 80, 60, 100)),
        ("重试", (100, 80, 140, 100)),
    ]
    gold = np.zeros((120, 200, 3), dtype=np.uint8)
    gold[80:100, 100:140] = (236, 203, 163)
    fake_auto = FakeAuto(entries, gold)
    monkeypatch.setattr(retry_module, "auto", fake_auto)
    monkeypatch.setattr(retry_module, "_last_server_error_retry_time", 0.0)
    monkeypatch.setattr(retry_module, "_server_error_disabled_since", None)

    assert retry_module.handle_server_error_dialog(now=10.0) is True
    assert fake_auto.clicks == [(120, 90)]
    assert retry_module.handle_server_error_dialog(now=14.9) is True
    assert fake_auto.clicks == [(120, 90)]
    assert retry_module.handle_server_error_dialog(now=15.0) is True
    assert fake_auto.clicks == [(120, 90), (120, 90)]


def test_get_ocr_entries_accepts_rapidocr_numpy_boxes(monkeypatch) -> None:
    automation = object.__new__(Automation)
    automation.screenshot = object()
    output = type(
        "Output",
        (),
        {
            "txts": ("服务器发生错误。",),
            "boxes": np.array([[[10, 20], [30, 20], [30, 40], [10, 40]]]),
        },
    )()
    monkeypatch.setattr("module.automation.automation.ocr.run", lambda _: output)

    assert automation.get_ocr_entries() == [("服务器发生错误。", (10, 20, 30, 40))]


def test_full_frame_ocr_is_cached_until_screenshot_refresh(monkeypatch) -> None:
    automation = object.__new__(Automation)
    automation.screenshot = object()
    automation._full_ocr_cache = None
    runs: list[int] = []
    output = type(
        "Output",
        (),
        {
            "txts": ("确认",),
            "boxes": np.array([[[10, 20], [30, 20], [30, 40], [10, 40]]]),
        },
    )()

    def fake_run(_):
        runs.append(1)
        return output

    monkeypatch.setattr("module.automation.automation.ocr.run", fake_run)

    automation.get_ocr_entries()
    automation.get_ocr_entries()
    assert len(runs) == 1  # 同一帧多次调用复用缓存，仅 OCR 一次

    automation._full_ocr_cache = None  # 模拟新截图刷新使缓存失效
    automation.get_ocr_entries()
    assert len(runs) == 2


def test_luxcavation_stops_normal_detection_while_server_error_is_handled(monkeypatch) -> None:
    import tasks.daily.luxcavation as luxcavation

    class FakeTaskAuto:
        model = ""

        def __init__(self) -> None:
            self.screenshots = 0
            self.find_calls = 0

        def take_screenshot_with_color(self) -> object:
            self.screenshots += 1
            if self.screenshots == 2:
                raise StopIteration
            return object()

        def find_element(self, *_args, **_kwargs) -> None:
            self.find_calls += 1
            raise AssertionError("服务器错误处理期间不应执行普通识图")

    fake_auto = FakeTaskAuto()
    monkeypatch.setattr(luxcavation, "auto", fake_auto)
    monkeypatch.setattr(luxcavation, "handle_server_error_dialog", lambda: True)

    for task in (luxcavation.EXP_luxcavation, luxcavation.thread_luxcavation):
        fake_auto.screenshots = 0
        with pytest.raises(StopIteration):
            task()
        assert fake_auto.find_calls == 0


def test_server_error_dialog_matches_the_user_reported_screenshot_layout() -> None:
    entries = [
        ("服务器发生错误。", (275, 143, 456, 168)),
        ("请稍后再试。", (300, 177, 433, 204)),
        ("关闭", (218, 323, 275, 356)),
        ("重试", (469, 324, 527, 356)),
    ]

    dialog = find_server_error_dialog(entries)

    assert dialog is not None
    assert dialog.close_position == (246, 339)
    assert dialog.retry_position == (498, 340)


def test_to_battle_skips_normal_detection_when_server_error_is_handled(monkeypatch) -> None:
    battle_module = importlib.import_module("tasks.battle.battle")

    class FakeBattleAuto:
        model = ""

        def __init__(self) -> None:
            self.screenshots = 0
            self.find_calls = 0

        def take_screenshot_with_color(self) -> object:
            self.screenshots += 1
            if self.screenshots == 2:
                raise StopIteration
            return object()

        def find_element(self, *_args, **_kwargs) -> None:
            self.find_calls += 1
            raise AssertionError("服务器错误处理期间不应执行开始战斗识图")

    fake_auto = FakeBattleAuto()
    monkeypatch.setattr(battle_module, "auto", fake_auto)
    monkeypatch.setattr(battle_module, "handle_server_error_dialog", lambda: True)

    with pytest.raises(StopIteration):
        battle_module.Battle.to_battle()

    assert fake_auto.find_calls == 0


def test_to_battle_returns_false_when_server_error_restarts_game(monkeypatch) -> None:
    battle_module = importlib.import_module("tasks.battle.battle")

    class FakeBattleAuto:
        model = ""

        def __init__(self) -> None:
            self.find_calls = 0

        def take_screenshot_with_color(self) -> object:
            return object()

        def find_element(self, *_args, **_kwargs) -> None:
            self.find_calls += 1
            raise AssertionError("重启游戏后不应执行开始战斗识图")

    fake_auto = FakeBattleAuto()
    monkeypatch.setattr(battle_module, "auto", fake_auto)
    monkeypatch.setattr(battle_module, "handle_server_error_dialog", lambda: False)

    assert battle_module.Battle.to_battle() is False
    assert fake_auto.find_calls == 0


class _FightServerErrorAuto:
    def __init__(self, *, stop_after_next_frame: bool = False) -> None:
        self.stop_after_next_frame = stop_after_next_frame
        self.screenshots = 0
        self.find_calls = 0
        self.ocr_calls = 0

    def take_screenshot_with_color(self) -> object:
        self.screenshots += 1
        if self.stop_after_next_frame and self.screenshots == 2:
            raise StopIteration
        return object()

    def take_screenshot(self) -> object:
        raise AssertionError("战斗服务器错误检测必须保留彩色截图")

    def find_element(self, *_args, **_kwargs) -> None:
        self.find_calls += 1
        raise AssertionError("服务器错误处理期间不应执行普通战斗识图")

    def get_ocr_entries(self) -> list[tuple[str, tuple[int, int, int, int]]]:
        self.ocr_calls += 1
        raise AssertionError("服务器错误处理期间不应读取事件或结算 OCR")


def test_fight_skips_all_normal_recognition_when_server_error_is_handled(monkeypatch) -> None:
    battle_module = importlib.import_module("tasks.battle.battle")
    fake_auto = _FightServerErrorAuto(stop_after_next_frame=True)
    handler_calls: list[None] = []

    monkeypatch.setattr(battle_module, "auto", fake_auto)
    monkeypatch.setattr(
        battle_module,
        "handle_server_error_dialog",
        lambda: handler_calls.append(None) or True,
    )

    with pytest.raises(StopIteration):
        battle_module.Battle(is_tool=True).fight()

    assert handler_calls == [None]
    assert fake_auto.find_calls == 0
    assert fake_auto.ocr_calls == 0


def test_fight_returns_false_when_server_error_restarts_game(monkeypatch) -> None:
    battle_module = importlib.import_module("tasks.battle.battle")
    fake_auto = _FightServerErrorAuto()

    monkeypatch.setattr(battle_module, "auto", fake_auto)
    monkeypatch.setattr(battle_module, "handle_server_error_dialog", lambda: False)

    assert battle_module.Battle(is_tool=True).fight() is False
    assert fake_auto.find_calls == 0
    assert fake_auto.ocr_calls == 0


@pytest.mark.parametrize("entrypoint_name", ["EXP_luxcavation", "thread_luxcavation"])
def test_luxcavation_returns_false_when_server_error_restarts_game(
    monkeypatch,
    entrypoint_name: str,
) -> None:
    import tasks.daily.luxcavation as luxcavation

    class FakeTaskAuto:
        model = ""

        def __init__(self) -> None:
            self.find_calls = 0
            self.screenshots = 0

        def take_screenshot_with_color(self) -> object:
            self.screenshots += 1
            if self.screenshots == 2:
                raise AssertionError("服务器重启后入口循环不应继续到下一帧")
            return object()

        def find_element(self, *_args, **_kwargs) -> None:
            self.find_calls += 1
            raise AssertionError("重启游戏后不应执行采光入口识图")

    fake_auto = FakeTaskAuto()
    monkeypatch.setattr(luxcavation, "auto", fake_auto)
    monkeypatch.setattr(luxcavation, "handle_server_error_dialog", lambda: False)

    assert getattr(luxcavation, entrypoint_name)() is False
    assert fake_auto.find_calls == 0
