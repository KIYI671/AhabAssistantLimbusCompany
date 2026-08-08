from __future__ import annotations

import importlib

import pytest

from tasks.event_page import EventPageResolution, resolve_event_page


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


class _BackInitMenuEventAuto:
    model = ""

    def __init__(
        self,
        ocr_frames: list[list[tuple[str, tuple[int, int, int, int]]]],
        *,
        home_after_event: bool = False,
        home_at_ocr_call: int | None = None,
    ) -> None:
        self._ocr_frames = ocr_frames
        self._home_after_event = home_after_event
        self._home_at_ocr_call = home_at_ocr_call
        self._ocr_calls = 0
        self.clicks: list[tuple[int, int]] = []
        self.blank_clicks = 0
        self.key_presses: list[str] = []

    def get_ocr_entries(self) -> list[tuple[str, tuple[int, int, int, int]]]:
        frame_index = min(self._ocr_calls, len(self._ocr_frames) - 1)
        self._ocr_calls += 1
        return self._ocr_frames[frame_index]

    def _is_home_ready(self) -> bool:
        if not self._home_after_event:
            return False
        if self._home_at_ocr_call is not None:
            return self._ocr_calls >= self._home_at_ocr_call
        return self._ocr_calls > 1

    def click_element(self, asset: str, **_kwargs) -> bool:
        return asset == "home/window_assets.png" and self._is_home_ready()

    def find_element(self, asset: str, **_kwargs) -> bool:
        return asset == "home/mail_assets.png" and self._is_home_ready()

    def mouse_click(self, x: int, y: int, **_kwargs) -> None:
        self.clicks.append((x, y))

    def mouse_click_blank(self) -> None:
        self.blank_clicks += 1

    def key_press(self, key: str) -> None:
        self.key_presses.append(key)


def test_back_init_menu_advances_event_page_before_returning_home(monkeypatch) -> None:
    back_init_menu_module = importlib.import_module("tasks.base.back_init_menu")
    fake_auto = _BackInitMenuEventAuto(
        [
            [
                _entry("判定成功", (500, 200, 700, 240)),
                _entry("继续", (680, 800, 760, 840)),
            ],
            [],
        ],
        home_after_event=True,
    )
    monkeypatch.setattr(back_init_menu_module, "auto", fake_auto)
    monkeypatch.setattr(back_init_menu_module, "ensure_simulator_game_started", lambda: False)
    monkeypatch.setattr(back_init_menu_module, "retry", lambda: True)
    monkeypatch.setattr(back_init_menu_module, "sleep", lambda _seconds: None)

    assert back_init_menu_module.back_init_menu(allow_restart=False) is True
    assert fake_auto.clicks == [(720, 820)]
    assert fake_auto.blank_clicks == 0
    assert fake_auto.key_presses == []


def test_back_init_menu_stops_after_event_wait_timeout_without_restart(monkeypatch) -> None:
    back_init_menu_module = importlib.import_module("tasks.base.back_init_menu")
    fake_auto = _BackInitMenuEventAuto([[_entry("判定成功", (500, 200, 700, 240))]])
    restart_calls: list[str] = []
    clock = iter((0.0, 0.0, 61.0))

    monkeypatch.setattr(back_init_menu_module, "auto", fake_auto)
    monkeypatch.setattr(back_init_menu_module, "ensure_simulator_game_started", lambda: False)
    monkeypatch.setattr(back_init_menu_module, "retry", lambda: True)
    monkeypatch.setattr(back_init_menu_module, "sleep", lambda _seconds: None)
    monkeypatch.setattr(back_init_menu_module, "monotonic", lambda: next(clock))
    monkeypatch.setattr(back_init_menu_module, "kill_game", lambda: restart_calls.append("kill"), raising=False)
    monkeypatch.setattr(back_init_menu_module, "restart_game", lambda: restart_calls.append("restart"), raising=False)

    assert back_init_menu_module.back_init_menu(allow_restart=False) is False
    assert restart_calls == []
    assert fake_auto.clicks == []
    assert fake_auto.blank_clicks == 0
    assert fake_auto.key_presses == []


def test_back_init_menu_resets_event_wait_after_allowed_restart(monkeypatch) -> None:
    back_init_menu_module = importlib.import_module("tasks.base.back_init_menu")
    retry_module = importlib.import_module("tasks.base.retry")
    fake_auto = _BackInitMenuEventAuto(
        [
            [_entry("判定成功", (500, 200, 700, 240))],
            [_entry("判定成功", (500, 200, 700, 240))],
            [_entry("判定成功", (500, 200, 700, 240))],
            [],
        ],
        home_after_event=True,
    )
    restart_calls: list[str] = []
    clock = iter((0.0, 0.0, 61.0, 62.0, 62.0))

    monkeypatch.setattr(back_init_menu_module, "auto", fake_auto)
    monkeypatch.setattr(back_init_menu_module, "ensure_simulator_game_started", lambda: False)
    monkeypatch.setattr(back_init_menu_module, "retry", lambda: True)
    monkeypatch.setattr(back_init_menu_module, "sleep", lambda _seconds: None)
    monkeypatch.setattr(back_init_menu_module, "monotonic", lambda: next(clock))
    monkeypatch.setattr(retry_module, "kill_game", lambda: restart_calls.append("kill"))
    monkeypatch.setattr(retry_module, "restart_game", lambda: restart_calls.append("restart"))

    assert back_init_menu_module.back_init_menu() is True
    assert restart_calls == ["kill", "restart"]


def _configure_back_init_menu_event_dependencies(
    monkeypatch: pytest.MonkeyPatch,
    back_init_menu_module,
    fake_auto: _BackInitMenuEventAuto,
) -> None:
    monkeypatch.setattr(back_init_menu_module, "auto", fake_auto)
    monkeypatch.setattr(back_init_menu_module, "ensure_simulator_game_started", lambda: False)
    monkeypatch.setattr(back_init_menu_module, "retry", lambda: True)
    monkeypatch.setattr(back_init_menu_module, "sleep", lambda _seconds: None)


def test_back_init_menu_keeps_waiting_for_event_result_past_loop_budget(monkeypatch) -> None:
    back_init_menu_module = importlib.import_module("tasks.base.back_init_menu")
    wait_frame = [_entry("判定成功", (500, 200, 700, 240))]
    fake_auto = _BackInitMenuEventAuto(
        [
            *([wait_frame] * 40),
            [
                _entry("判定成功", (500, 200, 700, 240)),
                _entry("继续", (680, 800, 760, 840)),
            ],
            [],
        ],
        home_after_event=True,
    )
    clock = iter([0.0, 0.0, *[float(second) for second in range(1, 40)]])
    _configure_back_init_menu_event_dependencies(monkeypatch, back_init_menu_module, fake_auto)
    monkeypatch.setattr(back_init_menu_module, "monotonic", lambda: next(clock))

    assert back_init_menu_module.back_init_menu(allow_restart=False) is True
    assert fake_auto.clicks == [(720, 820)]
    assert fake_auto.blank_clicks == 0
    assert fake_auto.key_presses == []


def test_back_init_menu_skips_event_ocr_when_server_error_recovery_fails(monkeypatch) -> None:
    back_init_menu_module = importlib.import_module("tasks.base.back_init_menu")
    fake_auto = _BackInitMenuEventAuto([[_entry("判定成功", (500, 200, 700, 240))]])
    monkeypatch.setattr(back_init_menu_module, "auto", fake_auto)
    monkeypatch.setattr(back_init_menu_module, "ensure_simulator_game_started", lambda: False)
    monkeypatch.setattr(back_init_menu_module, "retry", lambda: False)

    assert back_init_menu_module.back_init_menu(allow_restart=False) is False
    assert fake_auto._ocr_calls == 0


def test_back_init_menu_resets_event_wait_clock_after_non_event_frame(monkeypatch) -> None:
    back_init_menu_module = importlib.import_module("tasks.base.back_init_menu")
    fake_auto = _BackInitMenuEventAuto(
        [
            [_entry("判定成功", (500, 200, 700, 240))],
            [],
            [_entry("判定成功", (500, 200, 700, 240))],
            [
                _entry("判定成功", (500, 200, 700, 240)),
                _entry("继续", (680, 800, 760, 840)),
            ],
            [],
        ],
        home_after_event=True,
        home_at_ocr_call=5,
    )
    clock = iter((0.0, 0.0, 61.0, 61.0))
    _configure_back_init_menu_event_dependencies(monkeypatch, back_init_menu_module, fake_auto)
    monkeypatch.setattr(back_init_menu_module, "monotonic", lambda: next(clock))

    assert back_init_menu_module.back_init_menu(allow_restart=False) is True
    assert fake_auto.clicks == [(720, 820)]


def test_back_init_menu_handles_advance_without_position_as_bounded_wait(monkeypatch) -> None:
    back_init_menu_module = importlib.import_module("tasks.base.back_init_menu")
    fake_auto = _BackInitMenuEventAuto([[]])
    clock = iter((0.0, 0.0, 61.0))
    _configure_back_init_menu_event_dependencies(monkeypatch, back_init_menu_module, fake_auto)
    monkeypatch.setattr(back_init_menu_module, "monotonic", lambda: next(clock))
    monkeypatch.setattr(
        back_init_menu_module,
        "resolve_event_page",
        lambda _entries: EventPageResolution("advance", None, "damaged_result"),
    )

    assert back_init_menu_module.back_init_menu(allow_restart=False) is False
    assert fake_auto.clicks == []
    assert fake_auto.blank_clicks == 0
    assert fake_auto.key_presses == []
