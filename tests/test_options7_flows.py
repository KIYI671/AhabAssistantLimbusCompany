"""Version 7 regressions: execute production flows with all game input replaced."""

import ast
import sys
from functools import partial
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock, patch

import cv2
import numpy as np
import pytest
from PIL import Image

from test_optional_battle import ROOT, FakeAuto, actions, animation, battle_class_without_game_imports
from test_optional_integration import function_from_source, observation_types
from test_pack_observation import OBSERVATION, PACKS, ScriptedAuto
from tasks.mirror.failure_policy import BattleAttemptBudget, MirrorBattleAttemptsExhausted, forfeit_failed_run


class CostModalAuto(ScriptedAuto):
    def __init__(self, *, stuck=False):
        super().__init__()
        self.stuck = stuck

    def _run_ocr_for_text(self, **kwargs):
        if self.stage == "cost":
            # The directory remains visible behind the modal.
            return ["观测第1阶层主题卡包", "主题卡包A将被B", "替换。", "确认", "取消"]
        return super()._run_ocr_for_text(**kwargs)

    def mouse_click(self, x, y):
        point = (round(x), round(y))
        if self.stage == "selected" and point == (1185, 860):
            self.actions.append((self.stage, "click", point))
            self.stage = "cost"
        elif self.stage == "cost":
            self.actions.append((self.stage, "click", point))
            if point == (1146, 730):
                if not self.stuck:
                    self.stage = "returned"
            elif point == (772, 740):
                self.stage = "selected"
            else:
                raise AssertionError(f"Background footer clicked through modal: {point}")
        else:
            super().mouse_click(x, y)


def test_observation_second_confirmation_and_final_drag():
    auto = CostModalAuto()
    assert OBSERVATION.observe_and_select(auto, Mock(), OBSERVATION.ObservationRule(1, 1, 3),
                                          PACKS[2], pause=lambda _: None, candidate_count=5)
    assert [stage for stage, _, _ in auto.actions] == [
        "offer", "replacement", "catalogue", "selected", "cost", "returned"]
    assert auto.stage == "map"


def test_stuck_modal_is_paid_once_then_cancelled_before_catalogue_cancel():
    auto = CostModalAuto(stuck=True)
    with pytest.raises(OBSERVATION.PackObservationFailed) as failure:
        OBSERVATION.observe_and_select(auto, Mock(), OBSERVATION.ObservationRule(1, 1, 3),
                                       PACKS[2], pause=lambda _: None, candidate_count=5)
    assert failure.value.cancelled
    assert auto.actions.count(("cost", "click", (1146, 730))) == 1
    assert auto.actions[-2:] == [("cost", "click", (772, 740)), ("selected", "click", (765, 870))]


@pytest.mark.parametrize("size", [(1920, 1080), (2560, 1440)])
def test_cost_modal_buttons_use_game_client_coordinates(size):
    auto = Mock(screenshot=Image.new("RGB", size))
    auto.find_language_text.return_value = None
    assert OBSERVATION.modal_button(auto, True) == pytest.approx((1146 * size[0] / 1920, 730 * size[1] / 1080))
    crop = auto.find_language_text.call_args.kwargs["my_crop"]
    assert crop[3] < size[1] * .76  # directory footer cannot be matched


def run_prepared(*, guard=False, ego=True, focused=False, matched=True,
                 avoid=False, limited=False):
    auto = FakeAuto(gears=not focused)
    state = ["ready"]
    base_find = auto.find_element

    def find(path, **kwargs):
        if path == "battle/more_information_assets.png":
            return (50, 50) if state[0] == "ready" else None
        if path.endswith("select_encounter_reward_card_assets.png"):
            return (100, 100) if state[0] == "reward" else None
        return base_find(path, **kwargs)

    def capture(**kwargs):
        if state[0] == "done":
            state[0] = "reward"
        return auto.screenshot

    def press(key):
        auto.events.append(("key", key))
        if key == "enter":
            state[0] = "done"

    auto.find_element = find
    auto.take_screenshot = capture
    auto.key_press = press
    auto.mouse_to_blank = lambda **kwargs: None
    auto.mouse_click_blank = lambda *args, **kwargs: auto.events.append(("blank",))
    auto.click_element = lambda *args, **kwargs: False
    auto.get_restore_time = lambda: None
    if not matched:
        auto.words = {}
    namespace = battle_class_without_game_imports(ROOT / "tasks/battle/battle.py", auto)
    namespace["TurnEgoAction"] = partial(actions.TurnEgoAction, pause=lambda _: None)
    namespace["general_battle"] = partial(actions.general_battle, pause=lambda _: None)
    namespace["ImageUtils"].get_bbox.return_value = (10, 20, 80, 40)
    instance = namespace["Battle"](is_tool=True)
    instance._chain_battle = Mock(return_value=True)
    # A preference branch submits in the actual helper; mock its effect here.
    instance._chain_battle.side_effect = lambda **kwargs: (press("enter") or True)
    budget = namespace["DefenseForSoloState"](3) if limited else None
    retry = ModuleType("tasks.base.retry")
    retry.check_times = lambda *args, **kwargs: False
    with patch.dict(sys.modules, {"tasks.base.retry": retry}):
        instance.fight(defense_first_round=guard, avoid_skill_3=avoid, defense_for_solo_state=budget,
                       rabbit_options=actions.BattleOptions(ego_enabled=ego, ego_name="空洞(le trou)"))
    return auto, instance, budget


def test_turn_then_guard_then_ego_then_lower_chain_enter_and_budget():
    auto, battle, budget = run_prepared(guard=True, limited=True, avoid=True)
    events = auto.events
    assert events[0][0] == "ocr"  # TURN before preparing either action
    holds = [i for i, event in enumerate(events) if event[0] == "hold"]
    lower_clicks = [i for i, event in enumerate(events) if event[0] == "click" and event[2] == 1150]
    assert len(lower_clicks) == 4 and max(lower_clicks) < holds[0]
    chain = next(i for i, event in enumerate(events) if event[0] == "chain")
    assert [e for e in events[:chain] if e[0] == "click"][-1] == ("click", 20, 20)
    assert holds[-1] < chain
    assert [e for e in events if e[0] == "key"] == [("key", "enter")]
    assert budget.remaining_turns == 2  # EGO covering guard still spends one turn
    battle._chain_battle.assert_not_called()


@pytest.mark.parametrize("ego,guard", [(True, False)])
def test_ego_turn_action_selects_lower_row_without_independent_switch(ego, guard):
    auto, _, _ = run_prepared(ego=ego, guard=guard)
    assert len([e for e in auto.events if e[0] == "chain"]) == 1
    assert [e for e in auto.events if e[0] == "key"] == [("key", "enter")]


def test_focused_ego_without_gears_returns_to_p_enter():
    auto, _, _ = run_prepared(focused=True, guard=True)
    assert [e for e in auto.events if e[0] == "key"] == [("key", "p"), ("key", "enter")]
    assert [e[1] for e in auto.events if e[0] == "hold"] == [.8, 1.2]




def test_missing_ego_title_closes_menu_and_preserves_guard_submission():
    auto, _, _ = run_prepared(guard=True, matched=False, avoid=True)
    assert ("click", 20, 20) in auto.events
    assert len([e for e in auto.events if e[0] == "chain"]) == 1
    assert [e for e in auto.events if e[0] == "key"] == [("key", "enter")]


def test_no_action_due_keeps_original_skill_three_preference():
    _, battle, _ = run_prepared(ego=False, avoid=True)
    battle._chain_battle.assert_called_once_with(prioritize_skill_3=False)


def test_legacy_lower_chain_flag_alone_no_longer_triggers_input():
    auto = FakeAuto()
    control = actions.TurnEgoAction(auto, 1440, actions.BattleOptions(lower_chain=True), Mock(), None)
    assert not control.perform()
    assert auto.events == []


def test_stop_is_never_converted_to_p_fallback():
    auto = FakeAuto()
    auto.mouse_hold = Mock(side_effect=actions.userStopError("stop"))
    control = actions.TurnEgoAction(auto, 1440, actions.BattleOptions(ego_enabled=True, ego_name="空洞(le trou)"),
                                    Mock(), (0, 0, 100, 40), pause=lambda _: None)
    with pytest.raises(actions.userStopError):
        control.perform()
    assert not any(e[0] == "key" for e in auto.events)


def test_attempt_budget_counts_distinct_defeats_and_stops_before_fifth_start():
    budget = BattleAttemptBudget(4)
    for n in range(3):
        budget.defeat()
        budget.defeat()  # unchanged defeat page does not count twice
        assert budget.failures == n + 1
        budget.combat_resumed()
    with pytest.raises(MirrorBattleAttemptsExhausted):
        budget.defeat()


def test_abandonment_requires_explicit_reward_forfeit_and_verified_home():
    auto = Mock(screenshot=Image.new("RGB", (1920, 1080)))
    stage = ["defeat"]
    auto.find_element.side_effect = lambda path, **kw: (
        (973, 790) if path == "battle/dead_all_confirm_assets.png" and stage[0] == "defeat" else
        path == "battle/dead_all.png" if stage[0] == "defeat" else
        path in {"home/drive_assets.png", "home/mail_assets.png"} if stage[0] == "home" else
        path == "mirror/claim_reward/battle_statistics_assets.png" if stage[0] == "rewards" else False)
    auto.find_language_text.return_value = (200, 300)

    def click(path, **kw):
        if path == "battle/dead_all_confirm_assets.png" and stage[0] == "defeat":
            stage[0] = "map"
            return True
        if path == "mirror/road_in_mir/forfeit_assets.png" and stage[0] == "map":
            stage[0] = "exit_confirm"
            return True
        if path.endswith("towindow&forfeit_confirm_assets.png") and stage[0] == "exit_confirm":
            stage[0] = "rewards"
            return True
        if path.endswith("claim_forfeit_assets.png") and stage[0] == "rewards":
            stage[0] = "home"
            return True
        return False

    auto.click_element.side_effect = click
    assert forfeit_failed_run(auto, Mock(), pause=lambda _: None)
    assert stage[0] == "home"
    assert not any("use_enkephalin" in call.args[0] for call in auto.click_element.call_args_list)
    # A home screen alone is not proof that abandoning/reward forfeiting worked.
    with pytest.raises(RuntimeError):
        forfeit_failed_run(auto, Mock(), pause=lambda _: None)


def test_exhausted_attempts_use_abandoned_outcome_only_after_cleanup():
    types = observation_types()
    adventure = Mock(observation_forfeit=False)
    adventure.run.side_effect = MirrorBattleAttemptsExhausted("four defeats")
    cleanup = Mock(return_value=True)
    namespace = dict(cfg=SimpleNamespace(auto_hard_mirror=False), Mirror=Mock(return_value=adventure),
                     TeamSetting=object, MirrorRunOutcome=types.MirrorRunOutcome,
                     MirrorBattleAttemptsExhausted=MirrorBattleAttemptsExhausted,
                     ObservationCleanupError=types.ObservationCleanupError,
                     forfeit_failed_run=cleanup, auto=Mock(), battle=Mock(running=True), log=Mock())
    one_run = function_from_source("tasks/base/script_task_scheme.py", "onetime_mir_process", namespace)
    assert one_run(object(), 1) is types.MirrorRunOutcome.ABANDONED
    cleanup.assert_called_once()
    cleanup.side_effect = RuntimeError("unverified cleanup")
    with pytest.raises(RuntimeError):
        one_run(object(), 1)


def test_total_can_start_hold_before_victory_ocr_and_timeout_stays_blocked():
    auto = FakeAuto(gears=False)
    hold = animation.ContinuousAnimationHold(auto)
    with patch.object(animation, "corner_play_marker", return_value=False), \
            patch.object(animation, "visual_overclock", return_value=False), \
            patch.object(animation, "total_marker", return_value=True), \
            patch.object(animation, "monotonic", return_value=100):
        assert hold.start_from_visual()
    with patch.object(animation, "monotonic", return_value=131):
        assert not hold.update(known_visible=True)
        assert not hold.update(known_visible=True)
    assert hold.blocked and hold.animation_visible and not auto.held
    assert len([e for e in auto.events if e[0] == "begin"]) == 1


def test_rgb_frames_match_grayscale_templates_in_both_production_lookup_paths():
    tree = ast.parse((ROOT / "module/automation/automation.py").read_text(encoding="utf-8"))
    body = next(n.body for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "Automation")
    rng = np.random.default_rng(22)
    pixels = rng.integers(0, 256, (100, 140, 3), dtype=np.uint8)
    picture = Image.fromarray(pixels)
    template = np.array(picture.convert("L"))[20:38, 40:58]
    utils = SimpleNamespace(existing_image_paths=lambda _: ["share"], load_image=lambda _: template,
                            match_template=lambda screen, ref, bbox, model: (
                                (49, 29), cv2.minMaxLoc(cv2.matchTemplate(screen, ref, cv2.TM_CCOEFF_NORMED))[1]),
                            match_template_with_multiple_targets=lambda screen, ref, *a, **kw: (
                                [(49, 29)] if cv2.minMaxLoc(cv2.matchTemplate(screen, ref, cv2.TM_CCOEFF_NORMED))[1] > .9 else []))
    auto = SimpleNamespace(screenshot=picture, memory_protection=False,
                           _load_template_for_path=lambda *a: (template, None),
                           _is_valid_match=lambda value, threshold: value >= threshold,
                           _path_state_is_known=lambda: True)
    namespace = dict(np=np, ImageUtils=utils, log=Mock(), List=list)
    for name in ("find_image_element", "find_image_with_multiple_targets"):
        node = next(n for n in body if isinstance(n, ast.FunctionDef) and n.name == name)
        exec(compile(ast.Module(body=[node], type_ignores=[]), "isolated-rgb-matching", "exec"), namespace)
        assert namespace[name](auto, "plain.png", .9) == ((49, 29) if name == "find_image_element" else [(49, 29)])


def test_actual_fight_checks_budget_before_selecting_a_fifth_attempt():
    auto = FakeAuto(gears=False)
    stage = ["defeat"]
    retries = []
    auto.get_restore_time = lambda: None
    auto.wait_pause = lambda: None

    def find(path, **kwargs):
        if path == "battle/dead_all_confirm_assets.png" and stage[0] == "defeat":
            return (1297, 1053)
        if path == "battle/dead_all.png" and stage[0] == "defeat":
            return [(10, 10), (20, 20), (30, 30)] if kwargs.get("find_type") else (10, 10)
        if path == "battle/pause_assets.png" and stage[0] == "resumed":
            stage[0] = "next_defeat"
            return (100, 100)
        return None

    def capture(**kwargs):
        if stage[0] == "next_defeat":
            stage[0] = "defeat"
        return auto.screenshot

    def click(path, **kwargs):
        if path == "battle/dead_all_confirm_assets.png":
            retries.append(path)
            stage[0] = "resumed"
            return True
        return False

    auto.find_element, auto.take_screenshot, auto.click_element = find, capture, click
    namespace = battle_class_without_game_imports(ROOT / "tasks/battle/battle.py", auto)
    retry = ModuleType("tasks.base.retry")
    retry.check_times = lambda *args, **kwargs: False
    with patch.dict(sys.modules, {"tasks.base.retry": retry}), pytest.raises(MirrorBattleAttemptsExhausted):
        namespace["Battle"](is_tool=True).fight(max_attempts=4)
    assert len(retries) == 3  # initial + 3 retries, no fifth attempt


def test_animation_and_timeout_do_not_fall_through_to_center_or_battle_inputs():
    auto = FakeAuto(gears=False)
    frame = [-1]
    stages = ["animation", "timeout", "victory", "reward"]
    auto.get_restore_time = lambda: None
    auto.mouse_click_blank = Mock()
    auto.click_element = lambda *a, **kw: False

    def capture(**kwargs):
        frame[0] += 1
        assert kwargs == {"gray": False}
        assert frame[0] < len(stages)
        return auto.screenshot

    def find(path, **kwargs):
        return (100, 100) if stages[frame[0]] == "reward" and path.endswith("select_encounter_reward_card_assets.png") else None

    auto.take_screenshot, auto.find_element = capture, find
    namespace = battle_class_without_game_imports(ROOT / "tasks/battle/battle.py", auto)
    from tasks.battle import speed_hold
    hold = speed_hold.UnifiedSpeedHold(auto)
    namespace["UnifiedSpeedHold"] = Mock(return_value=hold)
    retry = ModuleType("tasks.base.retry")
    retry.check_times = lambda *args, **kwargs: False
    with patch.dict(sys.modules, {"tasks.base.retry": retry}), \
            patch.object(speed_hold, "corner_play_marker", side_effect=lambda _: stages[frame[0]] in {"animation", "timeout"}), \
            patch.object(speed_hold, "overclock_banner", return_value=False), \
            patch.object(speed_hold, "total_marker", return_value=False), \
            patch("tasks.battle.combat_hold.monotonic", side_effect=lambda: 100 if frame[0] == 0 else 131):
        namespace["Battle"](is_tool=False).fight(rabbit_animation_hold=True)
    assert len([e for e in auto.events if e[0] == "click"]) == 1
    assert abs(next(e for e in auto.events if e[0] == "click")[1] - auto.screenshot.width / 2) <= 10
    assert not any(e[0] in {"key", "chain"} for e in auto.events)
    assert len([e for e in auto.events if e[0] == "begin"]) == 1
    assert not auto.held


def test_ego_disabled_guard_uses_original_submission_instead_of_prepare_override():
    auto, _, _ = run_prepared(ego=False, guard=True)
    assert auto.events[0] == ("blank",)
    assert not any(e[0] in {"ocr", "hold"} for e in auto.events)
    assert len([e for e in auto.events if e[0] == "chain"]) == 1
    # Original guard helper's fallback submits P+Enter when pause is not seen.
    assert [e for e in auto.events if e[0] == "key"] == [("key", "p"), ("key", "enter")]
