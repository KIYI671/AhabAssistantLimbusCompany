from __future__ import annotations

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
