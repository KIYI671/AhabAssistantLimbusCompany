from __future__ import annotations

import importlib

import pytest

from tasks.event_page import resolve_event_page


def _entry(text: str, bounds: tuple[int, int, int, int]) -> tuple[str, tuple[int, int, int, int]]:
    return text, bounds


def test_resolve_event_page_advances_from_result_continue() -> None:
    result = resolve_event_page(
        [
            _entry("判定成功", (500, 200, 700, 240)),
            _entry("继续", (680, 800, 760, 840)),
        ]
    )

    assert result is not None
    assert result.state == "advance"
    assert result.position == (720, 820)
    assert result.reason == "continue"


def test_resolve_event_page_prefers_continue_over_other_event_actions() -> None:
    result = resolve_event_page(
        [
            _entry("进行判定", (680, 700, 840, 740)),
            _entry("判定成功", (500, 200, 700, 240)),
            _entry("继续", (680, 800, 760, 840)),
        ]
    )

    assert result is not None
    assert result.state == "advance"
    assert result.position == (720, 820)
    assert result.reason == "continue"


@pytest.mark.parametrize("result_text", ["判定成功", "判定失败"])
def test_resolve_event_page_waits_for_result_animation(
    result_text: str,
) -> None:
    result = resolve_event_page([_entry(result_text, (500, 200, 700, 240))])

    assert result is not None
    assert result.state == "wait"
    assert result.position is None


@pytest.mark.parametrize("context", ["事件", "判定", "选项"])
def test_resolve_event_page_advances_perform_check_for_each_event_context(
    context: str,
) -> None:
    result = resolve_event_page(
        [
            _entry(context, (450, 100, 550, 140)),
            _entry("进行判定", (680, 800, 840, 840)),
        ]
    )

    assert result is not None
    assert result.state == "advance"
    assert result.position == (760, 820)
    assert result.reason == "perform_check"


def test_resolve_event_page_ignores_normal_pages_and_ambiguous_continue() -> None:
    assert resolve_event_page([]) is None
    assert resolve_event_page([_entry("继续", (680, 800, 760, 840))]) is None
    assert resolve_event_page([_entry("战斗胜利", (500, 200, 700, 240))]) is None


@pytest.mark.parametrize(
    "button_text",
    [
        "进行判定：",
        "进行判定（消耗罪人）",
        "进行判定（事件）",
        "选项：进行判定",
    ],
)
def test_resolve_event_page_ignores_perform_check_variants_without_event_context(
    button_text: str,
) -> None:
    assert resolve_event_page([_entry(button_text, (680, 800, 840, 840))]) is None


def test_resolve_event_page_ignores_perform_check_without_event_context() -> None:
    assert resolve_event_page([_entry("进行判定", (680, 800, 840, 840))]) is None


def test_resolve_event_page_normalizes_whitespace() -> None:
    result = resolve_event_page(
        [
            _entry(" 判 定 成 功 ", (500, 200, 700, 240)),
            _entry("继 续", (680, 800, 760, 840)),
        ]
    )

    assert result is not None
    assert result.state == "advance"
    assert result.position == (720, 820)


class _FightEventAuto:
    def __init__(self, ocr_frames: list[list[tuple[str, tuple[int, int, int, int]]]]) -> None:
        self._ocr_frames = ocr_frames
        self._frame = 0
        self.clicks: list[tuple[int, int]] = []

    def take_screenshot(self) -> object:
        self._frame += 1
        return object()

    def get_restore_time(self) -> None:
        return None

    def find_element(self, *_args, **_kwargs) -> bool:
        return False

    def click_element(self, *_args, **_kwargs) -> bool:
        return False

    def find_language_text(self, zh_text: str, _en_text: str) -> tuple[int, int] | bool:
        if self._frame > len(self._ocr_frames):
            if zh_text == "战斗胜利":
                return 700, 700
            if zh_text == "确认":
                return 1400, 700
        return False

    def get_ocr_entries(self) -> list[tuple[str, tuple[int, int, int, int]]]:
        if self._frame <= len(self._ocr_frames):
            return self._ocr_frames[self._frame - 1]
        return []

    def mouse_click(self, x: int, y: int, **_kwargs) -> None:
        self.clicks.append((x, y))

    def mouse_to_blank(self) -> None:
        return None


def _run_daily_event_fight(
    monkeypatch: pytest.MonkeyPatch,
    ocr_frames: list[list[tuple[str, tuple[int, int, int, int]]]],
    *,
    init_chance: int | None = None,
) -> tuple[_FightEventAuto, list[None], list[None]]:
    battle_module = importlib.import_module("tasks.battle.battle")
    retry_calls: list[None] = []
    back_init_menu_calls: list[None] = []
    fake_auto = _FightEventAuto(ocr_frames)

    monkeypatch.setattr(battle_module, "auto", fake_auto)
    monkeypatch.setattr(battle_module, "sleep", lambda _seconds: None)
    monkeypatch.setattr(
        battle_module,
        "retry",
        lambda: retry_calls.append(None) or True,
    )
    back_init_menu_module = importlib.import_module("tasks.base.back_init_menu")
    monkeypatch.setattr(
        back_init_menu_module,
        "back_init_menu",
        lambda: back_init_menu_calls.append(None) or False,
    )

    battle = battle_module.Battle(is_tool=True)
    if init_chance is not None:
        battle.INIT_CHANCE = init_chance
    battle.fight()
    return fake_auto, retry_calls, back_init_menu_calls


def test_fight_advances_daily_event_result_from_ocr_then_settles(monkeypatch) -> None:
    fake_auto, retry_calls, back_init_menu_calls = _run_daily_event_fight(
        monkeypatch,
        [
            [
                _entry("判定成功", (500, 200, 700, 240)),
                _entry("继续", (680, 800, 760, 840)),
            ]
        ],
    )

    assert fake_auto.clicks == [(720, 820), (1400, 700)]
    assert retry_calls == []
    assert back_init_menu_calls == []


def test_fight_waits_for_daily_event_result_button_without_retry(monkeypatch) -> None:
    fake_auto, retry_calls, back_init_menu_calls = _run_daily_event_fight(
        monkeypatch,
        [
            [_entry("判定成功", (500, 200, 700, 240))],
            [
                _entry("判定成功", (500, 200, 700, 240)),
                _entry("继续", (680, 800, 760, 840)),
            ],
        ],
    )

    assert fake_auto.clicks == [(720, 820), (1400, 700)]
    assert retry_calls == []
    assert back_init_menu_calls == []


def test_fight_wait_result_resets_exhausted_chance_before_settlement(monkeypatch) -> None:
    fake_auto, retry_calls, back_init_menu_calls = _run_daily_event_fight(
        monkeypatch,
        [
            [],
            [_entry("判定成功", (500, 200, 700, 240))],
            [],
        ],
        init_chance=1,
    )

    assert fake_auto.clicks == [(1400, 700)]
    # 非事件帧会走现有循环末尾的无副作用重试检查，然后才减少 chance。
    assert retry_calls == [None, None]
    assert back_init_menu_calls == []


def test_fight_advance_result_resets_exhausted_chance_before_settlement(monkeypatch) -> None:
    fake_auto, retry_calls, back_init_menu_calls = _run_daily_event_fight(
        monkeypatch,
        [
            [],
            [
                _entry("判定成功", (500, 200, 700, 240)),
                _entry("继续", (680, 800, 760, 840)),
            ],
            [],
        ],
        init_chance=1,
    )

    assert fake_auto.clicks == [(720, 820), (1400, 700)]
    # 非事件帧会走现有循环末尾的无副作用重试检查，然后才减少 chance。
    assert retry_calls == [None, None]
    assert back_init_menu_calls == []
