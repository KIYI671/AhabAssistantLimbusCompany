"""Observation animation boundaries and removal of the added navigation keys."""
from upstream_reference import REFERENCE, original_source

import ast
import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import numpy as np
import pytest
from PIL import Image

from test_added_options import schema
from test_optional_integration import function_from_source
from test_optional_migration import migration
from test_pack_observation import OBSERVATION, ROOT


@pytest.mark.parametrize("old", [False, True])
def test_retired_recovery_is_removed_without_changing_other_settings(old):
    team = {"route_repeat_recovery": old, "mirror_floor_limit": 3, "rabbit_observe_rules": [[3, 2, 5]]}
    data = {"teams": {"1": team.copy()}}
    migration.migrate_global_battle_options(data)
    assert data["teams"]["1"] == {k: v for k, v in team.items() if k != "route_repeat_recovery"}
    assert "route_repeat_recovery" not in schema.TeamSetting(**team).model_dump()
    assert "route_repeat_recovery" not in schema.TeamSetting.model_fields


def test_original_two_up_keys_and_detection_of_enter_are_preserved():
    path = "tasks/mirror/search_road.py"
    original = original_source(path)
    def extract(text):
        return next(n for n in ast.parse(text).body if isinstance(n, ast.FunctionDef) and n.name == "search_road_simple_keyboard")
    assert ast.dump(extract(original)) == ast.dump(extract((ROOT / path).read_text(encoding="utf-8")))
    auto = Mock()
    enter = Mock(side_effect=[False, True])
    run = function_from_source(path, "search_road_simple_keyboard", {
        "cfg": SimpleNamespace(mirror_keyboard_navigation=True), "auto": auto,
        "sleep": Mock(), "log": Mock(), "_keyboard_enter_succeeded": enter,
    })
    assert run()
    assert [c.args for c in auto.key_press.call_args_list] == [("up",), ("up",)]
    assert enter.call_count == 2
    source = (ROOT / "tasks/mirror/mirror.py").read_text(encoding="utf-8")
    assert "route_recovery" not in source
    assert "RepeatRouteRecovery" not in (ROOT / "tasks/mirror/optional_recovery.py").read_text(encoding="utf-8")


@pytest.mark.parametrize("height", [720, 1080, 1440])
@pytest.mark.parametrize("column", [1, 2, 5])
def test_visible_second_row_stays_in_the_requested_card_without_scroll(height, column):
    scale = height / 1080
    auto = SimpleNamespace(screenshot=Image.new("L", (round(height * 16 / 9), height)), mouse_click=Mock())
    x, y = OBSERVATION.select_catalogue_card(auto, OBSERVATION.ObservationRule(3, 2, column), pause=lambda _: None)
    assert x == pytest.approx((964 + 176 * (column - 1)) * scale, abs=1)
    assert y == pytest.approx(750 * scale)
    auto.mouse_click.assert_called_once_with(x, y)


def test_swipe_keeps_overlap_and_starts_between_cards_then_uses_measured_shift():
    auto = SimpleNamespace(screenshot=Image.new("L", (1920, 1080)), mouse_click=Mock(),
                           mouse_swipe_for_scroll=Mock(), _run_ocr_for_text=lambda **_: ["观测第4阶层主题卡包"])
    with patch.object(OBSERVATION, "_wait_stable", return_value=True) as settle, \
         patch.object(OBSERVATION, "_fitted_scroll", return_value=-223):
        point = OBSERVATION.select_catalogue_card(auto, OBSERVATION.ObservationRule(4, 4, 2), pause=lambda _: None)
    assert auto.mouse_swipe_for_scroll.call_count == 3
    for call in auto.mouse_swipe_for_scroll.call_args_list:
        assert call.args == (1228, 740)
        assert call.kwargs["dy"] == -240
    assert settle.call_count == 3
    assert point == (1140, 750)


def test_wait_does_not_accept_a_moving_frame_or_repeat_stale_capture():
    rng = np.random.default_rng(64)
    frames = [Image.fromarray(rng.integers(0, 256, (80, 120), dtype=np.uint8)) for _ in range(4)]
    stream = iter([None, *frames[1:], frames[-1], frames[-1]])
    auto = SimpleNamespace(screenshot=frames[0])
    count = []
    def capture():
        count.append(1)
        value = next(stream)
        if value is not None:
            auto.screenshot = value
        return value
    auto.take_screenshot = capture
    assert OBSERVATION._wait_stable(auto, (0, 0, 120, 80), pause=lambda _: None)
    assert len(count) == 6


def test_perpetual_animation_is_bounded():
    rng = np.random.default_rng(65)
    auto = SimpleNamespace(screenshot=Image.new("L", (120, 80)))
    auto.take_screenshot = Mock(side_effect=lambda: setattr(auto, "screenshot", Image.fromarray(
        rng.integers(0, 256, (80, 120), dtype=np.uint8))) or auto.screenshot)
    assert not OBSERVATION._wait_stable(auto, (0, 0, 120, 80), pause=lambda _: None, max_frames=5)
    assert auto.take_screenshot.call_count == 5


def test_remaining_verbose_events_are_debug_only():
    targets = {
        "tasks/battle/optional_actions.py": "未找到完整EGO名称",
        "tasks/mirror/in_shop.py": "图片保护：跳过合成/出售材料",
        "tasks/base/script_task_scheme.py": "本局已放弃奖励并返回主界面",
    }
    for path, text in targets.items():
        tree = ast.parse((ROOT / path).read_text(encoding="utf-8"))
        calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and n.args and
                 text in ast.unparse(n.args[0]) and isinstance(n.func, ast.Attribute)]
        assert calls and all(n.func.attr == "debug" for n in calls), path


def test_cost_modal_wrapped_text_can_interleave_background_titles():
    assert OBSERVATION.replacement_modal([
        "主题卡包”伏行深渊”将被”吞噬的暴食”替", "压抑的暴怒", "沉迷的色欲", "换。",
    ])
    assert not OBSERVATION.replacement_modal(["主题卡包观测", "替换", "确认", "取消"])
