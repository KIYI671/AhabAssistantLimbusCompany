"""Execute isolated production AST functions with all external effects mocked."""

import ast
import importlib.util
import types
import unittest
from pathlib import Path
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[1]


def function_from_source(relative, name, namespace, class_name=None):
    """Do not import configuration/UI/automation modules during these tests."""
    if relative == "tasks/mirror/mirror.py":
        from tasks.mirror.settlement import ExplorationExit, settlement_wait
        namespace.setdefault("ExplorationExit", ExplorationExit)
        namespace.setdefault("settlement_wait", settlement_wait)
    tree = ast.parse((ROOT / relative).read_text(encoding="utf-8"))
    body = tree.body
    if class_name:
        body = next(node.body for node in body if isinstance(node, ast.ClassDef) and node.name == class_name)
    function = next(node for node in body if isinstance(node, ast.FunctionDef) and node.name == name)
    function.decorator_list = []
    isolated = ast.fix_missing_locations(ast.Module(body=[function], type_ignores=[]))
    previous = namespace.get(name)
    exec(compile(isolated, str(ROOT / relative), "exec"), namespace)
    result = namespace[name]
    if previous is not None:
        namespace[name] = previous
    if relative == "tasks/mirror/mirror.py" and name == "run":
        statistics = function_from_source(relative, "_record_run_statistics", namespace, "Mirror")
        production_run = result
        def with_statistics(instance, *args, **kwargs):
            if not hasattr(instance, "_record_long_term_log"):
                instance._record_long_term_log = Mock()
            if not hasattr(instance, "_record_run_statistics"):
                instance._record_run_statistics = types.MethodType(statistics, instance)
            return production_run(instance, *args, **kwargs)
        return with_statistics
    return result


def observation_types():
    spec = importlib.util.spec_from_file_location("observation_failure_offline", ROOT / "tasks/mirror/observation_failure.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RouteIntegrationTests(unittest.TestCase):
    def test_custom_weights_preserve_original_simple_shortcut(self):
        namespace = {
            "cfg": types.SimpleNamespace(mirror_keyboard_simple_pathfinding=True),
            "auto": Mock(), "log": Mock(),
            "search_road_simple_keyboard": Mock(return_value=True),
            "search_road_default_distance": Mock(),
            "search_road_farthest_distance": Mock(),
        }
        search = function_from_source("tasks/mirror/mirror.py", "search_road", namespace, "Mirror")
        road_map = Mock()
        instance = types.SimpleNamespace(route_recovery=None, route_node_weights={"event": 2}, mirror_map=road_map, floor=2)
        self.assertTrue(search(instance))
        namespace["search_road_simple_keyboard"].assert_called_once_with()
        road_map.get_next_step.assert_not_called()
        for name in ("search_road_default_distance", "search_road_farthest_distance"):
            namespace[name].assert_not_called()

    def test_plan_failure_or_error_preserves_original_nearest_fallback(self):
        for weights in (None, {"event": 2}):
            for planned in (False, [], "D", RuntimeError("unreadable map")):
                with self.subTest(weights=weights, planned=planned):
                    road_map = Mock()
                    if isinstance(planned, Exception):
                        road_map.get_next_step.side_effect = planned
                    else:
                        road_map.get_next_step.return_value = planned
                    road_map.enter_next_node.return_value = False
                    namespace = {
                        "cfg": types.SimpleNamespace(mirror_keyboard_simple_pathfinding=False),
                        "auto": Mock(), "log": Mock(), "sleep": Mock(),
                        "search_road_default_distance": Mock(return_value=True),
                        "search_road_farthest_distance": Mock(),
                        "InputAttributeError": ValueError,
                    }
                    search = function_from_source("tasks/mirror/mirror.py", "search_road", namespace, "Mirror")
                    self.assertTrue(search(types.SimpleNamespace(route_node_weights=weights, mirror_map=road_map)))
                    namespace["search_road_default_distance"].assert_called_once_with()
                    namespace["search_road_farthest_distance"].assert_not_called()

    def test_nearest_failure_preserves_original_zoom_fallback(self):
        for weights in (None, {"event": 2}):
            with self.subTest(weights=weights):
                auto, road_map = Mock(), Mock()
                auto.click_element.return_value = False
                road_map.get_next_step.return_value = False
                namespace = {
                    "cfg": types.SimpleNamespace(mirror_keyboard_simple_pathfinding=False, background_click=False),
                    "auto": auto, "log": Mock(), "sleep": Mock(), "retry": Mock(return_value=True),
                    "search_road_default_distance": Mock(return_value=False),
                    "search_road_farthest_distance": Mock(return_value=True),
                    "InputAttributeError": ValueError,
                }
                search = function_from_source("tasks/mirror/mirror.py", "search_road", namespace, "Mirror")
                self.assertTrue(search(types.SimpleNamespace(route_node_weights=weights, mirror_map=road_map)))
                self.assertEqual(namespace["search_road_default_distance"].call_count, 3)
                namespace["search_road_farthest_distance"].assert_called_once_with()

    def test_disabled_still_runs_original_simple_shortcut(self):
        shortcut = Mock(return_value=True)
        namespace = {
            "cfg": types.SimpleNamespace(mirror_keyboard_simple_pathfinding=True),
            "search_road_simple_keyboard": shortcut, "log": Mock(),
        }
        search = function_from_source("tasks/mirror/mirror.py", "search_road", namespace, "Mirror")
        instance = types.SimpleNamespace(route_recovery=None, route_node_weights=None)
        self.assertTrue(search(instance))
        shortcut.assert_called_once_with()


class EventIntegrationTests(unittest.TestCase):
    def test_same_allowed_sinner_can_participate_in_second_independent_check(self):
        for transition in ("continue", "proceed", "commence", "commence_battle"):
            with self.subTest(transition=transition):
                auto = Mock()
                state = {"page": "check1", "captures": 0}

                def capture():
                    state["captures"] += 1
                    if state["captures"] > 10:
                        self.fail("Event did not finish within the offline screen budget")
                    return True

                def find(path, **kwargs):
                    if path == "event/perform_the_check_feature_assets.png":
                        return state["page"] in {"check1", "check2"}
                    if path == "mirror/road_in_mir/legend_assets.png":
                        return state["page"] == "done"
                    return False

                def select(x, y):
                    self.assertEqual((x, y), (1690, 1300))
                    state["page"] = {"check1": "between", "check2": "done"}[state["page"]]

                def click(path, **kwargs):
                    if state["page"] == "between" and path == f"event/{transition}_assets.png":
                        state["page"] = "check2"
                        return True
                    return False

                auto.take_screenshot.side_effect = capture
                auto.find_element.side_effect = find
                auto.mouse_click.side_effect = select
                auto.click_element.side_effect = click
                auto._run_ocr_for_text.return_value = {}
                # Execute the actual exclusion class without importing automation/config.
                event_tree = ast.parse((ROOT / "tasks/event/event_handling.py").read_text(encoding="utf-8"))
                event_class = next(node for node in event_tree.body if isinstance(node, ast.ClassDef)
                                   and node.name == "EventHandling")
                handler_namespace = {
                    "auto": auto, "cfg": types.SimpleNamespace(set_win_size=1440), "log": Mock(),
                    "time": types.SimpleNamespace(monotonic=Mock(side_effect=[0, 2])),
                }
                exec(compile(ast.Module(body=[event_class], type_ignores=[]), "offline-event-class", "exec"),
                     handler_namespace)
                handler = handler_namespace["EventHandling"]()
                namespace = {
                    "auto": auto, "event_handling": handler, "retry": Mock(return_value=True), "log": Mock(),
                    "time": types.SimpleNamespace(time=Mock(return_value=1)), "back_init_menu": Mock(),
                }
                event = function_from_source("tasks/mirror/mirror.py", "event_handling", namespace, "Mirror")
                instance = types.SimpleNamespace(
                    event_excluded_sinners=tuple(range(11)), event_total_time=0, event_times=0,
                )
                event(instance)
                self.assertEqual(auto.mouse_click.call_count, 2)
                self.assertEqual(state["page"], "done")
                self.assertFalse(handler.exclusion_exhausted)
                namespace["back_init_menu"].assert_not_called()

    def test_exhaustion_uses_original_failure_exit_without_selecting_another_sinner(self):
        auto = Mock()
        auto.take_screenshot.return_value = True
        auto.find_element.side_effect = lambda path, **kwargs: path == "event/perform_the_check_feature_assets.png"
        auto.click_element.return_value = False
        auto.find_text_element.return_value = False
        handler = Mock(exclusion_exhausted=True)
        handler.decision_event_handling.return_value = False
        back = Mock()
        namespace = {
            "auto": auto, "event_handling": handler, "retry": Mock(return_value=True), "log": Mock(),
            "time": types.SimpleNamespace(time=Mock(return_value=1)), "back_init_menu": back,
            "ImageUtils": types.SimpleNamespace(get_bbox=Mock(return_value=(0, 0, 100, 100)), load_image=Mock()),
        }
        event = function_from_source("tasks/mirror/mirror.py", "event_handling", namespace, "Mirror")
        instance = types.SimpleNamespace(event_excluded_sinners=(1,), event_total_time=0, event_times=0)
        event(instance)
        handler.reset_exclusion_attempts.assert_called_once_with()
        handler.decision_event_handling.assert_called_once_with(excluded_sinners=(1,))
        back.assert_called_once_with()
        auto.mouse_click.assert_not_called()

    def test_battle_exhaustion_is_explicitly_handed_to_original_event_failure(self):
        outcome = object()
        namespace = {
            "BattleEventOutcome": types.SimpleNamespace(EXCLUDED_EXHAUSTED=outcome),
            "battle": Mock(),
        }
        fight = function_from_source("tasks/mirror/mirror.py", "_fight", namespace, "Mirror")
        instance = types.SimpleNamespace(
            rabbit_options=types.SimpleNamespace(lower_chain=False, ego_enabled=False),
            victory_click=False,
            speed_hold=False, event_excluded_sinners=(1,),
            avoid_skill_3=False, prioritize_skill_3=False, defense_first_round=False, defense_for_solo_state=None,
            _time_call=Mock(return_value=(outcome, 2.5)), battle_total_time=0,
            event_handling=Mock(),
        )
        fight(instance)
        instance.event_handling.assert_called_once_with(force_failure=True)
        self.assertEqual(instance.battle_total_time, 2.5)
        self.assertEqual(instance._time_call.call_args.kwargs["event_excluded_sinners"], (1,))

    def test_forced_failure_does_not_reset_or_retry_excluded_participants(self):
        auto = Mock()
        auto.take_screenshot.return_value = True
        auto.find_element.return_value = False
        auto.find_text_element.return_value = False
        handler = Mock(exclusion_exhausted=True)
        back = Mock()
        namespace = {
            "auto": auto, "event_handling": handler, "retry": Mock(return_value=True), "log": Mock(),
            "time": types.SimpleNamespace(time=Mock(return_value=1)), "back_init_menu": back,
            "ImageUtils": types.SimpleNamespace(get_bbox=Mock(return_value=(0, 0, 100, 100)), load_image=Mock()),
        }
        event = function_from_source("tasks/mirror/mirror.py", "event_handling", namespace, "Mirror")
        instance = types.SimpleNamespace(event_excluded_sinners=(1,), event_total_time=0, event_times=0)
        event(instance, force_failure=True)
        handler.reset_exclusion_attempts.assert_not_called()
        handler.decision_event_handling.assert_not_called()
        back.assert_called_once_with()
        auto.mouse_click.assert_not_called()

    def test_forced_failure_is_not_skipped_by_turn_visible_behind_event(self):
        auto = Mock()
        auto.take_screenshot.return_value = True
        auto.find_element.side_effect = lambda path, **kwargs: path in {
            "battle/turn_assets.png", "event/perform_the_check_feature_assets.png",
        }
        auto.find_text_element.return_value = False
        handler = Mock(exclusion_exhausted=True)
        back = Mock()
        namespace = {
            "auto": auto, "event_handling": handler, "retry": Mock(return_value=True), "log": Mock(),
            "time": types.SimpleNamespace(time=Mock(return_value=1)), "back_init_menu": back,
            "ImageUtils": types.SimpleNamespace(get_bbox=Mock(return_value=(0, 0, 100, 100)), load_image=Mock()),
        }
        event = function_from_source("tasks/mirror/mirror.py", "event_handling", namespace, "Mirror")
        instance = types.SimpleNamespace(event_excluded_sinners=(1,), event_total_time=0, event_times=0)
        event(instance, force_failure=True)
        back.assert_called_once_with()
        handler.reset_exclusion_attempts.assert_not_called()
        handler.decision_event_handling.assert_not_called()


class ForfeitScreen:
    def __init__(self, *, forfeit_available=True, gray_claim=False):
        self.state = "theme"
        self.forfeit_available = forfeit_available
        self.gray_claim = gray_claim
        self.calls = []
        self.captures = 0
        self.model = "clam"
        self.screenshot = types.SimpleNamespace(size=(1920, 1080))

    def _run_ocr_for_text(self, **kwargs):
        return []

    def take_screenshot(self, **kwargs):
        self.captures += 1
        if self.captures > 60:
            raise RuntimeError("offline screen budget exhausted")
        return True

    def find_element(self, path, **kwargs):
        self.calls.append(("find", path))
        return ((self.state == "theme" and path == "mirror/theme_pack/feature_theme_pack_assets.png")
                or (self.state == "home" and path == "home/drive_assets.png")
                or (self.state in {"claim", "popup"} and path == "mirror/claim_reward/complete_mirror_100%_assets.png"))

    def click_element(self, path, **kwargs):
        self.calls.append(("click", path))
        if self.state == "result" and path == "battle/battle_finish_confirm_assets.png":
            self.state = "claim"
            return True
        if self.state == "claim" and path == "mirror/claim_reward/claim_rewards_assets.png" and not self.gray_claim:
            self.state = "popup"
            return True
        if (self.state in {"claim", "popup"} and path == "mirror/claim_reward/claim_forfeit_assets.png"
                and self.forfeit_available):
            self.state = "forfeit_confirm"
            return True
        if self.state == "forfeit_confirm" and path == "mirror/claim_reward/claim_rewards_confirm_assets.png":
            self.state = "home"
            return True
        if self.state == "popup" and path == "mirror/claim_reward/use_enkephalin_assets.png":
            self.state = "home"
            return True
        return False

    def find_text_element(self, *args, **kwargs):
        return False

    def mouse_click_blank(self, *args, **kwargs):
        pass

    def mouse_to_blank(self, *args, **kwargs):
        pass


class ObservationIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.types = observation_types()

    def run_observation_failure(self, screen, *, cancelled=True):
        class PackFailure(RuntimeError):
            def __init__(self):
                self.cancelled = cancelled

        cleanup = Mock(side_effect=lambda *args: setattr(screen, "state", "result"))
        namespace = {
            "auto": screen, "cfg": types.SimpleNamespace(floor_3_exit=True),
            "time": types.SimpleNamespace(time=Mock(return_value=1)), "sleep": Mock(), "log": Mock(),
            "retry": Mock(return_value=True), "switch_theme_pack_difficulty": Mock(),
            "selection_floor": Mock(return_value=None), "get_floor": Mock(return_value=3),
            "select_theme_pack": Mock(side_effect=PackFailure()), "PackObservationFailed": PackFailure,
            "ObservationCleanupError": self.types.ObservationCleanupError,
            "MirrorBattleAttemptsExhausted": __import__("tasks.mirror.failure_policy", fromlist=["MirrorBattleAttemptsExhausted"]).MirrorBattleAttemptsExhausted,
            "MirrorRunOutcome": self.types.MirrorRunOutcome, "exit_failed_observation": cleanup,
            "cannotOperateGameError": RuntimeError,
            "ImageUtils": types.SimpleNamespace(get_bbox=Mock(return_value=(0, 0, 100, 100)), load_image=Mock()),
        }
        run = function_from_source("tasks/mirror/mirror.py", "run", namespace, "Mirror")
        instance = types.SimpleNamespace(
            LOOP_COUNT=250, floor=3, mirror_floor_limit=3, floor_limit_exit=False, route_recovery=None,
            observation_rules=[[3, 2, 5]], hard_mode=False, team_order=1,
            use_custom_theme_pack_weight=False, observation_forfeit=False, bequest_from_the_previous_game=False,
            mirror_map=Mock(), _enter_hard_mode_if_needed=Mock(),
        )
        return run, instance, namespace

    def test_observation_failure_reuses_forfeit_and_requires_home_confirmation(self):
        screen = ForfeitScreen()
        run, instance, namespace = self.run_observation_failure(screen)
        self.assertIs(run(instance), self.types.MirrorRunOutcome.ABANDONED)
        self.assertEqual(screen.state, "home")
        self.assertTrue(instance.observation_forfeit)
        namespace["exit_failed_observation"].assert_called_once()
        self.assertIn(("click", "mirror/claim_reward/claim_forfeit_assets.png"), screen.calls)
        self.assertNotIn(("click", "mirror/claim_reward/use_enkephalin_assets.png"), screen.calls)

    def test_gray_claim_button_does_not_prevent_forfeit(self):
        screen = ForfeitScreen(gray_claim=True)
        run, instance, _ = self.run_observation_failure(screen)
        self.assertIs(run(instance), self.types.MirrorRunOutcome.ABANDONED)
        self.assertEqual(screen.state, "home")

    def test_unconfirmed_cancel_stops_before_exit_and_counting(self):
        screen = ForfeitScreen()
        run, instance, namespace = self.run_observation_failure(screen, cancelled=False)
        with self.assertRaises(self.types.ObservationCleanupError):
            run(instance)
        self.assertFalse(instance.observation_forfeit)
        namespace["exit_failed_observation"].assert_not_called()

    def test_missing_forfeit_cannot_fall_through_to_using_modules(self):
        screen = ForfeitScreen(forfeit_available=False)
        run, instance, _ = self.run_observation_failure(screen)
        with self.assertRaises(RuntimeError):
            run(instance)
        self.assertNotIn(("click", "mirror/claim_reward/use_enkephalin_assets.png"), screen.calls)

    def test_cleanup_failure_propagates_from_onetime_process(self):
        cfg = types.SimpleNamespace(auto_hard_mirror=False)
        adventure = Mock(observation_forfeit=True)
        adventure.run.side_effect = self.types.ObservationCleanupError("not confirmed")
        namespace = {
            "cfg": cfg, "Mirror": Mock(return_value=adventure), "TeamSetting": object,
            "MirrorRunOutcome": self.types.MirrorRunOutcome,
            "ObservationCleanupError": self.types.ObservationCleanupError,
            "MirrorBattleAttemptsExhausted": __import__("tasks.mirror.failure_policy", fromlist=["MirrorBattleAttemptsExhausted"]).MirrorBattleAttemptsExhausted,
            "log": Mock(), "back_init_menu": Mock(), "make_enkephalin_module": Mock(),
        }
        onetime = function_from_source("tasks/base/script_task_scheme.py", "onetime_mir_process", namespace)
        with self.assertRaises(self.types.ObservationCleanupError):
            onetime(object(), 1)
        namespace["back_init_menu"].assert_not_called()
        namespace["make_enkephalin_module"].assert_not_called()

    def test_abandoned_consumes_one_plan_without_success_or_hard_reward(self):
        team = types.SimpleNamespace(fixed_team_use=False)
        cfg = types.SimpleNamespace(
            set_mirror_count=1, infinite_dungeons=False, save_rewards=False, hard_mirror=True,
            auto_hard_mirror=True, hard_mirror_chance=3, teams_active_queue=[1],
            config=types.SimpleNamespace(teams={"1": team}), re_claim_rewards=False,
            normalize_and_sync_team_state=Mock(), get_value=Mock(return_value=[True]),
            rotate_team_queue=Mock(), set_value=Mock(),
        )
        mediator = types.SimpleNamespace(mirror_signal=Mock(), mirror_bar_kill_signal=Mock())
        namespace = {
            "cfg": cfg, "mediator": mediator, "log": Mock(),
            "MirrorRunOutcome": self.types.MirrorRunOutcome,
            "onetime_mir_process": Mock(return_value=self.types.MirrorRunOutcome.ABANDONED),
        }
        task = function_from_source("tasks/base/script_task_scheme.py", "Mirror_task", namespace)
        task()
        namespace["onetime_mir_process"].assert_called_once_with(team, 1)
        cfg.rotate_team_queue.assert_called_once_with()
        cfg.set_value.assert_called_once_with("set_mirror_count", 0)
        self.assertEqual(cfg.hard_mirror_chance, 3)
        self.assertEqual([call.args for call in mediator.mirror_signal.emit.call_args_list], [(0, 1), (0, 0)])

    def test_cleanup_helper_cannot_count_an_unconfirmed_exit(self):
        auto = Mock()
        auto.take_screenshot.return_value = True
        auto.find_element.return_value = False
        auto.click_element.return_value = False
        with self.assertRaises(self.types.ObservationCleanupError):
            self.types.exit_failed_observation(auto, Mock(), pause=Mock(), max_steps=3)
        self.assertEqual(auto.take_screenshot.call_count, 3)
        auto.mouse_click.assert_not_called()

    def test_cleanup_helper_requires_exploration_dialog_context_for_ocr_confirm(self):
        auto = Mock(screenshot=types.SimpleNamespace(size=(1920, 1080)))
        auto.take_screenshot.return_value = True
        auto.find_element.return_value = False
        auto.click_element.side_effect = lambda path, **kwargs: path == "mirror/road_in_mir/forfeit_assets.png"
        auto._run_ocr_for_text.return_value = {"确认": [100, 100]}
        with self.assertRaises(self.types.ObservationCleanupError):
            self.types.exit_failed_observation(auto, Mock(), pause=Mock(), max_steps=3)
        auto.mouse_click.assert_not_called()

    def test_cleanup_helper_can_confirm_original_exploration_exit_by_scoped_text(self):
        auto = Mock(screenshot=types.SimpleNamespace(size=(1920, 1080)))
        auto.take_screenshot.return_value = True
        auto.find_element.return_value = False
        auto.click_element.side_effect = lambda path, **kwargs: path == "mirror/road_in_mir/forfeit_assets.png"
        auto._run_ocr_for_text.return_value = {"终止迷宫探索": [100, 80], "确认": [300, 400]}
        self.types.exit_failed_observation(auto, Mock(), pause=Mock(), max_steps=3)
        auto.mouse_click.assert_called_once_with(300 + 480, 400 + int(1080 * .12))

    def test_cleanup_error_propagates_through_schedule_without_deducting(self):
        team = types.SimpleNamespace(fixed_team_use=False)
        cfg = types.SimpleNamespace(
            set_mirror_count=1, infinite_dungeons=False, save_rewards=False, hard_mirror=True,
            teams_active_queue=[1], config=types.SimpleNamespace(teams={"1": team}),
            normalize_and_sync_team_state=Mock(), get_value=Mock(return_value=[True]),
            rotate_team_queue=Mock(), set_value=Mock(),
        )
        namespace = {
            "cfg": cfg, "mediator": types.SimpleNamespace(mirror_signal=Mock()), "log": Mock(),
            "MirrorRunOutcome": self.types.MirrorRunOutcome,
            "onetime_mir_process": Mock(side_effect=self.types.ObservationCleanupError("not confirmed")),
        }
        task = function_from_source("tasks/base/script_task_scheme.py", "Mirror_task", namespace)
        with self.assertRaises(self.types.ObservationCleanupError):
            task()
        cfg.set_value.assert_not_called()
        cfg.rotate_team_queue.assert_not_called()


if __name__ == "__main__":
    unittest.main()
