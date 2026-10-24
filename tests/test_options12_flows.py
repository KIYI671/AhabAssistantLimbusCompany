"""Floor cutoffs, map retry and defeat dialogs: no real input or game capture."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from PIL import Image
from pydantic import ValidationError

from test_added_options import schema
from test_optional_integration import function_from_source
from test_optional_migration import migration
from test_pack_observation import CandidateAuto, _selection_module
from tasks.mirror.failure_policy import DefeatDialogAction, forfeit_failed_run
from tasks.mirror.optional_recovery import theme_refresh_wait


@pytest.mark.parametrize("old,target", [(True, 3), (False, 5)])
def test_old_team_flag_import_and_global_migration(old, target):
    team = schema.TeamSetting(floor_3_exit=old)
    assert team.mirror_floor_limit == target
    assert "floor_3_exit" not in team.model_dump()
    assert "route_repeat_recovery" not in team.model_dump()
    data = {"floor_3_exit": True, "teams": {
        "1": {"floor_3_exit": old},
        "2": {"floor_3_exit": old, "mirror_floor_limit": 2},
    }}
    migration.migrate_global_battle_options(data)
    assert data["teams"]["1"]["mirror_floor_limit"] == target
    assert data["teams"]["2"]["mirror_floor_limit"] == 2
    assert "floor_3_exit" not in data["teams"]["1"]


def test_floor_schema_range_defaults_and_new_field_wins():
    assert schema.TeamSetting().mirror_floor_limit == 5
    for limit in range(1, 6):
        team = schema.TeamSetting(mirror_floor_limit=limit, floor_3_exit=True)
        assert team.mirror_floor_limit == limit
        assert schema.TeamSetting.model_validate_json(team.model_dump_json()) == team
    for limit in (0, 6):
        with pytest.raises(ValidationError):
            schema.TeamSetting(mirror_floor_limit=limit)
    defaults = {"1": {"mirror_floor_limit": 5}}
    migrated = migration.migrate_global_battle_options({"floor_3_exit": True}, defaults)
    assert migrated["teams"]["1"]["mirror_floor_limit"] == 3
    assert defaults["1"]["mirror_floor_limit"] == 5
    assert "route_repeat_recovery" not in schema.TeamSetting(route_repeat_recovery=False).model_dump()


class Selected(Exception):
    pass


def run_pack_boundary(limit, current_floor):
    state = ["pack"]
    calls = []
    auto = Mock(screenshot=Image.new("L", (1920, 1080)))
    frames = [0]
    def capture():
        frames[0] += 1
        assert frames[0] < 20
        return auto.screenshot
    def find(path, **kwargs):
        return ((state[0] == "pack" and path.endswith("feature_theme_pack_assets.png"))
                or (state[0] == "home" and path == "home/drive_assets.png"))
    transitions = {
        ("pack", "mirror/theme_pack/theme_pack_setting_assets.png"): "settings",
        ("settings", "mirror/road_in_mir/forfeit_assets.png"): "confirm",
        ("confirm", "mirror/road_in_mir/towindow&forfeit_confirm_assets.png"): "reward",
        ("reward", "battle/battle_finish_confirm_assets.png"): "claim",
        ("claim", "mirror/claim_reward/claim_rewards_confirm_assets.png"): "home",
    }
    def click(path, **kwargs):
        key = state[0], path
        if key not in transitions:
            return False
        state[0] = transitions[key]
        calls.append(path)
        return True
    auto.take_screenshot, auto.find_element, auto.click_element = capture, find, click
    namespace = dict(auto=auto, cfg=SimpleNamespace(), time=SimpleNamespace(time=lambda: 1),
                     sleep=Mock(), retry=lambda: True, log=Mock(), to_log_with_time=Mock(),
                     switch_theme_pack_difficulty=Mock(), select_theme_pack=Mock(side_effect=Selected),
                     PackObservationFailed=type("PackObservationFailed", (Exception,), {}))
    run = function_from_source("tasks/mirror/mirror.py", "run", namespace, "Mirror")
    instance = SimpleNamespace(mirror_floor_limit=limit, floor=0, floor_limit_exit=False,
                               route_recovery=None, observation_rules=None, LOOP_COUNT=250,
                               bequest_from_the_previous_game=False, observation_forfeit=False,
                               theme_pack_timing_start_count=0, current_floor_start_time=None, current_floor_time_complete=False, mirror_map=Mock(), _log_floor_time=Mock(), _record_run_statistics=Mock(return_value=True), battle_total_time=0, hard_mode=False,
                               system="burn", event_times=0, event_total_time=0, shop_total_time=0,
                               find_road_total_time=0, team_order=1, use_custom_theme_pack_weight=False,
                               _enter_hard_mode_if_needed=Mock())
    def read(_):
        instance.floor = current_floor
    namespace["get_floor"] = Mock(return_value=current_floor)
    namespace["ImageUtils"] = Mock()
    return run, instance, namespace, calls


@pytest.mark.parametrize("limit", range(1, 6))
def test_read_floor_then_exit_before_difficulty_or_pack_and_keep_rewards(limit):
    run, instance, namespace, calls = run_pack_boundary(limit, limit + 1)
    assert run(instance) is True
    assert instance.floor_limit_exit
    instance._enter_hard_mode_if_needed.assert_not_called()
    namespace["switch_theme_pack_difficulty"].assert_not_called()
    namespace["select_theme_pack"].assert_not_called()
    assert calls[-1].endswith("claim_rewards_confirm_assets.png")
    assert not any("claim_forfeit" in path for path in calls)


@pytest.mark.parametrize("limit,current", [(1, 1), (3, 3), (5, 5), (3, 0)])
def test_target_floor_itself_and_unknown_floor_do_not_trigger_early_exit(limit, current):
    run, instance, namespace, calls = run_pack_boundary(limit, current)
    with pytest.raises(Selected):
        run(instance)
    assert not instance.floor_limit_exit and not calls
    assert instance._enter_hard_mode_if_needed.call_count == int(current > 0)
    namespace["select_theme_pack"].assert_called_once()


@pytest.mark.parametrize("height", [720, 1080, 1440])
@pytest.mark.parametrize("retry", [True, False])
def test_defeat_coordinates_rescale_and_single_confirm(height, retry):
    scale = height / 1080
    auto = Mock(screenshot=Image.new("L", (int(height * 16 / 9), height)))
    auto.find_element.return_value = (973 * scale, 790 * scale)
    auto.click_element.return_value = True
    action = DefeatDialogAction()
    config = SimpleNamespace(set_win_size=height, mouse_action_interval=1.2)
    pauses = []
    assert action.submit(auto, retry=retry, config=config, pause=pauses.append)
    assert auto.mouse_click.call_args.args == pytest.approx((1189 * scale, (532 if retry else 670) * scale))
    assert not action.submit(auto, retry=retry, config=config, pause=pauses.append)
    auto.mouse_click.assert_called_once()
    auto.click_element.assert_called_once()
    assert pauses == [1.2, 1.2, 1.2]


def test_missing_confirmation_does_not_click_and_delayed_confirm_does_not_reselect():
    action, auto = DefeatDialogAction(), Mock(screenshot=Image.new("L", (1920, 1080)))
    cfg = SimpleNamespace(set_win_size=1080, mouse_action_interval=.5)
    auto.find_element.return_value = None
    assert not action.submit(auto, retry=True, config=cfg, pause=lambda _: None)
    auto.mouse_click.assert_not_called()
    auto.find_element.return_value = (973, 790)
    auto.click_element.side_effect = [False, True]
    assert not action.submit(auto, retry=True, config=cfg, pause=lambda _: None)
    assert action.submit(auto, retry=True, config=cfg, pause=lambda _: None)
    auto.mouse_click.assert_called_once()


def test_third_row_then_confirm_then_esc_and_original_forfeit_chain():
    state = ["defeat"]
    actions = []
    auto = Mock(screenshot=Image.new("L", (1920, 1080)))
    cfg = SimpleNamespace(set_win_size=1080, mouse_action_interval=.8)
    auto.take_screenshot.return_value = auto.screenshot
    def find(path, **kwargs):
        if state[0] == "defeat" and path == "battle/dead_all_confirm_assets.png":
            return (973, 790)
        if state[0] == "defeat" and path == "battle/dead_all.png":
            return (1200, 500)
        if state[0] == "home":
            return path in {"home/drive_assets.png", "home/mail_assets.png"}
        return state[0] == "reward" and path.endswith("battle_statistics_assets.png")
    transitions = {
        ("defeat", "battle/dead_all_confirm_assets.png"): "entry",
        ("settings", "mirror/road_in_mir/forfeit_assets.png"): "confirm_exit",
        ("confirm_exit", "mirror/road_in_mir/towindow&forfeit_confirm_assets.png"): "reward",
        ("reward", "mirror/claim_reward/claim_forfeit_assets.png"): "confirm_reward",
        ("confirm_reward", "mirror/claim_reward/claim_rewards_confirm_assets.png"): "home",
    }
    def click(path, **kwargs):
        key = state[0], path
        if key not in transitions:
            return False
        state[0] = transitions[key]
        actions.append(path)
        return True
    def keypress(key):
        actions.append(key)
        assert state[0] == "entry" and key == "esc"
        state[0] = "settings"
    auto.find_element, auto.click_element, auto.key_press = find, click, keypress
    auto.mouse_click.side_effect = lambda *point: actions.append(point)
    assert forfeit_failed_run(auto, Mock(), config=cfg, pause=lambda _: None, max_steps=15)
    assert actions[:3] == [(1189, 670), "battle/dead_all_confirm_assets.png", "esc"]
    assert actions[-2:] == ["mirror/claim_reward/claim_forfeit_assets.png",
                           "mirror/claim_reward/claim_rewards_confirm_assets.png"]
    auto.mouse_click.assert_called_once()
    assert not any("use_enkephalin" in str(action) for action in actions)


def test_stuck_defeat_confirmation_is_not_submitted_repeatedly_or_counted_complete():
    auto = Mock(screenshot=Image.new("L", (1920, 1080)))
    auto.take_screenshot.return_value = auto.screenshot
    auto.find_element.side_effect = lambda path, **kw: ((973, 790) if path.endswith("dead_all_confirm_assets.png")
                                                       else path == "battle/dead_all.png")
    auto.click_element.side_effect = lambda path, **kw: path.endswith("dead_all_confirm_assets.png")
    with pytest.raises(RuntimeError, match="尚未扣除次数"):
        forfeit_failed_run(auto, Mock(), pause=lambda _: None, max_steps=4)
    assert len([call for call in auto.click_element.call_args_list
                if call.args[0].endswith("dead_all_confirm_assets.png")]) == 1
    auto.key_press.assert_not_called()


@pytest.mark.parametrize("mouse,screenshot", [(0, 0), (.01, .01), (.2, 1.5), (2.0, .2), (3.5, .2), (.2, 3.5)])
def test_refresh_wait_is_at_least_two_seconds_and_respects_slower_settings(mouse, screenshot):
    value = theme_refresh_wait(SimpleNamespace(mouse_action_interval=mouse, screenshot_interval=screenshot))
    assert value == max(2.0, mouse or .5, screenshot or .85)
    assert value >= mouse and value >= screenshot


@pytest.mark.parametrize("observation", [False, True])
def test_refresh_wait_occurs_before_new_candidate_frame_in_both_flows(observation):
    auto = CandidateAuto([1] * 5, remaining=3)
    module = _selection_module(auto, {"A": 1}, threshold=2)
    module.cfg.mouse_action_interval = 1.8
    module.cfg.screenshot_interval = 2.2
    events = []
    original_capture = auto.take_screenshot
    auto.take_screenshot = lambda **kw: (events.append("capture") or original_capture(**kw))
    refreshed = [False]
    original_text = auto.find_language_text
    def text(*args, **kwargs):
        if refreshed[0] and args[0] == {"A": 1}:
            from test_pack_observation import TextMatchResult
            return TextMatchResult(3, "A")
        return original_text(*args, **kwargs)
    auto.find_language_text = text
    def click(path, **kwargs):
        if path.endswith("refresh_assets.png") and not refreshed[0]:
            refreshed[0] = True
            events.append("refresh")
            return True
        return False
    auto.click_element = click
    module.sleep = lambda duration: events.append(("wait", duration))
    module.select_theme_pack(floor=1, observation_rules=[[1, 1, 3]] if observation else None)
    index = events.index("refresh")
    assert events[index + 1] == ("wait", 2.2)
    assert events[index + 2] == "capture"
    auto.mouse_drag_down.assert_called_once()


def test_same_pack_page_retries_keep_official_one_floor_read_and_one_timer_start():
    run, instance, namespace, calls = run_pack_boundary(5, 1)
    instance.re_formation_each_floor = False
    namespace["select_theme_pack"].side_effect = [None, Selected()]
    with pytest.raises(Selected):
        run(instance)
    namespace["get_floor"].assert_called_once()
    instance.mirror_map.refresh_floor.assert_called_once_with(1, reset=True)
    assert instance.theme_pack_timing_start_count == 1
    instance._log_floor_time.assert_called_once()
