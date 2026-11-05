"""Offline battle regressions: all game input, capture and timing are replaced."""
from upstream_reference import REFERENCE, original_source

import ast
import dataclasses
import importlib.util
import random
import re
import sys
import time
import unittest
from pathlib import Path
from threading import RLock
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock, patch

import cv2
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def load_file(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


actions = load_file("tested_optional_actions", "tasks/battle/optional_actions.py")
animation = load_file("tested_optional_animation", "tasks/battle/animation_hold.py")


class FakeAuto:
    def __init__(self, gears=True):
        self.screenshot = Image.new("RGB", (2560, 1440), "black")
        self.events = []
        self.turn = ["TURN 1"]
        self.words = {"空洞(le trou)": (800, 350)}
        self.elements = {"battle/gear_left.png": (400, 900), "battle/gear_right.png": (1190, 900)} if gears else {}
        self.input_handler = SimpleNamespace(has_active_hold=lambda: self.held)
        self.held = False

    def _run_ocr_for_text(self, **kwargs):
        self.events.append(("ocr", kwargs))
        return self.turn if kwargs.get("only_text") else self.words

    def find_element(self, path, **kwargs):
        return self.elements.get(path)

    def take_screenshot(self, **kwargs):
        self.events.append(("capture", kwargs))
        return self.screenshot

    def mouse_hold(self, x, y, duration):
        self.events.append(("hold", duration, x, y))

    def mouse_click(self, x, y, **kwargs):
        self.events.append(("click", x, y))

    def key_press(self, key):
        self.events.append(("key", key))

    def mouse_drag_link(self, points):
        self.events.append(("chain", points))

    def mouse_begin_hold(self, x, y, **kwargs):
        self.held = True
        self.events.append(("begin", x, y, kwargs))

    def mouse_keep_hold(self):
        self.events.append(("keep",))

    def mouse_end_hold(self):
        self.held = False
        self.events.append(("release",))


class EgoAndGeneralTests(unittest.TestCase):
    def controller(self, auto=None, **fields):
        auto = auto or FakeAuto()
        options = actions.BattleOptions(ego_enabled=True, ego_name="空洞(le trou)", **fields)
        return actions.TurnEgoAction(auto, 1440, options, Mock(), (10, 20, 80, 40), pause=lambda _: None)

    def test_full_name_normalization_and_no_nickname(self):
        words = {"空洞 （le trou）": (50, 100)}
        self.assertEqual(actions.exact_name_position(words, "空洞(le trou)"), (50, 100))
        self.assertIsNone(actions.exact_name_position(words, "空洞"))
        self.assertIsNone(actions.exact_name_position(words, "hollow"))
        self.assertIsNone(actions.exact_name_position(words, ""))

    def test_neighbor_fragments_join_but_separate_cards_do_not(self):
        self.assertEqual(
            actions.exact_name_position({"空洞": (500, 300), "(le trou)": (590, 300)}, "空洞(le trou)"), (545, 300)
        )
        self.assertIsNone(actions.exact_name_position({"空洞": (100, 300), "(le trou)": (1100, 300)}, "空洞(le trou)"))
        self.assertIsNone(actions.exact_name_position({"空洞": (500, 300), "(le trou)": (510, 500)}, "空洞(le trou)"))

    def test_disabled_controller_does_no_recognition_or_input(self):
        auto = FakeAuto()
        control = actions.TurnEgoAction(auto, 1440, actions.BattleOptions(), Mock(), None)
        self.assertFalse(control.perform())
        self.assertEqual(auto.events, [])

    def test_wrong_turn_is_not_latched_and_can_match_later(self):
        control = self.controller()
        control.auto.turn = ["TURN 2"]
        self.assertFalse(control.perform())
        self.assertEqual(control.attempted_turns, set())
        control.auto.turn = ["TURN 1"]
        self.assertTrue(control.perform())
        self.assertEqual(control.attempted_turns, {1})

    def test_corrosion_once_per_turn_without_post_checks(self):
        control = self.controller()
        self.assertTrue(control.perform())
        self.assertFalse(control.perform())
        events = control.auto.events
        self.assertEqual([event[1] for event in events if event[0] == "hold"], [0.8, 1.2])
        self.assertEqual([event for event in events if event[0] == "key"], [("key", "enter")])
        self.assertEqual([event for event in events if event[0] == "click"],
                         [("click", 800, 350 + 259 - 170), ("click", 20, 20)])
        # Only TURN reads and a single menu-title read; no OVERCLOCK/slot OCR.
        self.assertEqual(len([event for event in events if event[0] == "ocr" and not event[1].get("only_text")]), 1)

    def test_awakening_clicks_directly_after_opening_menu(self):
        control = self.controller(ego_mode=0)
        control.perform()
        self.assertEqual([event[1] for event in control.auto.events if event[0] == "hold"], [0.8])
        self.assertEqual([event for event in control.auto.events if event[0] in {"click", "key"}],
                         [("click", 800, 350 + 259 - 170), ("click", 20, 20),
                          ("key", "enter")])

    def test_missing_name_closes_top_left_then_general_and_latches(self):
        control = self.controller()
        control.auto.words = {"空洞": (800, 350)}
        self.assertTrue(control.perform())
        relevant = [event for event in control.auto.events if event[0] in {"click", "key"}]
        self.assertEqual(relevant, [("click", 20, 20), ("click", 20, 20), ("key", "enter")])
        self.assertFalse(control.perform())
        self.assertEqual(len([event for event in control.auto.events if event[0] == "hold"]), 2)

    def test_dark_image_does_not_prevent_corrosion_selection(self):
        control = self.controller()
        self.assertTrue(control.perform())
        relevant = [event for event in control.auto.events if event[0] in {"hold", "click", "key"}]
        self.assertEqual(relevant[0][1], 0.8)
        self.assertEqual(relevant[1:], [("hold", 1.2, 800, 350 + 259 - 170),
                                      ("click", 800, 350 + 259 - 170), ("click", 20, 20),
                                      ("key", "enter")])

    def test_configuration_exception_latches_before_input_and_falls_back(self):
        control = self.controller()
        control.auto.mouse_hold = Mock(side_effect=RuntimeError("adapter unavailable"))
        self.assertTrue(control.perform())
        self.assertFalse(control.perform())
        self.assertEqual(control.auto.mouse_hold.call_count, 1)
        self.assertEqual(
            [event for event in control.auto.events if event[0] in {"click", "key"}],
            [("click", 20, 20), ("key", "enter")],
        )

    def test_turn_ocr_exception_falls_back_without_opening_menu(self):
        control = self.controller()
        control.auto._run_ocr_for_text = Mock(side_effect=RuntimeError("OCR unavailable"))
        self.assertTrue(control.perform())
        self.assertFalse(any(event[0] == "hold" for event in control.auto.events))
        self.assertEqual(
            [event for event in control.auto.events if event[0] == "key"], [("key", "enter")]
        )

    def test_reset_allows_same_turn_in_next_battle(self):
        control = self.controller()
        control.perform()
        control.reset()
        control.perform()
        self.assertEqual([event[1] for event in control.auto.events if event[0] == "hold"], [0.8, 1.2, 0.8, 1.2])

    def test_shared_turn_state_prevents_repeat_after_fight_controller_reentry(self):
        auto = FakeAuto()
        shared = set()
        options = actions.BattleOptions(ego_enabled=True, ego_name="空洞(le trou)")

        def controller():
            return actions.TurnEgoAction(
                auto,
                1440,
                options,
                Mock(),
                (10, 20, 80, 40),
                pause=lambda _: None,
                attempted_turns=shared,
            )

        self.assertTrue(controller().perform())
        second = controller()
        self.assertIs(second.attempted_turns, shared)
        self.assertFalse(second.perform())
        self.assertEqual(shared, {1})
        self.assertEqual([event[1] for event in auto.events if event[0] == "hold"], [0.8, 1.2])

    def test_reset_clears_shared_state_for_retry_or_next_battle(self):
        auto = FakeAuto()
        shared = {1}
        options = actions.BattleOptions(ego_enabled=True, ego_name="空洞(le trou)")
        control = actions.TurnEgoAction(
            auto,
            1440,
            options,
            Mock(),
            (10, 20, 80, 40),
            pause=lambda _: None,
            attempted_turns=shared,
        )
        self.assertFalse(control.perform())
        control.reset()
        self.assertEqual(shared, set())
        self.assertIs(control.attempted_turns, shared)
        self.assertTrue(control.perform())
        self.assertEqual(shared, {1})
        self.assertEqual([event[1] for event in auto.events if event[0] == "hold"], [0.8, 1.2])

    def test_stop_during_either_hold_prevents_selection_and_submission(self):
        for stop_at, expected_holds in ((0.8, [0.8]), (1.2, [0.8, 1.2])):
            with self.subTest(stop_at=stop_at):
                control = self.controller(lower_chain=True)
                running = [True]
                control.running = lambda: running[0]
                original_hold = control.auto.mouse_hold

                def hold_and_stop(x, y, duration):
                    original_hold(x, y, duration)
                    if duration == stop_at:
                        running[0] = False

                control.auto.mouse_hold = hold_and_stop
                self.assertTrue(control.perform())
                self.assertEqual([event[1] for event in control.auto.events if event[0] == "hold"], expected_holds)
                self.assertFalse(any(event[0] in {"click", "key", "chain"} for event in control.auto.events))
                self.assertEqual(control.attempted_turns, {1})

    def test_focused_ego_has_no_gear_requirement_and_uses_p_enter(self):
        control = self.controller(FakeAuto(gears=False), lower_chain=True)
        control.perform()
        self.assertEqual(
            [event for event in control.auto.events if event[0] == "key"], [("key", "p"), ("key", "enter")]
        )
        self.assertFalse(any(event[0] == "chain" for event in control.auto.events))

    def test_normal_lower_chain_increases_x_and_submits_enter_only(self):
        control = self.controller(lower_chain=True)
        control.perform()
        chain = next(event[1] for event in control.auto.events if event[0] == "chain")
        self.assertEqual(chain[0], (400, 900))
        self.assertEqual(sorted(point[0] for point in chain[1:-1]), [point[0] for point in chain[1:-1]])
        self.assertTrue(all(point[1] == 1150 for point in chain[1:-1]))
        self.assertEqual([event for event in control.auto.events if event[0] == "key"], [("key", "enter")])

    def test_chain_exception_falls_back_to_p_enter(self):
        auto = FakeAuto()
        auto.mouse_drag_link = Mock(side_effect=RuntimeError("drag failed"))
        actions.general_battle(auto, 1, True, Mock(), pause=lambda _: None)
        self.assertEqual([event for event in auto.events if event[0] == "key"], [("key", "p"), ("key", "enter")])


class AnimationHoldTests(unittest.TestCase):
    def setUp(self):
        self.auto = FakeAuto(gears=False)
        self.time = [100.0]
        self.patches = [
            patch.object(animation, "monotonic", side_effect=lambda: self.time[0]),
            patch.object(animation, "corner_play_marker", return_value=False),
            patch.object(animation, "visual_overclock", return_value=False),
            patch.object(animation, "overclock_banner", return_value=False),
            patch.object(animation, "total_marker", return_value=False),
        ]
        for item in self.patches:
            item.start()
        self.addCleanup(lambda: [item.stop() for item in reversed(self.patches)])
        self.hold = animation.ContinuousAnimationHold(self.auto)

    def test_pending_request_alone_does_not_press_mouse(self):
        self.hold.arm()
        self.assertFalse(self.hold.update())
        self.assertFalse(any(event[0] == "begin" for event in self.auto.events))

    def test_visual_starts_one_continuous_bounded_hold(self):
        with patch.object(animation, "corner_play_marker", return_value=True):
            self.assertTrue(self.hold.start_from_visual())
            self.assertTrue(self.hold.update())
        starts = [event for event in self.auto.events if event[0] == "begin"]
        self.assertEqual(len(starts), 1)
        self.assertEqual(starts[0][-1], {"max_duration": 30})
        self.assertFalse(any(event[0] == "release" for event in self.auto.events))

    def test_thirty_second_limit_releases_and_prevents_restart(self):
        self.hold.update(known_visible=True)
        self.time[0] += 30
        self.assertFalse(self.hold.update(known_visible=True))
        self.assertFalse(self.hold.update(known_visible=True))
        self.assertTrue(self.hold.blocked)
        self.assertFalse(self.auto.held)
        self.assertEqual(len([event for event in self.auto.events if event[0] == "begin"]), 1)

    def test_adapter_timer_release_is_detected_even_if_recognition_is_slow(self):
        self.hold.update(known_visible=True)
        self.auto.held = False
        self.assertFalse(self.hold.update(known_visible=True))
        self.assertTrue(self.hold.blocked)

    def test_reward_boundary_releases_before_new_input(self):
        self.hold.update(known_visible=True)
        self.auto.elements["mirror/road_in_mir/select_encounter_reward_card_assets.png"] = (100, 100)
        self.assertFalse(self.hold.update(known_visible=True))
        self.assertEqual(self.auto.events[-1], ("release",))
        self.assertTrue(self.hold.blocked)

    def test_two_missing_frames_release_and_next_animation_can_start(self):
        self.hold.update(known_visible=True)
        self.assertTrue(self.hold.update(known_visible=False))
        self.assertFalse(self.hold.update(known_visible=False))
        self.assertFalse(self.hold.blocked)
        self.assertTrue(self.hold.update(known_visible=True))

    def test_cleanup_is_opt_in_and_runs_on_error(self):
        wrapped = animation.optional_hold_cleanup(self.auto)(lambda **kwargs: "ok")
        self.assertEqual(wrapped(), "ok")
        self.assertEqual(self.auto.events, [])
        self.assertEqual(wrapped(rabbit_animation_hold=True), "ok")
        self.assertEqual(self.auto.events, [("release",)])

        @animation.optional_hold_cleanup(self.auto)
        def failing(**kwargs):
            raise RuntimeError("stop")

        with self.assertRaises(RuntimeError):
            failing(rabbit_animation_hold=True)
        self.assertEqual(self.auto.events, [("release",), ("release",)])


def battle_class_without_game_imports(path, auto):
    """Execute the real Battle class bodies with every external service replaced."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    nodes = [
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef)
        or isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "DEFENSE_FOR_SOLO_TURN_LIMIT" for target in node.targets)
    ]
    isolated = ModuleType("isolated_battle")
    namespace = isolated.__dict__
    namespace.update(
        {
            "__name__": "isolated_battle",
            "dataclass": dataclasses.dataclass,
            "userStopError": actions.userStopError,
            "auto": auto,
            "cfg": SimpleNamespace(set_win_size=1440, simulator=False, fight_to_last_man=False, mouse_action_interval=0),
            "log": Mock(),
            "sleep": lambda _: None,
            "time": time,
            "random": random,
            "re": re,
            "np": np,
            "cv2": cv2,
            "Callable": object,
            "Optional": object,
            "BattleOptions": actions.BattleOptions,
            "TurnEgoAction": Mock(),
            "general_battle": actions.general_battle,
            "lower_row_points": actions.lower_row_points,
            "BattleAttemptBudget": __import__("tasks.mirror.failure_policy", fromlist=["BattleAttemptBudget"]).BattleAttemptBudget,
            "DefeatDialogAction": __import__("tasks.mirror.failure_policy", fromlist=["DefeatDialogAction"]).DefeatDialogAction,
            "UnifiedSpeedHold": Mock(),
            "CombatSpeedHold": __import__("tasks.battle.combat_hold", fromlist=["CombatSpeedHold"]).CombatSpeedHold,
            "optional_hold_cleanup": animation.optional_hold_cleanup,
            "begin_and_finish_time_log": lambda **kwargs: lambda function: function,
            "ImageUtils": Mock(),
            "event_handling": Mock(),
            "retry": lambda: True,
        }
    )
    # Original annotations use Optional[Callable]; postpone them without imports.
    module = ast.Module(
        body=[ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0), *nodes],
        type_ignores=[],
    )
    ast.fix_missing_locations(module)
    with patch.dict(sys.modules, {"isolated_battle": isolated}):
        exec(compile(module, str(path), "exec"), namespace)
    return namespace


class BattleDefaultCompatibilityTests(unittest.TestCase):
    def run_fight(self, path, kwargs=None):
        auto = FakeAuto(gears=False)
        auto.get_restore_time = lambda: None
        auto.mouse_click_blank = lambda *args, **kwargs: auto.events.append(("blank",))
        auto.mouse_to_blank = lambda *args, **kwargs: None
        state = ["ready"]

        def find(path, **kwargs):
            if path == "battle/more_information_assets.png" and state[0] == "ready":
                return (50, 50)
            if path == "battle/pause_assets.png" and state[0] == "done":
                return (80, 80)
            if path == "mirror/road_in_mir/select_encounter_reward_card_assets.png" and state[0] == "reward":
                return (100, 100)
            return None

        def capture(**kwargs):
            if state[0] == "done":
                state[0] = "reward"
            return auto.screenshot

        def press(key):
            auto.events.append(("key", key))
            if key == "enter":
                state[0] = "done"

        auto.find_element = find
        auto.click_element = lambda *args, **kwargs: False
        auto.take_screenshot = capture
        auto.key_press = press
        namespace = battle_class_without_game_imports(path, auto)
        retry = ModuleType("tasks.base.retry")
        retry.check_times = lambda *args, **kwargs: False
        with patch.dict(sys.modules, {"tasks.base.retry": retry}):
            namespace["Battle"](is_tool=True).fight(**(kwargs or {}))
        return auto.events, namespace

    def test_all_options_off_keep_original_action_sequence(self):
        reference = REFERENCE / "tasks/battle/battle.py"
        self.assertTrue(reference.is_file(), "Original V1.6 battle reference is required")
        original, _ = self.run_fight(reference)
        updated, namespace = self.run_fight(
            ROOT / "tasks/battle/battle.py",
            {
                "rabbit_options": actions.BattleOptions(),
                "rabbit_animation_hold": False,
            },
        )
        self.assertEqual(updated, original)
        self.assertEqual(updated, [("blank",), ("key", "p"), ("key", "enter")])
        namespace["TurnEgoAction"].assert_not_called()
        namespace["UnifiedSpeedHold"].assert_not_called()

    def test_original_operation_body_is_unchanged(self):
        def operation(path):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            battle = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "Battle")
            return next(
                node for node in battle.body if isinstance(node, ast.FunctionDef) and node.name == "_battle_operation"
            )

        reference = REFERENCE / "tasks/battle/battle.py"
        self.assertEqual(ast.dump(operation(reference)), ast.dump(operation(ROOT / "tasks/battle/battle.py")))


class HeldInputAdapterTests(unittest.TestCase):
    def setUp(self):
        self.clock = 100.0
        self.timers = []
        outer = self

        class FakeTimer:
            def __init__(self, interval, callback, args=()):
                self.interval, self.callback, self.args = interval, callback, args
                self.cancelled = False
                self.started = False
                outer.timers.append(self)

            def start(self):
                self.started = True

            def cancel(self):
                self.cancelled = True

            def expire(self):
                self.callback(*self.args)

        def fake_sleep(duration):
            self.clock += duration

        namespace = {
            "__name__": "isolated_held_input",
            "log": Mock(),
            "sleep": fake_sleep,
            "time": lambda: self.clock,
            "monotonic": lambda: self.clock,
            "RLock": RLock,
            "Timer": FakeTimer,
            "cfg": SimpleNamespace(config=SimpleNamespace(use_post_message=True)),
            "pyautogui": Mock(),
            "PyWinTypesError": RuntimeError,
            "win32api": SimpleNamespace(MAKELONG=lambda x, y: (x, y), PostMessage=Mock(), SendMessage=Mock()),
            "win32con": SimpleNamespace(WM_LBUTTONDOWN=1, MK_LBUTTON=2, WM_MOUSEMOVE=3),
            "screen": SimpleNamespace(handle=SimpleNamespace(hwnd=1, set_window_pos=Mock())),
        }
        for path, class_name in (
            ("module/automation/input_handlers/__init__.py", "AbstractInput"),
            ("module/automation/input_handlers/input.py", "WinAbstractInput"),
        ):
            tree = ast.parse((ROOT / path).read_text(encoding="utf-8"))
            node = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == class_name)
            module = ast.Module(body=[node], type_ignores=[])
            ast.fix_missing_locations(module)
            exec(compile(module, str(ROOT / path), "exec"), namespace)
        base = namespace["WinAbstractInput"]
        namespace["Input"] = type("ForegroundUnderTest", (base,), {})
        namespace["WindowMoveInput"] = type("WindowMoveUnderTest", (base,), {})
        self.namespace = namespace
        self.adapter = base()
        for name in ("set_mouse_pos", "set_active", "mouse_up"):
            setattr(self.adapter, name, Mock())

    def test_no_timer_or_mouse_input_before_feature_requests_hold(self):
        self.assertEqual(self.timers, [])
        self.namespace["win32api"].PostMessage.assert_not_called()
        self.adapter.mouse_up.assert_not_called()

    def test_independent_timer_caps_hold_at_thirty_and_releases(self):
        self.adapter.mouse_begin_hold(50, 80, max_duration=200)
        self.assertEqual(self.timers[0].interval, 30)
        self.assertTrue(self.timers[0].started)
        self.assertTrue(self.adapter.has_active_hold())
        self.timers[0].expire()
        self.assertFalse(self.adapter.has_active_hold())
        self.adapter.mouse_up.assert_called_once_with(50, 80)

    def test_keep_hold_reuses_press_and_release_is_idempotent(self):
        self.adapter.mouse_begin_hold(50, 80, max_duration=30)
        self.adapter.mouse_begin_hold(500, 800, max_duration=30)
        self.adapter.mouse_keep_hold()
        self.adapter.mouse_keep_hold()
        self.assertEqual(len(self.timers), 1)
        messages = self.namespace["win32api"].PostMessage.call_args_list
        self.assertEqual(sum(call.args[1] == 1 for call in messages), 1)
        self.assertEqual(sum(call.args[1] == 3 for call in messages), 2)
        self.adapter.release_active_hold()
        self.adapter.release_active_hold()
        self.adapter.mouse_up.assert_called_once_with(50, 80)
        self.assertTrue(self.timers[0].cancelled)

    def test_expired_timer_cannot_release_a_later_hold(self):
        self.adapter.mouse_begin_hold(50, 80, max_duration=30)
        old_timer = self.timers[0]
        self.adapter.release_active_hold()
        self.adapter.mouse_begin_hold(50, 80, max_duration=30)
        old_timer.expire()
        self.assertTrue(self.adapter.has_active_hold())
        self.assertEqual(self.adapter.mouse_up.call_count, 1)

    def test_pause_immediately_releases_current_hold(self):
        self.adapter.mouse_begin_hold(50, 80, max_duration=30)
        self.adapter.set_pause()
        self.assertTrue(self.adapter.is_pause)
        self.assertFalse(self.adapter.has_active_hold())
        self.adapter.mouse_up.assert_called_once_with(50, 80)

    def test_short_ego_hold_releases_even_when_mouse_down_raises(self):
        adapter = self.namespace["Input"]()
        adapter.pos_offset = Mock(return_value=(50, 80))
        gui = self.namespace["pyautogui"]
        gui.mouseDown.side_effect = RuntimeError("simulated input failure")
        with self.assertRaises(RuntimeError):
            adapter.mouse_hold(50, 80, duration=0.8)
        gui.mouseUp.assert_called_once()
        self.assertFalse(adapter.has_active_hold())


if __name__ == "__main__":
    unittest.main()
