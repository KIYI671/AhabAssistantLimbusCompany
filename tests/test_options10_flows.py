"""Merged options exercise real controllers, configuration and original exits."""

from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from test_added_options import make_shop, schema
from test_optional_battle import FakeAuto
from test_optional_integration import function_from_source
from tasks.battle import speed_hold
from tasks.battle.animation_hold import optional_hold_cleanup


def test_pause_animation_handoff_keeps_one_hold_and_one_shared_limit():
    auto = FakeAuto(gears=False)
    hold = speed_hold.UnifiedSpeedHold(auto)
    animation = [False]
    with patch.object(speed_hold, "corner_play_marker", side_effect=lambda _: animation[0]), \
            patch.object(speed_hold, "overclock_banner", return_value=False), \
            patch.object(speed_hold, "total_marker", return_value=False), \
            patch("tasks.battle.combat_hold.monotonic") as clock:
        clock.return_value = 1
        auto.elements["battle/pause_assets.png"] = (10, 10)
        assert hold.probe() and hold.combat_visible and auto.held
        auto.elements.clear()
        animation[0] = True
        clock.return_value = 20
        assert hold.probe() and not hold.combat_visible and auto.held
        clock.return_value = 32
        assert hold.probe() and not auto.held and hold.blocked
        auto.elements["battle/pause_assets.png"] = (10, 10)
        assert hold.probe() and not auto.held  # changing signals cannot renew the budget
        auto.elements.clear()
        animation[0] = False
        assert not hold.probe() and not hold.blocked
        animation[0] = True
        assert hold.probe() and auto.held
    assert len([e for e in auto.events if e[0] == "begin"]) == 2
    hold.release()


@pytest.mark.parametrize("marker", ["battle/dead_all.png", "battle/battle_finish_confirm_assets.png",
    "mirror/road_in_mir/select_encounter_reward_card_assets.png", "mirror/road_in_mir/acquire_ego_gift_card.png",
    "mirror/road_in_mir/legend_assets.png", "mirror/claim_reward/battle_statistics_assets.png",
    "event/choices_assets.png", "base/waiting_assets.png"])
def test_terminal_frame_releases_even_when_both_signals_remain(marker):
    auto = FakeAuto(gears=False)
    hold = speed_hold.UnifiedSpeedHold(auto)
    auto.elements["battle/pause_assets.png"] = (10, 10)
    assert hold.probe() and auto.held
    auto.elements[marker] = (20, 20)
    with patch.object(speed_hold, "corner_play_marker", return_value=True) as probe:
        assert not hold.probe() and not auto.held
        probe.assert_not_called()


def test_unified_flag_cleans_up_on_error():
    auto = FakeAuto()
    @optional_hold_cleanup(auto)
    def run(**kwargs):
        auto.mouse_begin_hold(100, 100)
        raise RuntimeError("failed capture")
    with pytest.raises(RuntimeError):
        run(speed_hold=True)
    assert not auto.held


def test_total_starts_hold_before_slower_banner_ocr():
    auto = FakeAuto(gears=False)
    hold = speed_hold.UnifiedSpeedHold(auto)
    with patch.object(speed_hold, "corner_play_marker", return_value=False), \
            patch.object(speed_hold, "visual_overclock", return_value=False), \
            patch.object(speed_hold, "total_marker", return_value=True), \
            patch.object(speed_hold, "overclock_banner", side_effect=AssertionError("unnecessary OCR")):
        assert hold.probe() and auto.held
    hold.release()


def test_gift_migration_unions_lists_and_new_empty_false_wins():
    old = dict(protect_gift_images=True, protected_gift_images=["a.png", "b.png"],
               specify_gift_images=False, specified_gift_images=["b.png", "c.png"])
    team = schema.TeamSetting(**old)
    assert team.gift_lock_enabled and team.gift_lock_images == ["a.png", "b.png", "c.png"]
    assert not set(old) & team.model_dump().keys()
    explicit = schema.TeamSetting(**old, gift_lock_enabled=False, gift_lock_images=[])
    assert not explicit.gift_lock_enabled and explicit.gift_lock_images == []
    assert schema.TeamSetting.model_validate_json(team.model_dump_json()) == team


def test_common_lock_list_reaches_purchase_fusion_sale_and_stays_team_local():
    shop, _, _ = make_shop(gift_lock_enabled=True, gift_lock_images=["needle.png", "stone.png"])
    assert shop.specify_gift_images and shop.protect_gift_images
    assert shop.specified_gift_images == shop.protected_gift_images == ("needle.png", "stone.png")
    other, _, _ = make_shop()
    assert not other.specify_gift_images and not other.protect_gift_images
    assert other.specified_gift_images == other.protected_gift_images == ()


@pytest.mark.parametrize("limit", range(1, 6))
def test_floor_limit_uses_current_team_and_original_reward_confirmation(limit):
    # Execute the complete production run: original menu -> forfeit exploration
    # -> standard reward confirmation -> home, with every external effect mocked.
    auto = Mock()
    stage = ["map"]
    captures = [0]
    calls = []
    def capture(**kwargs):
        captures[0] += 1
        assert captures[0] < 15
        return True
    def find(path, **kwargs):
        return stage[0] == "home" and path == "home/drive_assets.png"
    transitions = {
        ("map", "mirror/road_in_mir/setting_assets.png"): "settings",
        ("settings", "mirror/road_in_mir/forfeit_assets.png"): "confirm",
        ("confirm", "mirror/road_in_mir/towindow&forfeit_confirm_assets.png"): "reward",
        ("reward", "battle/battle_finish_confirm_assets.png"): "claim",
        ("claim", "mirror/claim_reward/claim_rewards_confirm_assets.png"): "home",
    }
    def click(path, **kwargs):
        key = (stage[0], path)
        if key in transitions:
            calls.append(key)
            stage[0] = transitions[key]
            return True
        return False
    auto.take_screenshot, auto.find_element, auto.click_element = capture, find, click
    namespace = dict(auto=auto, cfg=SimpleNamespace(), time=SimpleNamespace(time=lambda: 1),
                     sleep=lambda _: None, retry=lambda: True, log=Mock(), to_log_with_time=Mock(), ImageUtils=Mock())
    run = function_from_source("tasks/mirror/mirror.py", "run", namespace, "Mirror")
    instance = SimpleNamespace(mirror_floor_limit=limit, floor_limit_exit=False, route_recovery=None,
                               floor=limit + 1, LOOP_COUNT=250, bequest_from_the_previous_game=False,
                               observation_forfeit=False, current_floor_start_time=None, _record_run_statistics=Mock(return_value=True), battle_total_time=0,
                               system="burn", event_times=0, event_total_time=0, shop_total_time=0, find_road_total_time=0)
    assert run(instance) is True
    assert [key[1] for key in calls] == [key[1] for key in transitions]
    assert not any("claim_forfeit" in path for _, path in calls)


def test_team_exit_setting_does_not_read_retired_global_in_any_runtime_branch():
    from test_optional_battle import ROOT
    text = (ROOT / "tasks/mirror/mirror.py").read_text(encoding="utf-8")
    assert "cfg.floor_3_exit" not in text
    assert "self.floor_3_exit" not in text
    assert "self.mirror_floor_limit = team_setting.mirror_floor_limit" in text
    assert "and not self.floor_limit_exit" in text
