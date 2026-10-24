"""Ordered EGO fallback regressions; all input, capture and timing stay offline."""

import ast
import dataclasses
import importlib.util
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def load_file(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


actions = load_file("ordered_ego_actions_offline", "tasks/battle/optional_actions.py")
schema = load_file("ordered_ego_schema_offline", "module/config/config_typing.py")


def rule(name, *, turn=1, enabled=True, mode=0):
    return {"enabled": enabled, "turn": turn, "name": name, "mode": mode}


class RuleScreen:
    """Every operation records an event; this class cannot access the game."""

    def __init__(self):
        self.screenshot = Image.new("RGB", (2560, 1440), "black")
        self.events = []
        self.turn = ["TURN 1"]
        self.words = {"第一完整名称": (650, 350), "第二完整名称": (1250, 350)}

    def _run_ocr_for_text(self, **kwargs):
        if kwargs.get("only_text"):
            self.events.append(("turn",))
            return self.turn
        self.events.append(("names",))
        return self.words

    def find_element(self, *args, **kwargs):
        return None

    def take_screenshot(self, **kwargs):
        self.events.append(("capture",))
        return self.screenshot

    def mouse_hold(self, x, y, duration):
        self.events.append(("hold", duration, x, y))

    def mouse_click(self, x, y, **kwargs):
        self.events.append(("click", x, y))

    def key_press(self, key):
        self.events.append(("key", key))

    def mouse_drag_link(self, points):
        self.events.append(("chain", points))


class OrderedRuleTests(unittest.TestCase):
    def control(self, rules=None, *, auto=None, attempted=None, **fields):
        options = actions.BattleOptions(ego_enabled=True, ego_rules=rules, **fields)
        return actions.TurnEgoAction(
            auto or RuleScreen(),
            1440,
            options,
            Mock(),
            (0, 0, 200, 100),
            pause=lambda _: None,
            attempted_turns=attempted,
        )

    def relevant(self, control):
        return [event for event in control.auto.events if event[0] in {"click", "key"}]

    def test_first_named_rule_wins_and_submits_only_once(self):
        control = self.control([rule("第一完整名称"), rule("第二完整名称", mode=1)])
        self.assertTrue(control.perform())
        self.assertEqual(self.relevant(control), [("click", 650, 350 + 259 - 170), ("click", 20, 20),
                                                 ("key", "p"), ("key", "enter")])
        self.assertEqual([event[1] for event in control.auto.events if event[0] == "hold"], [0.8])
        self.assertEqual(control.attempted_turns, {1})

    def test_missing_full_name_closes_before_opening_fallback(self):
        control = self.control([rule("第一"), rule("第二完整名称", mode=1)])
        self.assertTrue(control.perform())
        events = [event for event in control.auto.events if event[0] in {"click", "hold", "key"}]
        self.assertEqual([e[1] for e in events if e[0] == "hold"], [.8, .8, .8, 1.2])
        selected = next(i for i, e in enumerate(events) if e == ("click", 1250, 350 + 259 - 170))
        self.assertEqual(events[selected + 1:], [("click", 20, 20), ("key", "p"), ("key", "enter")])
        # Every failed menu attempt closes before opening another entry.
        self.assertEqual([e for e in events[:selected] if e[0] == "click"], [("click", 20, 20), ("click", 20, 20)])

    def test_dark_first_rule_is_selected_without_trying_second(self):
        control = self.control([rule("第一完整名称"), rule("第二完整名称")])
        self.assertTrue(control.perform())
        self.assertEqual(
            self.relevant(control),
            [
                ("click", 650, 350 + 259 - 170),
                ("click", 20, 20),
                ("key", "p"),
                ("key", "enter"),
            ],
        )

    def test_disabled_and_other_turn_rules_do_not_open_the_menu(self):
        control = self.control(
            [
                rule("第一完整名称", enabled=False),
                rule("第一完整名称", turn=2),
                rule("第二完整名称"),
            ]
        )
        self.assertTrue(control.perform())
        self.assertEqual([event[1] for event in control.auto.events if event[0] == "hold"], [0.8])
        self.assertEqual(self.relevant(control)[0], ("click", 1250, 350 + 259 - 170))

    def test_all_missing_names_fall_back_once_and_latch_entire_turn(self):
        shared = set()
        screen = RuleScreen()
        screen.words = {}
        rules = [rule("第一完整名称"), rule("第二完整名称")]
        first = self.control(rules, auto=screen, attempted=shared)
        self.assertTrue(first.perform())
        second = self.control(rules, auto=screen, attempted=shared)
        self.assertFalse(second.perform())
        self.assertEqual(shared, {1})
        self.assertEqual([event for event in screen.events if event[0] == "key"], [("key", "p"), ("key", "enter")])
        self.assertEqual([event[1] for event in screen.events if event[0] == "hold"], [0.8, 0.8, 0.8, 0.8])

    def test_exception_in_first_rule_does_not_skip_next_fallback(self):
        control = self.control([rule("第一完整名称"), rule("第二完整名称")])
        original = control.auto.mouse_hold
        holds = []

        def fail_first(x, y, duration):
            holds.append(duration)
            if len(holds) == 1:
                raise RuntimeError("simulated first menu error")
            original(x, y, duration)

        control.auto.mouse_hold = fail_first
        self.assertTrue(control.perform())
        self.assertEqual(holds, [0.8, 0.8])
        self.assertIn(("click", 1250, 350 + 259 - 170), self.relevant(control))
        self.assertEqual(
            [event for event in self.relevant(control) if event[0] == "key"], [("key", "p"), ("key", "enter")]
        )

    def test_success_has_no_postselection_capture_or_rule_overwrite(self):
        control = self.control([rule("第一完整名称"), rule("第二完整名称")])
        selected = []
        original_click = control.auto.mouse_click
        original_capture = control.auto.take_screenshot

        def click(x, y, **kwargs):
            original_click(x, y, **kwargs)
            if x > 20:
                selected.append((x, y))

        def capture(**kwargs):
            if selected:
                raise AssertionError("EGO selection must not require a postcondition screenshot")
            return original_capture(**kwargs)

        control.auto.mouse_click = click
        control.auto.take_screenshot = capture
        self.assertTrue(control.perform())
        self.assertEqual(selected, [(650, 350 + 259 - 170)])
        self.assertEqual(
            [event for event in self.relevant(control) if event[0] == "key"], [("key", "p"), ("key", "enter")]
        )

    def test_blank_click_error_after_selection_does_not_choose_another_ego(self):
        control = self.control([rule("第一完整名称"), rule("第二完整名称")])
        original_click = control.auto.mouse_click

        def click(x, y, **kwargs):
            original_click(x, y, **kwargs)
            if (x, y) == (20, 20):
                raise RuntimeError("simulated menu cleanup error")

        control.auto.mouse_click = click
        self.assertTrue(control.perform())
        self.assertEqual(self.relevant(control), [
            ("click", 650, 350 + 259 - 170), ("click", 20, 20),
            ("key", "p"), ("key", "enter"),
        ])
        self.assertEqual([event[1] for event in control.auto.events if event[0] == "hold"], [0.8])

    def test_no_current_turn_match_does_not_latch_or_configure(self):
        control = self.control([rule("第一完整名称", turn=2)])
        self.assertFalse(control.perform())
        self.assertEqual(control.attempted_turns, set())
        self.assertFalse(any(event[0] in {"click", "hold", "key"} for event in control.auto.events))
        control.auto.turn = ["TURN 2"]
        self.assertTrue(control.perform())
        self.assertEqual(control.attempted_turns, {2})

    def test_different_turn_rules_run_independently(self):
        control = self.control([rule("第一完整名称"), rule("第二完整名称", turn=2)])
        self.assertTrue(control.perform())
        self.assertFalse(control.perform())
        control.auto.turn = ["TURN 2"]
        self.assertTrue(control.perform())
        self.assertFalse(control.perform())
        self.assertEqual(control.attempted_turns, {1, 2})
        self.assertEqual(
            [event for event in self.relevant(control) if event[0] == "key"],
            [
                ("key", "p"),
                ("key", "enter"),
                ("key", "p"),
                ("key", "enter"),
            ],
        )

    def test_retry_reset_allows_ordered_rules_again(self):
        shared = set()
        control = self.control([rule("第一完整名称"), rule("第二完整名称")], attempted=shared)
        self.assertTrue(control.perform())
        self.assertFalse(control.perform())
        control.reset()
        self.assertIs(control.attempted_turns, shared)
        self.assertTrue(control.perform())
        self.assertEqual(shared, {1})
        self.assertEqual(len([event for event in control.auto.events if event[0] == "hold"]), 2)

    def test_explicit_empty_list_does_not_resurrect_legacy_single_rule(self):
        control = self.control([], ego_name="第一完整名称")
        self.assertFalse(control.perform())
        self.assertFalse(any(event[0] in {"hold", "click", "key"} for event in control.auto.events))
        self.assertEqual(control.attempted_turns, set())

    def test_none_list_preserves_legacy_single_rule(self):
        control = self.control(None, ego_name="第一完整名称", ego_mode=0)
        self.assertTrue(control.perform())
        self.assertEqual(self.relevant(control)[0], ("click", 650, 350 + 259 - 170))

    def test_master_switch_off_preserves_list_without_recognition(self):
        options = actions.BattleOptions(ego_enabled=False, ego_rules=[rule("第一完整名称")])
        screen = RuleScreen()
        control = actions.TurnEgoAction(screen, 1440, options, Mock(), (0, 0, 200, 100), pause=lambda _: None)
        self.assertFalse(control.perform())
        self.assertEqual(screen.events, [])

    def test_pydantic_rules_and_dataclass_rules_preserve_same_order(self):
        for rules in (
            [schema.EgoReleaseRule(**rule("第一完整名称")), schema.EgoReleaseRule(**rule("第二完整名称"))],
            [actions.EgoRule(name="第一完整名称", mode=0), actions.EgoRule(name="第二完整名称", mode=0)],
        ):
            with self.subTest(rule_type=type(rules[0]).__name__):
                control = self.control(rules)
                self.assertTrue(control.perform())
                self.assertEqual(
                    self.relevant(control),
                    [
                        ("click", 650, 350 + 259 - 170),
                        ("click", 20, 20),
                        ("key", "p"),
                        ("key", "enter"),
                    ],
                )

    def test_stopping_after_entry_does_not_attempt_fallback_or_submit(self):
        control = self.control([rule("第一完整名称"), rule("第二完整名称")])
        running = [True]
        control.running = lambda: running[0]
        original = control.auto.mouse_hold

        def stop_after_hold(x, y, duration):
            original(x, y, duration)
            running[0] = False

        control.auto.mouse_hold = stop_after_hold
        self.assertTrue(control.perform())
        self.assertEqual([event[1] for event in control.auto.events if event[0] == "hold"], [0.8])
        self.assertEqual(self.relevant(control), [])
        self.assertEqual(control.attempted_turns, {1})


class GlobalRuntimeWiringTests(unittest.TestCase):
    def mirror(self, team, *, lower_chain=False, animation=False):
        tree = ast.parse((ROOT / "tasks/mirror/mirror.py").read_text(encoding="utf-8"))
        mirror = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "Mirror")
        initializer = next(
            node for node in mirror.body if isinstance(node, ast.FunctionDef) and node.name == "__init__"
        )
        namespace = {
            "TeamSetting": object,
            "log": Mock(),
            "Shop": Mock(),
            "all_systems": ["burn"],
            "BattleOptions": actions.BattleOptions,
            "EgoRule": actions.EgoRule,
            "EgoAttemptState": actions.EgoAttemptState,
            "DefenseForSoloState": Mock(),
            "MirrorMap": Mock(),
            "cfg": SimpleNamespace(hard_mirror=False, mirror_lower_chain=lower_chain, battle_speed_hold=animation),
            "time": SimpleNamespace(time=lambda: 1),
        }
        module = ast.fix_missing_locations(ast.Module(body=[initializer], type_ignores=[]))
        exec(compile(module, "offline-mirror-init", "exec"), namespace)
        instance = SimpleNamespace()
        namespace["__init__"](instance, team, 1)
        return instance

    def test_global_off_overrides_obsolete_team_flags(self):
        team = schema.TeamSetting(rabbit_lower_chain=True, rabbit_animation_hold=True)
        mirror = self.mirror(team)
        self.assertFalse(mirror.rabbit_options.lower_chain)
        self.assertFalse(mirror.speed_hold)

    def test_global_on_applies_to_team_without_obsolete_flags(self):
        mirror = self.mirror(schema.TeamSetting(), lower_chain=True, animation=True)
        self.assertFalse(mirror.rabbit_options.lower_chain)
        self.assertTrue(mirror.speed_hold)

    def test_model_rules_map_to_runtime_in_order_and_do_not_mutate_team(self):
        team = schema.TeamSetting(
            rabbit_ego_enabled=True,
            rabbit_ego_rules=[
                rule("第一完整名称", turn=2, mode=1),
                rule("第二完整名称", turn=2, enabled=False),
            ],
        )
        before = team.model_dump()
        mirror = self.mirror(team)
        self.assertEqual(
            [dataclasses.asdict(entry) for entry in mirror.rabbit_options.ego_rules],
            [entry.model_dump() for entry in team.rabbit_ego_rules],
        )
        self.assertEqual(team.model_dump(), before)


if __name__ == "__main__":
    unittest.main()
