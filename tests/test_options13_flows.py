"""No-reward entry coverage and settlement transitions; all game I/O is fake."""

import ast
import zipfile
from functools import partial
from types import MethodType, SimpleNamespace
from unittest.mock import Mock

import pytest
from PIL import Image

from test_optional_battle import ROOT
from test_optional_integration import function_from_source
from tasks.mirror.developer_rewards import reward_page_visible
from tasks.mirror.failure_policy import forfeit_failed_run, MirrorBattleAttemptsExhausted
from tasks.mirror.observation_failure import MirrorRunOutcome, ObservationCleanupError
from tasks.mirror.settlement import ExplorationExit, settlement_wait


class NoRewardScreen:
    def __init__(self):
        self.phase = "statistics"
        self.events = []
        self.screenshot = Image.new("L", (1920, 1080))
        self.wait_pause = Mock()
        self.mouse_to_blank = Mock()
        self.find_language_text = Mock(return_value=None)

    def take_screenshot(self, **kwargs):
        self.events.append(("capture", self.phase))
        assert len(self.events) < 100
        return self.screenshot

    def find_element(self, path, **kwargs):
        if self.phase == "home":
            return path in {"home/drive_assets.png", "home/mail_assets.png"}
        if path.endswith("battle_statistics_assets.png"):
            return self.phase in {"statistics", "overview"}
        if path.endswith("complete_mirror_100%_assets.png"):
            return self.phase in {"statistics", "overview"}
        return False

    def click_element(self, path, **kwargs):
        assert not path.endswith("use_enkephalin_assets.png"), "Module/payment action attempted"
        if path.endswith("claim_rewards_confirm_assets.png"):
            assert self.phase == "forfeit_confirm", "Reward confirmation before explicit forfeit"
        transitions = {
            ("statistics", "battle/battle_finish_confirm_assets.png"): "overview",
            ("overview", "mirror/claim_reward/claim_rewards_assets.png"): "choice",
            ("choice", "mirror/claim_reward/claim_forfeit_assets.png"): "forfeit_confirm",
            ("forfeit_confirm", "mirror/claim_reward/claim_rewards_confirm_assets.png"): "home",
        }
        key = self.phase, path
        if key not in transitions:
            return False
        self.events.append(("click", path))
        self.phase = transitions[key]
        return True


def mirror_fixture(*, floor=5, limit=5, reason="completed", times=None):
    auto = NoRewardScreen()
    config = SimpleNamespace(disable_mirror_rewards=True, mouse_action_interval=.1, screenshot_interval=.1)
    namespace = dict(auto=auto, cfg=config, battle=SimpleNamespace(running=True),
                     log=Mock(), time=SimpleNamespace(time=lambda: 100), retry=lambda: True, sleep=lambda _: None,
                     reward_page_visible=reward_page_visible, MirrorRunOutcome=MirrorRunOutcome, ImageUtils=Mock(),
                     forfeit_failed_run=partial(forfeit_failed_run, pause=lambda _: None, max_steps=20))
    instance = SimpleNamespace(floor=floor, mirror_floor_limit=limit, floor_limit_exit=reason == "floor_limit",
                               observation_forfeit=reason == "observation_failed",
                               bequest_from_the_previous_game=reason == "previous_settlement", LOOP_COUNT=250,
                               start_time=1, _record_run_statistics=Mock(return_value=True), _record_long_term_log=Mock())
    for name in ("_complete_without_rewards", "record_developer_result"):
        setattr(instance, name, MethodType(function_from_source("tasks/mirror/mirror.py", name, namespace, "Mirror"), instance))
    run = function_from_source("tasks/mirror/mirror.py", "run", namespace, "Mirror")
    return auto, config, namespace, instance, run


@pytest.mark.parametrize("floor,limit,reason", [(5,5,"completed"), (4,3,"floor_limit"),
                                               (2,3,"observation_failed"), (3,3,"previous_settlement")])
def test_developer_run_entry_forfeits_then_uses_original_statistics(floor, limit, reason):
    auto, _, _, instance, run = mirror_fixture(floor=floor, limit=limit, reason=reason)
    assert run(instance) is MirrorRunOutcome.DEVELOPER_NO_REWARDS
    assert auto.phase == "home"
    assert [e[1] for e in auto.events if e[0] == "click"] == [
        "battle/battle_finish_confirm_assets.png", "mirror/claim_reward/claim_rewards_assets.png",
        "mirror/claim_reward/claim_forfeit_assets.png", "mirror/claim_reward/claim_rewards_confirm_assets.png"]
    instance._record_run_statistics.assert_called_once_with(1, count_complete=reason in {"completed", "floor_limit"})


def test_incomplete_result_does_not_increment_original_success_statistics():
    auto, _, _, instance, run = mirror_fixture()
    original_find = auto.find_element
    auto.find_element = lambda path, **kw: False if path.endswith("complete_mirror_100%_assets.png") else original_find(path, **kw)
    assert run(instance) is MirrorRunOutcome.DEVELOPER_NO_REWARDS
    instance._record_run_statistics.assert_called_once_with(1, count_complete=False)


def test_legacy_reward_method_and_startup_handoff_are_guarded_before_claiming():
    auto, _, ns, instance, _ = mirror_fixture(reason="previous_settlement")
    method = function_from_source("tasks/mirror/mirror.py", "get_reward_in_road", ns, "Mirror")
    assert method(instance) is MirrorRunOutcome.DEVELOPER_NO_REWARDS
    assert auto.phase == "home"
    auto.phase = "statistics"
    method = function_from_source("tasks/mirror/mirror.py", "road_to_mir", ns, "Mirror")
    assert method(instance) is True and instance.bequest_from_the_previous_game
    assert auto.phase == "statistics"  # only hands off; cannot pay or claim


def test_cleanup_failure_never_records_or_counts_a_developer_run():
    _, _, ns, instance, _ = mirror_fixture()
    ns["forfeit_failed_run"] = Mock(side_effect=RuntimeError("unconfirmed"))
    with pytest.raises(RuntimeError, match="unconfirmed"):
        instance._complete_without_rewards("completed")
    instance._record_run_statistics.assert_not_called()


def test_developer_schedule_ignores_save_rewards_limit_and_deducts_only_planned_runs():
    config = SimpleNamespace(set_mirror_count=2, infinite_dungeons=False, save_rewards=True, hard_mirror=True,
        disable_mirror_rewards=True, re_claim_rewards=True, teams_active_queue=[1],
        config=SimpleNamespace(teams={"1":SimpleNamespace(fixed_team_use=False)}),
        normalize_and_sync_team_state=Mock(), get_value=lambda _: [True], rotate_team_queue=Mock())
    changes = []
    def save(key, value):
        changes.append((key, value))
        setattr(config, key, value)
    config.set_value = save
    process = Mock(return_value=MirrorRunOutcome.DEVELOPER_NO_REWARDS)
    ns = dict(cfg=config, mediator=SimpleNamespace(mirror_signal=Mock(),mirror_bar_kill_signal=Mock()),
              log=Mock(), onetime_mir_process=process, MirrorRunOutcome=MirrorRunOutcome, to_get_reward=Mock())
    task = function_from_source("tasks/base/script_task_scheme.py", "Mirror_task", ns)
    task()
    assert process.call_count == 2
    assert changes == [("set_mirror_count", 1), ("set_mirror_count", 0)]
    assert config.rotate_team_queue.call_count == 2
    ns["to_get_reward"].assert_not_called()


def test_attempts_exhausted_records_only_after_original_abandonment_confirmed():
    adventure = Mock(observation_forfeit=False)
    adventure.run.side_effect = MirrorBattleAttemptsExhausted("limit")
    adventure.record_developer_result.return_value = MirrorRunOutcome.DEVELOPER_NO_REWARDS
    cleanup = Mock(return_value=True)
    ns = dict(cfg=SimpleNamespace(auto_hard_mirror=False,disable_mirror_rewards=True), Mirror=Mock(return_value=adventure),
              TeamSetting=object, MirrorRunOutcome=MirrorRunOutcome, MirrorBattleAttemptsExhausted=MirrorBattleAttemptsExhausted,
              ObservationCleanupError=ObservationCleanupError, forfeit_failed_run=cleanup, auto=Mock(),
              battle=Mock(running=True), log=Mock())
    process = function_from_source("tasks/base/script_task_scheme.py", "onetime_mir_process", ns)
    assert process(object(),1) is MirrorRunOutcome.DEVELOPER_NO_REWARDS
    adventure.record_developer_result.assert_called_once_with("attempts_exhausted")
    adventure.record_developer_result.reset_mock()
    cleanup.side_effect = RuntimeError("unverified")
    with pytest.raises(RuntimeError):
        process(object(),1)
    adventure.record_developer_result.assert_not_called()


@pytest.mark.parametrize("complete", [True, False])
def test_statistics_use_the_original_team_fields_and_five_floor_rule(complete):
    history = SimpleNamespace(total_mirror_time_hard=[10,10,10],mirror_hard_count=2,
                              total_mirror_time_normal=[10,10,10],mirror_normal_count=2)
    ns = dict(cfg=SimpleNamespace(config=SimpleNamespace(teams={"1":history})),
              time=SimpleNamespace(time=lambda:120), log=Mock(),to_log_with_time=Mock())
    statistics = function_from_source("tasks/mirror/mirror.py", "_record_run_statistics", ns, "Mirror")
    instance = SimpleNamespace(theme_pack_timing_start_count=5 if complete else 3, current_floor_start_time=1, _log_floor_time=Mock(),
        team_order=1,team_number=1,hard_reward_eligible=False,floor=5,system="burn",
        battle_total_time=10,event_total_time=2,event_times=1,shop_total_time=3,find_road_total_time=4)
    assert statistics(instance, 0)
    assert history.mirror_normal_count == (3 if complete else 2)
    assert history.total_mirror_time_normal[0] == pytest.approx(140/3 if complete else 10)
    assert history.mirror_hard_count == 2




@pytest.mark.parametrize("mouse,screen", [(0,0),(.01,.01),(1.7,.2),(.2,2)])
def test_exit_stages_are_single_submit_and_obey_window_intervals(mouse, screen):
    config=SimpleNamespace(mouse_action_interval=mouse,screenshot_interval=screen)
    action=ExplorationExit()
    phase=["map"]
    submitted=[]
    auto=Mock()
    def click(path,**kwargs):
        assert kwargs.get("offset") is False
        transitions={("map","mirror/road_in_mir/setting_assets.png"):"menu",
                     ("menu","mirror/road_in_mir/forfeit_assets.png"):"pending",
                     ("confirm","mirror/road_in_mir/towindow&forfeit_confirm_assets.png"):"done"}
        if (phase[0],path) not in transitions:return False
        submitted.append(path)
        phase[0]=transitions[phase[0],path]
        return True
    auto.click_element=click
    waits=[]
    assert not action.advance(auto,config,pause=waits.append)
    assert not action.advance(auto,config,pause=waits.append)
    for _ in range(3):assert not action.advance(auto,config,pause=waits.append)
    phase[0]="confirm"
    assert action.advance(auto,config,pause=waits.append)
    assert len(submitted)==3
    assert all(wait>=max(1,mouse,screen) for wait in waits)


def test_confirmed_original_restart_records_before_reset_and_failed_exit_does_not_record():
    for confirmed in (False, True):
        auto = Mock()
        auto.take_screenshot.return_value = True
        auto.click_element.side_effect = lambda path, **kwargs: confirmed and path.endswith("towindow&forfeit_confirm_assets.png")
        instance = SimpleNamespace(start_time=10, floor=3, _record_long_term_log=Mock())
        seen = []
        instance._record_long_term_log.side_effect = lambda *args: seen.append((instance.start_time, instance.floor, args))
        ns = dict(auto=auto, time=SimpleNamespace(time=lambda: 100, sleep=lambda _: None),
                  log=Mock(), retry=lambda: False)
        restart = function_from_source("tasks/mirror/mirror.py", "re_start", ns, "Mirror")
        restart(instance, reason="战败重试达到原版上限，放弃并重开")
        if confirmed:
            assert seen == [(10, 3, (False, "战败重试达到原版上限，放弃并重开"))]
            assert instance.start_time == 100 and instance.floor == 0
        else:
            assert seen == [] and instance.start_time == 10 and instance.floor == 3


def test_attempt_limit_records_only_after_confirmed_cleanup_without_no_reward_mode():
    adventure = Mock(observation_forfeit=False)
    adventure.run.side_effect = MirrorBattleAttemptsExhausted("尝试次数耗尽")
    cleanup = Mock(return_value=True)
    ns = dict(cfg=SimpleNamespace(auto_hard_mirror=False, disable_mirror_rewards=False),
              Mirror=Mock(return_value=adventure), TeamSetting=object, MirrorRunOutcome=MirrorRunOutcome,
              MirrorBattleAttemptsExhausted=MirrorBattleAttemptsExhausted, ObservationCleanupError=ObservationCleanupError,
              forfeit_failed_run=cleanup, auto=Mock(), battle=Mock(running=True), log=Mock())
    process = function_from_source("tasks/base/script_task_scheme.py", "onetime_mir_process", ns)
    assert process(object(), 1) is MirrorRunOutcome.ABANDONED
    adventure._record_long_term_log.assert_called_once_with(False, "尝试次数耗尽")
    adventure._record_long_term_log.reset_mock()
    cleanup.side_effect = RuntimeError("清退未确认")
    with pytest.raises(RuntimeError):
        process(object(), 1)
    adventure._record_long_term_log.assert_not_called()
