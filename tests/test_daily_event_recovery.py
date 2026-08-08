from __future__ import annotations

import importlib

import pytest

from tasks.event_page import (
    EventPageResolution,
    find_event_choice_positions,
    is_event_choice_page,
    resolve_event_page,
)


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


def test_is_event_choice_page_requires_the_ocr_choice_title() -> None:
    assert is_event_choice_page([_entry(" 选 项 ", (900, 145, 990, 173))]) is True
    assert is_event_choice_page([_entry("第二个候选", (920, 374, 1022, 402))]) is False


def test_find_event_choice_positions_uses_right_choice_column_only() -> None:
    entries = [
        _entry("选项", (900, 145, 990, 173)),
        _entry("00:00:00:30", (120, 160, 210, 186)),
        _entry("献上土偶。", (920, 250, 1021, 279)),
        _entry("献上罪人。", (920, 374, 1022, 402)),
        _entry("有很多方法可以使场面平静下来，", (120, 422, 377, 450)),
        _entry("但供奉祭品似乎是这个异想体最喜欢的方法。", (120, 451, 487, 479)),
        _entry("一股鲜血似乎可以将其安抚。", (120, 479, 352, 507)),
        _entry("SKIP", (1380, 796, 1455, 824)),
    ]

    assert find_event_choice_positions(entries) == [(970, 264), (971, 388)]


class _ChoiceFallbackAuto:
    def __init__(
        self,
        ocr_frames: list[list[tuple[str, tuple[int, int, int, int]]]],
    ) -> None:
        self._ocr_frames = ocr_frames
        self._frame = 0
        self.choice_template_clicks = 0
        self.template_call_frames: list[int] = []
        self.click_element_calls: list[tuple[str, int]] = []
        self.choice_page_check_frames: list[int] = []
        self.clicks: list[tuple[int, int]] = []
        self.sleeps: list[float] = []
        self.template_click_result = True
        self.choice_template_visible_frames: set[int] | None = None
        self.choice_page_template_visible_frames: set[int] | None = None
        self.stop_when_frames_exhausted = False
        self.stop_when_choice_page_disappears = False
        self.unexpected_event_actions: list[str] = []
        self.sleep_frames: list[int] = []
        self.click_frames: list[int] = []

    def take_screenshot_with_color(self) -> object:
        self._frame += 1
        if self.stop_when_frames_exhausted and self._frame > len(self._ocr_frames):
            raise StopIteration
        return object()

    def get_restore_time(self) -> None:
        return None

    def find_element(self, asset: str, **_kwargs) -> bool:
        if asset == "event/choices_assets.png":
            self.choice_page_check_frames.append(self._frame)
            is_visible = self._frame <= len(self._ocr_frames) and (
                self.choice_page_template_visible_frames is None
                or self._frame in self.choice_page_template_visible_frames
            )
            if self.stop_when_choice_page_disappears and not is_visible:
                raise StopIteration
            return is_visible
        if asset == "event/select_first_option_assets.png":
            return self._frame <= len(self._ocr_frames) and (
                self.choice_template_visible_frames is None
                or self._frame in self.choice_template_visible_frames
            )
        return False

    def click_element(self, asset: str, **_kwargs) -> bool:
        self.click_element_calls.append((asset, self._frame))
        if asset == "event/select_first_option_assets.png":
            self.choice_template_clicks += 1
            self.template_call_frames.append(self._frame)
            return self.template_click_result
        if asset.startswith("event/"):
            self.unexpected_event_actions.append(asset)
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
        self.click_frames.append(self._frame)

    def mouse_to_blank(self) -> None:
        return None


def _run_choice_fallback_fight(
    monkeypatch: pytest.MonkeyPatch,
    ocr_frames: list[list[tuple[str, tuple[int, int, int, int]]]],
    *,
    template_click_result: bool = True,
    choice_template_visible_frames: set[int] | None = None,
    choice_page_template_visible_frames: set[int] | None = None,
    stop_when_frames_exhausted: bool = False,
    stop_when_choice_page_disappears: bool = False,
    is_tool: bool = True,
) -> _ChoiceFallbackAuto:
    battle_module = importlib.import_module("tasks.battle.battle")
    fake_auto = _ChoiceFallbackAuto(ocr_frames)
    fake_auto.template_click_result = template_click_result
    fake_auto.choice_template_visible_frames = choice_template_visible_frames
    fake_auto.choice_page_template_visible_frames = choice_page_template_visible_frames
    fake_auto.stop_when_frames_exhausted = stop_when_frames_exhausted
    fake_auto.stop_when_choice_page_disappears = stop_when_choice_page_disappears

    def record_sleep(seconds: float) -> None:
        fake_auto.sleeps.append(seconds)
        fake_auto.sleep_frames.append(fake_auto._frame)

    monkeypatch.setattr(battle_module, "auto", fake_auto)
    monkeypatch.setattr(battle_module, "handle_server_error_dialog", lambda: None)
    monkeypatch.setattr(battle_module, "sleep", record_sleep)
    monkeypatch.setattr(battle_module, "retry", lambda: True)

    if stop_when_frames_exhausted or stop_when_choice_page_disappears:
        with pytest.raises(StopIteration):
            battle_module.Battle(is_tool=is_tool).fight()
    else:
        battle_module.Battle(is_tool=is_tool).fight()
    return fake_auto


def _choice_entries(*choice_entries: tuple[str, tuple[int, int, int, int]]):
    return [
        _entry("选项", (900, 145, 990, 173)),
        *choice_entries,
        _entry("左侧剧情描述", (120, 422, 377, 450)),
        _entry("SKIP", (1380, 796, 1455, 824)),
    ]


def test_fight_tracks_choice_candidates_by_stable_slot_when_the_first_option_appears_late(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first_frame = _choice_entries(_entry("第二个候选", (920, 374, 1022, 402)))
    second_frame = _choice_entries(
        _entry("第一个候选", (920, 250, 1021, 279)),
        _entry("第二个候选", (920, 374, 1022, 402)),
    )

    fake_auto = _run_choice_fallback_fight(
        monkeypatch,
        [first_frame, second_frame],
        template_click_result=False,
        stop_when_frames_exhausted=True,
    )

    assert fake_auto.choice_template_clicks == 1
    assert fake_auto.clicks == [(971, 388)]
    assert fake_auto.click_frames == [1]
    assert fake_auto.sleep_frames == [2]


def test_fight_keeps_ocr_choice_state_when_choice_template_temporarily_disappears(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    choice_frame = _choice_entries(
        _entry("第一个候选", (920, 250, 1021, 279)),
        _entry("第二个候选", (920, 374, 1022, 402)),
    )

    fake_auto = _run_choice_fallback_fight(
        monkeypatch,
        [choice_frame, choice_frame],
        template_click_result=False,
        choice_page_template_visible_frames={1},
        stop_when_frames_exhausted=True,
    )

    assert fake_auto.clicks == [(971, 388)]
    assert fake_auto.unexpected_event_actions == []
    assert fake_auto.sleep_frames == [2]


def test_fight_never_random_clicks_while_ocr_still_identifies_choice_page(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    choice_frame = _choice_entries(
        _entry("第一个候选", (920, 250, 1021, 279)),
        _entry("第二个候选", (920, 374, 1022, 402)),
    )

    fake_auto = _run_choice_fallback_fight(
        monkeypatch,
        [choice_frame, choice_frame],
        template_click_result=False,
        choice_page_template_visible_frames={1},
        stop_when_frames_exhausted=True,
        is_tool=False,
    )

    assert fake_auto.clicks == [(971, 388)]
    assert fake_auto.unexpected_event_actions == []
    assert fake_auto.sleep_frames == [2]


def test_fight_waits_for_a_new_choice_frame_after_default_template_click(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    choice_frame = _choice_entries(
        _entry("第一个候选", (920, 250, 1021, 279)),
        _entry("第二个候选", (920, 374, 1022, 402)),
    )

    fake_auto = _run_choice_fallback_fight(
        monkeypatch,
        [choice_frame, choice_frame],
        stop_when_frames_exhausted=True,
    )

    assert fake_auto.template_call_frames == [1]
    assert fake_auto.clicks == [(971, 388)]
    assert fake_auto.click_frames == [2]
    assert fake_auto.unexpected_event_actions == []


def test_fight_does_not_try_ocr_or_other_event_actions_after_default_choice_leaves_page(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    choice_frame = _choice_entries(
        _entry("第一个候选", (920, 250, 1021, 279)),
        _entry("第二个候选", (920, 374, 1022, 402)),
    )

    fake_auto = _run_choice_fallback_fight(
        monkeypatch,
        [choice_frame, []],
        choice_page_template_visible_frames={1},
        stop_when_choice_page_disappears=True,
    )

    assert fake_auto.choice_page_check_frames == [1, 2]
    assert fake_auto.template_call_frames == [1]
    assert fake_auto.clicks == []
    assert fake_auto.unexpected_event_actions == []


def test_fight_does_not_click_unrelated_text_when_only_default_choice_is_ocr_visible(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    choice_frame = _choice_entries(_entry("唯一候选", (920, 250, 1021, 279)))

    fake_auto = _run_choice_fallback_fight(monkeypatch, [choice_frame, choice_frame])

    assert fake_auto.clicks == [(1400, 700)]


def test_fight_marks_failed_default_choice_before_clicking_next_ocr_candidate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    choice_frame = _choice_entries(
        _entry("第一个候选", (920, 250, 1021, 279)),
        _entry("第二个候选", (920, 374, 1022, 402)),
    )

    fake_auto = _run_choice_fallback_fight(
        monkeypatch,
        [choice_frame, choice_frame],
        template_click_result=False,
        stop_when_frames_exhausted=True,
    )

    assert fake_auto.template_call_frames == [1]
    assert fake_auto.clicks == [(971, 388)]
    assert fake_auto.click_frames == [1]


def test_fight_skips_default_ocr_candidate_that_appears_after_template_attempt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidates_frame = _choice_entries(
        _entry("第一个候选", (920, 250, 1021, 279)),
        _entry("第二个候选", (920, 374, 1022, 402)),
    )

    fake_auto = _run_choice_fallback_fight(
        monkeypatch,
        [_choice_entries(), candidates_frame],
        template_click_result=False,
        stop_when_frames_exhausted=True,
    )

    assert fake_auto.choice_template_clicks == 1
    assert fake_auto.clicks == [(971, 388)]


def test_fight_waits_after_failed_default_choice_with_one_ocr_candidate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    choice_frame = _choice_entries(_entry("唯一候选", (920, 250, 1021, 279)))

    fake_auto = _run_choice_fallback_fight(
        monkeypatch,
        [choice_frame, choice_frame],
        template_click_result=False,
        stop_when_frames_exhausted=True,
    )

    assert fake_auto.choice_template_clicks == 1
    assert fake_auto.clicks == []
    assert fake_auto.sleeps


def test_fight_does_not_run_other_event_actions_when_choice_template_disappears(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    choice_frame = _choice_entries(
        _entry("第一个候选", (920, 250, 1021, 279)),
        _entry("第二个候选", (920, 374, 1022, 402)),
    )

    fake_auto = _run_choice_fallback_fight(
        monkeypatch,
        [choice_frame, choice_frame, choice_frame],
        template_click_result=False,
        choice_template_visible_frames={1, 2},
        stop_when_frames_exhausted=True,
    )

    assert fake_auto.clicks == [(971, 388)]
    assert fake_auto.unexpected_event_actions == []
    assert fake_auto.sleeps


def test_fight_waits_after_all_ocr_choice_candidates_are_attempted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    choice_frame = _choice_entries(
        _entry("第一个候选", (920, 250, 1021, 279)),
        _entry("第二个候选", (920, 374, 1022, 402)),
    )

    fake_auto = _run_choice_fallback_fight(
        monkeypatch,
        [choice_frame, choice_frame, choice_frame],
        template_click_result=False,
        stop_when_frames_exhausted=True,
    )

    assert fake_auto.choice_template_clicks == 1
    assert fake_auto.clicks == [(971, 388)]
    assert fake_auto.sleeps


class _FightEventAuto:
    def __init__(self, ocr_frames: list[list[tuple[str, tuple[int, int, int, int]]]]) -> None:
        self._ocr_frames = ocr_frames
        self._frame = 0
        self.clicks: list[tuple[int, int]] = []

    def take_screenshot_with_color(self) -> object:
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
    monkeypatch.setattr(battle_module, "handle_server_error_dialog", lambda: None)
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


class _DailyEntryAuto:
    model = ""

    def __init__(self, *, enter_team_after_frame: int | None) -> None:
        self._enter_team_after_frame = enter_team_after_frame
        self.frames = 0

    def take_screenshot_with_color(self) -> object:
        self.frames += 1
        return object()

    def find_element(self, asset: str, **_kwargs) -> bool:
        return asset == "teams/identify_assets.png" and (
            self._enter_team_after_frame is not None
            and self.frames >= self._enter_team_after_frame
        )

    def click_element(self, *_args, **_kwargs) -> bool:
        return False

    def mouse_to_blank(self) -> None:
        return None


@pytest.mark.parametrize("entrypoint_name", ["EXP_luxcavation", "thread_luxcavation"])
def test_luxcavation_recovers_once_then_retries_entry_search(
    monkeypatch: pytest.MonkeyPatch,
    entrypoint_name: str,
) -> None:
    luxcavation = importlib.import_module("tasks.daily.luxcavation")
    fake_auto = _DailyEntryAuto(enter_team_after_frame=32)
    recovery_calls: list[str] = []

    monkeypatch.setattr(luxcavation, "auto", fake_auto)
    monkeypatch.setattr(luxcavation, "sleep", lambda _seconds: None)
    monkeypatch.setattr(luxcavation, "handle_server_error_dialog", lambda: None)
    monkeypatch.setattr(
        luxcavation,
        "back_init_menu",
        lambda: recovery_calls.append("recover") or True,
        raising=False,
    )

    assert getattr(luxcavation, entrypoint_name)() is True
    assert recovery_calls == ["recover"]
    assert fake_auto.frames == 32


@pytest.mark.parametrize("entrypoint_name", ["EXP_luxcavation", "thread_luxcavation"])
def test_luxcavation_stops_when_entry_recovery_fails(
    monkeypatch: pytest.MonkeyPatch,
    entrypoint_name: str,
) -> None:
    luxcavation = importlib.import_module("tasks.daily.luxcavation")
    fake_auto = _DailyEntryAuto(enter_team_after_frame=None)
    recovery_calls: list[str] = []

    monkeypatch.setattr(luxcavation, "auto", fake_auto)
    monkeypatch.setattr(luxcavation, "sleep", lambda _seconds: None)
    monkeypatch.setattr(luxcavation, "handle_server_error_dialog", lambda: None)
    monkeypatch.setattr(
        luxcavation,
        "back_init_menu",
        lambda: recovery_calls.append("recover") or False,
        raising=False,
    )

    assert getattr(luxcavation, entrypoint_name)() is False
    assert recovery_calls == ["recover"]
    assert fake_auto.frames == 31


@pytest.mark.parametrize("entrypoint_name", ["EXP_luxcavation", "thread_luxcavation"])
def test_luxcavation_stops_after_second_entry_search_exhaustion(
    monkeypatch: pytest.MonkeyPatch,
    entrypoint_name: str,
) -> None:
    luxcavation = importlib.import_module("tasks.daily.luxcavation")
    fake_auto = _DailyEntryAuto(enter_team_after_frame=None)
    recovery_calls: list[str] = []

    monkeypatch.setattr(luxcavation, "auto", fake_auto)
    monkeypatch.setattr(luxcavation, "sleep", lambda _seconds: None)
    monkeypatch.setattr(luxcavation, "handle_server_error_dialog", lambda: None)
    monkeypatch.setattr(
        luxcavation,
        "back_init_menu",
        lambda: recovery_calls.append("recover") or True,
        raising=False,
    )

    assert getattr(luxcavation, entrypoint_name)() is False
    assert recovery_calls == ["recover"]
    assert fake_auto.frames == 62
