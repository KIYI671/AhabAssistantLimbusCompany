"""Pause-driven input ownership and editable original route costs, offline."""
from upstream_reference import REFERENCE, original_source

import ast
import subprocess
import sys
from types import ModuleType
from unittest.mock import Mock, patch

import pytest
from PIL import Image
from pydantic import ValidationError
from test_added_options import schema
from test_optional_battle import ROOT, FakeAuto, actions, animation, battle_class_without_game_imports
from test_optional_route_event import load_policy

from tasks.battle.combat_hold import CombatSpeedHold
from tasks.battle.speed_hold import UnifiedSpeedHold
from utils.route_weights import DEFAULT_ROUTE_WEIGHTS


@pytest.mark.parametrize("height", [1080, 1440])
def test_pause_starts_one_center_hold_and_disappearance_releases(height):
    auto = FakeAuto(gears=False)
    auto.screenshot = Image.new("RGB", (round(height * 16 / 9), height))
    auto.elements["battle/pause_assets.png"] = (80, 80)
    hold = CombatSpeedHold(auto)
    assert hold.visible() and hold.update(True)
    assert hold.update(True)
    begins = [event for event in auto.events if event[0] == "begin"]
    assert len(begins) == 1
    assert begins[0][1:3] == (auto.screenshot.width / 2, height / 2)
    assert begins[0][3] == {"max_duration": 30}
    auto.elements.clear()
    assert not hold.visible() and not hold.update(False)
    assert not auto.held


@pytest.mark.parametrize("marker", ["battle/dead_all.png", "battle/battle_finish_confirm_assets.png",
    "mirror/road_in_mir/select_encounter_reward_card_assets.png", "mirror/road_in_mir/legend_assets.png",
    "event/choices_assets.png", "base/waiting_assets.png"])
def test_background_pause_does_not_hold_results_loading_or_events(marker):
    auto = FakeAuto(gears=False)
    auto.elements.update({"battle/pause_assets.png": (10, 10), marker: (20, 20)})
    hold = CombatSpeedHold(auto)
    assert not hold.visible() and not hold.update(hold.visible())
    assert not auto.events


def test_timeout_does_not_restart_until_pause_disappears():
    auto = FakeAuto(gears=False)
    hold = CombatSpeedHold(auto)
    with patch("tasks.battle.combat_hold.monotonic", return_value=1):
        assert hold.update(True)
    with patch("tasks.battle.combat_hold.monotonic", return_value=32):
        assert not hold.update(True)
        assert not hold.update(True)
        assert not auto.held and hold.blocked
        hold.update(False)
        assert hold.update(True)
    assert len([e for e in auto.events if e[0] == "begin"]) == 2
    hold.release()


def test_stop_and_input_exception_release_without_new_battle_inputs():
    auto, running = FakeAuto(gears=False), [True]
    hold = CombatSpeedHold(auto, lambda: running[0])
    assert hold.update(True)
    running[0] = False
    assert not hold.update(True) and not auto.held
    running[0] = True
    auto.mouse_keep_hold = Mock(side_effect=actions.userStopError("stop"))
    with pytest.raises(actions.userStopError):
        hold.update(True)
    assert not auto.held


def test_combat_only_cleanup_covers_early_return_and_exception():
    auto = FakeAuto(gears=False)
    @animation.optional_hold_cleanup(auto)
    def run(**kwargs):
        auto.mouse_begin_hold(100, 100)
        if kwargs.get("fail"):
            raise RuntimeError("frame failed")
        return "done"
    assert run(combat_speed_hold=True) == "done" and not auto.held
    with pytest.raises(RuntimeError):
        run(combat_speed_hold=True, fail=True)
    assert not auto.held


@pytest.mark.parametrize("ego_hold", [False, True])
def test_real_battle_loop_pause_hold_and_reward_release_with_both_switches(ego_hold):
    auto = FakeAuto(gears=False)
    frame = [0]
    def capture(**kwargs):
        frame[0] += 1
        assert frame[0] <= 5
        return auto.screenshot
    def find(path, **kwargs):
        if path == "battle/pause_assets.png" and frame[0] < 4:
            return (80, 80)
        if path.endswith("select_encounter_reward_card_assets.png") and frame[0] == 4:
            return (100, 100)
        return None
    auto.take_screenshot, auto.find_element = capture, find
    auto.get_restore_time = lambda: None
    auto.mouse_to_blank = Mock()
    auto.click_element = Mock(return_value=False)
    ns = battle_class_without_game_imports(ROOT / "tasks/battle/battle.py", auto)
    ns["UnifiedSpeedHold"] = UnifiedSpeedHold
    retry = ModuleType("tasks.base.retry")
    retry.check_times = lambda *args, **kwargs: False
    with patch.dict(sys.modules, {"tasks.base.retry": retry}):
        ns["Battle"](is_tool=True).fight(combat_speed_hold=True, rabbit_animation_hold=ego_hold)
    assert len([e for e in auto.events if e[0] == "begin"]) == 1
    assert not auto.held
    assert not any(e[0] in {"key", "chain"} for e in auto.events)
    clicks = [index for index, event in enumerate(auto.events) if event[0] == "click"]
    assert not clicks


def graph(module, weights=None):
    nodes = [[("event", (600, 253)), ("battle", (600, 690))], [("boss_battle", (1120, 690))]]
    result = module.RouteGraph(nodes, module.Row.MID, (80, 690), hard_mode=True, node_weights=weights)
    result.init_road([(1, module.Row.MID, module.Row.TOP), (1, module.Row.MID, module.Row.MID),
                      (2, module.Row.TOP, module.Row.MID), (2, module.Row.MID, module.Row.MID)])
    return result


def test_editing_costs_changes_original_total_weight_route_without_global_mutation():
    module, _, _ = load_policy("weighted_route_test", "tasks/mirror/search_road.py")
    original = dict(module.all_node_weight)
    assert graph(module).find_min_weight_route()[1][1].node_class == "event"
    assert graph(module, {"event": 100, "battle": 0}).find_min_weight_route()[1][1].node_class == "battle"
    assert module.all_node_weight == original
    assert graph(module).find_min_weight_route()[1][1].node_class == "event"


def test_synthetic_shop_boss_keep_original_terminal_costs_with_any_weight_table():
    module, _, _ = load_policy("synthetic_route_test", "tasks/mirror/search_road.py")
    for weights, expected in ((None, (1, 1)), ({"shop": 14, "boss_battle": 18}, (1, 1))):
        result = module.RouteGraph([], module.Row.MID, (80, 690), node_weights=weights)
        assert (result.columns["column2"][module.Row.MID].weight,
                result.columns["column3"][module.Row.MID].weight) == expected


@pytest.mark.parametrize("keyboard", [False, True])
def test_custom_costs_are_forwarded_to_planner_and_dispatched_by_original_input_mode(keyboard):
    module, auto, cfg = load_policy("dispatch_route_test", "tasks/mirror/search_road.py")
    module.sleep = lambda _: None
    cfg.mirror_keyboard_navigation = keyboard
    auto.find_element.return_value = (80, 690)
    auto.click_element.return_value = True
    weights = {"event": 99}
    road = module.MirrorMap(node_weights=weights)
    with patch.object(module, "search_road_from_road_map", return_value=(["D"], ["battle"])) as planner:
        step = road.get_next_step()
    planner.assert_called_once_with(hard_mode=False, node_weights=weights)
    assert road.enter_next_node(step)
    if keyboard:
        auto.key_press.assert_called_once_with("down")
        auto.mouse_click.assert_not_called()
    else:
        auto.mouse_click.assert_called_once()
        auto.key_press.assert_not_called()


@pytest.mark.parametrize("weights", [{"event": -1}, {"event": 1000}, {"event": True}, {"event": "4"}, {"unknown": 2}])
def test_invalid_costs_are_rejected(weights):
    with pytest.raises(ValidationError):
        schema.TeamSetting(route_node_weights=weights)


def test_weights_roundtrip_merge_defaults_and_remain_team_local():
    first = schema.TeamSetting(route_weights_enabled=True, route_node_weights={"event": 11})
    assert first.route_node_weights == {**DEFAULT_ROUTE_WEIGHTS, "event": 11}
    assert schema.TeamSetting.model_validate_json(first.model_dump_json()).model_dump() == first.model_dump()
    assert schema.TeamSetting().route_node_weights == DEFAULT_ROUTE_WEIGHTS


def test_original_route_algorithm_is_unchanged_and_experimental_elite_policy_is_removed():
    original = original_source("tasks/mirror/search_road.py")
    current = (ROOT / "tasks/mirror/search_road.py").read_text(encoding="utf-8")
    def method(source):
        graph_type = next(n for n in ast.parse(source).body if isinstance(n, ast.ClassDef) and n.name == "RouteGraph")
        return ast.dump(next(n for n in graph_type.body if isinstance(n, ast.FunctionDef) and n.name == "find_min_weight_route"))
    assert method(current) == method(original)
    assert "avoid_elites" not in current
