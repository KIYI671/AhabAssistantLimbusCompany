"""Offline tests.  Production Automation is never imported or instantiated."""

import ast
import hashlib
import importlib.util
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def _load_file(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


OBSERVATION = _load_file("pack_observation_under_test", ROOT / "tasks/mirror/pack_observation.py")
PACKS = [(415 + 315 * index, 335) for index in range(5)]


class TextMatchResult:
    def __init__(self, value, text, position=(0, 0)):
        self.value, self.text, self.position = value, text, position


def _selection_module(auto, weights, threshold=2):
    bindings = {
        "module.automation": SimpleNamespace(auto=auto, TextMatchResult=TextMatchResult),
        "module.config": SimpleNamespace(
            cfg=SimpleNamespace(set_win_size=1080, select_event_pack=False, skip_event_pack=False),
            theme_list=SimpleNamespace(
                get_effective_theme_pack_list=lambda *args: dict(weights), preferred_thresholds=threshold
            ),
        ),
        "module.decorator.decorator": SimpleNamespace(begin_and_finish_time_log=lambda **kwargs: lambda fn: fn),
        "module.logger": SimpleNamespace(log=Mock()),
        "module.my_error.my_error": SimpleNamespace(userStopError=type("userStopError", (Exception,), {})),
        "tasks.base.back_init_menu": SimpleNamespace(back_init_menu=Mock()),
        "tasks.mirror.pack_observation": OBSERVATION,
        "utils.path_manager": SimpleNamespace(path_manager=SimpleNamespace(current_language="zh_cn")),
    }
    with patch.dict(sys.modules, bindings):
        module = _load_file("pack_selection_under_test", ROOT / "tasks/mirror/select_theme_pack.py")
    module.sleep = lambda _: None
    return module


class CandidateAuto:
    """All screenshot and input surfaces are fakes, including fallback clicks."""

    def __init__(self, values, remaining=0, packs=PACKS):
        self.screenshot = Image.new("L", (1920, 1080))
        self.values, self.remaining, self.packs = values, remaining, list(packs)
        self.index = 0
        self.mouse_drag_down = Mock()
        self.mouse_to_blank = Mock()
        self.click_element = Mock(return_value=False)

    def take_screenshot(self):
        return self.screenshot

    def find_element(self, name, **kwargs):
        return list(self.packs) if name.endswith("theme_pack_features.png") else False

    def _run_ocr_for_text(self, **kwargs):
        return [] if self.remaining is None else [f"刷新{self.remaining}/3"]

    def find_language_text(self, *args, **kwargs):
        index = self.index % len(self.values)
        self.index += 1
        weight = self.values[index]
        return None if weight is None else TextMatchResult(weight, f"pack{index}")


class RuleTests(unittest.TestCase):
    def test_refresh_zero_is_explicit_not_guessed(self):
        self.assertEqual(OBSERVATION.refresh_remaining(["刷新", "0/3"]), 0)
        self.assertEqual(OBSERVATION.refresh_remaining(["2／3"]), 2)
        self.assertIsNone(OBSERVATION.refresh_remaining(["第0层", "3"]))
        self.assertIsNone(OBSERVATION.refresh_remaining(["4/3"]))

    def test_rules_use_configured_floor_and_coordinates(self):
        rules = [[1, 1, 3], [2, 2, 2], [3, 2, 5]]
        self.assertEqual(OBSERVATION.rule_for_floor(rules, 2), OBSERVATION.ObservationRule(2, 2, 2))
        self.assertIsNone(OBSERVATION.rule_for_floor(rules, 4))
        self.assertEqual(rules, [[1, 1, 3], [2, 2, 2], [3, 2, 5]])
        for invalid in ([[1, 0, 3]], [[1, 1, 6]], [[1, 1, 3], [1, 2, 2]]):
            with self.assertRaises(ValueError):
                OBSERVATION.rule_for_floor(invalid, 1)

    def test_english_floor_titles_allow_game_word_order(self):
        self.assertEqual(OBSERVATION.selection_floor(["Select a Theme Pack for Floor 3"]), 3)
        self.assertEqual(OBSERVATION.observed_floor(["Observe a Theme Pack for Floor 2"]), 2)

    def test_missing_candidate_matches_cannot_establish_complete_row(self):
        self.assertTrue(OBSERVATION.candidate_layout_complete(PACKS, (1920, 1080)))
        for incomplete in (PACKS[1:], PACKS[:-1], PACKS[:2] + PACKS[3:], PACKS[:1]):
            self.assertFalse(OBSERVATION.candidate_layout_complete(incomplete, (1920, 1080)))


class SelectionTests(unittest.TestCase):
    def test_disabled_standard_function_matches_original_v160_ast(self):
        module_ast = ast.parse((ROOT / "tasks/mirror/select_theme_pack.py").read_text(encoding="utf-8"))
        function = next(node for node in module_ast.body if isinstance(node, ast.FunctionDef) and node.name == "_select_theme_pack_standard")
        function.name = "select_theme_pack"
        # The only authorized standard-flow delta is extending refresh loading
        # to at least two seconds (or slower window settings). Normalize for V1.6.
        changes = 0
        for node in ast.walk(function):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "sleep":
                if node.args and isinstance(node.args[0], ast.Call) and isinstance(node.args[0].func, ast.Name) and node.args[0].func.id == "theme_refresh_wait":
                    node.args = [ast.Constant(value=1)]
                    changes += 1
        self.assertEqual(changes, 1)
        digest = hashlib.sha256(ast.dump(function).encode()).hexdigest()
        # Independently computed from upstream V1.6.0 41299bb, not this wrapper.
        self.assertEqual(digest, "4d8de444d00ad1e84953e7af7ecac6ed74c4f35e25606fcfec992d3546170f32")

    def test_disabled_or_other_floor_dispatches_only_original(self):
        module = _selection_module(CandidateAuto([5] * 5), {})
        module._select_theme_pack_standard = Mock(return_value="original")
        module._select_theme_pack_observation = Mock(side_effect=AssertionError("Unexpected extension"))
        for rules in (None, [], [[2, 2, 2]]):
            self.assertEqual(module.select_theme_pack(floor=1, team_num=7, observation_rules=rules), "original")
        module._select_theme_pack_standard.assert_called_with(False, 1, 7, False)

    def test_disabled_or_unconfigured_floor_never_reads_refresh_counter(self):
        # Execute the actual standard selector, including its refresh fallback.
        # The number reader and its OCR surface must never be invoked here.
        for rules in (None, [], [[2, 2, 2]]):
            auto = CandidateAuto([-1, -2, -3, -4, -5])
            auto.click_element = Mock(side_effect=[True, True, True, False])
            auto._run_ocr_for_text = Mock(side_effect=AssertionError("Disabled observation read refresh OCR"))
            module = _selection_module(auto, {}, threshold=10)
            module.read_refresh_remaining = Mock(side_effect=AssertionError("Refresh reader must be bypassed"))
            module._select_theme_pack_observation = Mock(side_effect=AssertionError("Observation is disabled"))
            module.select_theme_pack(floor=1, observation_rules=rules)
            module.read_refresh_remaining.assert_not_called()
            auto._run_ocr_for_text.assert_not_called()
            auto.mouse_drag_down.assert_called_once_with(*PACKS[0])

    def test_enabled_matching_floor_still_reads_counter_for_observation(self):
        auto = CandidateAuto([-1] * 5, remaining=0)
        module = _selection_module(auto, {}, threshold=0)
        module.read_refresh_remaining = Mock(return_value=0)
        module.observe_and_select = Mock(return_value="observed")
        self.assertEqual(module.select_theme_pack(floor=1, observation_rules=[[1, 1, 3]]), "observed")
        module.read_refresh_remaining.assert_called_once_with(auto)
        module.observe_and_select.assert_called_once()

    def test_zero_and_all_known_negative_observes_before_negative_threshold(self):
        weights = {f"pack{index}": -index - 1 for index in range(5)}
        auto = CandidateAuto(list(weights.values()))
        module = _selection_module(auto, weights, threshold=-10)
        module.observe_and_select = Mock(return_value="observed")
        self.assertEqual(module.select_theme_pack(floor=3, observation_rules=[[3, 2, 5]]), "observed")
        module.observe_and_select.assert_called_once_with(
            auto, module.log, OBSERVATION.ObservationRule(3, 2, 5), PACKS[-1], candidate_count=5
        )
        auto.mouse_drag_down.assert_not_called()
        self.assertEqual(weights, {f"pack{index}": -index - 1 for index in range(5)})

    def test_unknown_negative_default_is_not_all_confirmed_negative(self):
        auto = CandidateAuto([-2, -1, None, -3, -4])
        module = _selection_module(auto, {"未知": -5}, threshold=0)
        module.observe_and_select = Mock(side_effect=AssertionError("Must not observe unknown title"))
        module.select_theme_pack(floor=1, observation_rules=[[1, 1, 3]])
        module.observe_and_select.assert_not_called()
        auto.mouse_drag_down.assert_called_once_with(*PACKS[1])

    def test_zero_with_nonnegative_candidate_uses_original_selection(self):
        auto = CandidateAuto([-2, 0, -1, -3, -4])
        module = _selection_module(auto, {}, threshold=2)
        module.observe_and_select = Mock(side_effect=AssertionError("Not all negative"))
        module.select_theme_pack(floor=1, observation_rules=[[1, 1, 3]])
        auto.mouse_drag_down.assert_called_once_with(*PACKS[1])

    def test_unknown_or_nonzero_refresh_does_not_observe(self):
        for remaining in (None, 1, 3):
            auto = CandidateAuto([-1] * 5, remaining=remaining)
            module = _selection_module(auto, {}, threshold=-2)
            module.observe_and_select = Mock(side_effect=AssertionError("Counter is not explicitly zero"))
            module.select_theme_pack(floor=1, observation_rules=[[1, 1, 3]])
            module.observe_and_select.assert_not_called()
            auto.mouse_drag_down.assert_called_once()

    def test_observation_failure_propagates_without_refresh_or_negative_pick(self):
        auto = CandidateAuto([-1] * 5)
        module = _selection_module(auto, {}, threshold=0)
        failure = OBSERVATION.PackObservationFailed("cancelled", cancelled=True)
        module.observe_and_select = Mock(side_effect=failure)
        with self.assertRaises(OBSERVATION.PackObservationFailed) as context:
            module.select_theme_pack(floor=1, observation_rules=[[1, 1, 3]])
        self.assertIs(context.exception, failure)
        auto.click_element.assert_not_called()
        auto.mouse_drag_down.assert_not_called()
        module.observe_and_select.assert_called_once()

    def test_zero_all_negative_observation_precedes_optional_event_pack_priority(self):
        auto = CandidateAuto([-1] * 5)
        module = _selection_module(auto, {}, threshold=0)
        module.cfg.select_event_pack = True
        module.observe_and_select = Mock(return_value="observed")
        self.assertEqual(module.select_theme_pack(floor=5, observation_rules=[[5, 1, 1]]), "observed")
        module.observe_and_select.assert_called_once()
        auto.mouse_drag_down.assert_not_called()


class ScriptedAuto:
    """Strict transition model: no frame advances without the required input."""

    def __init__(self, invalid_confirmation=False, invalid_cancel=False):
        self.screenshot = Image.new("L", (1920, 1080))
        self.stage = "offer"
        self.actions = []
        self.invalid_confirmation = invalid_confirmation
        self.invalid_cancel = invalid_cancel

    def take_screenshot(self):
        return self.screenshot

    def _run_ocr_for_text(self, **kwargs):
        if self.stage in ("catalogue", "selected"):
            return ["观测第1阶层主题卡包", "取消", "确认"]
        if self.stage != "map":
            return ["选择1层主题卡包"]
        return ["地图"]

    def find_language_text(self, *args, **kwargs):
        return None

    def find_element(self, name, **kwargs):
        if name.endswith("legend_assets.png"):
            return self.stage == "map"
        if name.endswith("theme_pack_features.png"):
            return PACKS if self.stage == "returned" else []
        return False

    def mouse_click(self, x, y):
        point = (round(x), round(y))
        self.actions.append((self.stage, "click", point))
        transitions = {
            ("offer", (285, 70)): "replacement",
            ("replacement", PACKS[2]): "catalogue",
            ("catalogue", (1316, 470)): "selected",
        }
        if (self.stage, point) in transitions:
            self.stage = transitions[self.stage, point]
        elif self.stage == "selected" and point == (1185, 860):
            if not self.invalid_confirmation:
                self.stage = "returned"
        elif self.stage == "selected" and point == (765, 870):
            if not self.invalid_cancel:
                self.stage = "offer"
        else:
            raise AssertionError(f"Unexpected click {self.stage, point}")

    def mouse_drag_down(self, x, y):
        if self.stage != "returned" or (x, y) != PACKS[2]:
            raise AssertionError("Final target drag is mandatory and must use the replaced slot")
        self.actions.append((self.stage, "drag", (x, y)))
        self.stage = "map"

    def key_press(self, key):
        raise AssertionError(f"Unexpected keyboard action: {key}")

    def mouse_swipe_for_scroll(self, *args, **kwargs):
        raise AssertionError("First-row target must not scroll")


class ObservationFlowTests(unittest.TestCase):
    def test_every_observation_transition_includes_required_click_and_final_drag(self):
        auto = ScriptedAuto()
        self.assertTrue(OBSERVATION.observe_and_select(auto, Mock(), OBSERVATION.ObservationRule(1, 1, 3), PACKS[2], pause=lambda _: None, candidate_count=5))
        self.assertEqual([stage for stage, _, _ in auto.actions], ["offer", "replacement", "catalogue", "selected", "returned"])
        self.assertEqual(auto.stage, "map")

    def test_invalid_confirmation_is_not_repeated_and_cancels_before_failure(self):
        auto = ScriptedAuto(invalid_confirmation=True)
        with self.assertRaises(OBSERVATION.PackObservationFailed) as context:
            OBSERVATION.observe_and_select(auto, Mock(), OBSERVATION.ObservationRule(1, 1, 3), PACKS[2], pause=lambda _: None)
        self.assertTrue(context.exception.cancelled)
        self.assertEqual(auto.actions[-1], ("selected", "click", (765, 870)))
        self.assertEqual(sum(point == (1185, 860) for _, _, point in auto.actions), 1)
        self.assertEqual(auto.stage, "offer")

    def test_cancellation_must_be_verified_before_reporting_closed(self):
        auto = ScriptedAuto(invalid_confirmation=True, invalid_cancel=True)
        with self.assertRaises(OBSERVATION.PackObservationFailed) as context:
            OBSERVATION.observe_and_select(auto, Mock(), OBSERVATION.ObservationRule(1, 1, 3), PACKS[2], pause=lambda _: None)
        self.assertFalse(context.exception.cancelled)
        self.assertEqual(sum(point == (765, 870) for _, _, point in auto.actions), 1)

    def test_first_row_column_uses_scaled_grid(self):
        auto = SimpleNamespace(screenshot=Image.new("L", (960, 540)), mouse_click=Mock())
        point = OBSERVATION.select_catalogue_card(auto, OBSERVATION.ObservationRule(3, 1, 5), pause=lambda _: None)
        self.assertEqual(point, (834, 235))
        auto.mouse_click.assert_called_once_with(834, 235)

    def test_scroll_fit_tracks_actual_clamped_shift(self):
        rng = np.random.default_rng(42)
        content = rng.integers(0, 256, (1500, 1920), dtype=np.uint8)
        before = Image.fromarray(content[:1080])
        after = np.asarray(before).copy()
        # Move only the catalogue's content, not modal title/buttons.
        after[315:795, 860:1780] = content[315 + 137:795 + 137, 860:1780]
        shift = OBSERVATION._fitted_scroll(before, Image.fromarray(after), (860, 315, 1780, 795), (1, 1))
        self.assertIsNotNone(shift)
        self.assertAlmostEqual(shift, -137, delta=2)

    def test_second_row_uses_visible_interior_without_unnecessary_scroll(self):
        auto = SimpleNamespace(screenshot=Image.new("L", (1920, 1080)),
                               mouse_click=Mock(), mouse_swipe_for_scroll=Mock())
        point = OBSERVATION.select_catalogue_card(auto, OBSERVATION.ObservationRule(2, 2, 2), pause=lambda _: None)
        self.assertEqual(point, (1140, 750))
        auto.mouse_swipe_for_scroll.assert_not_called()
        auto.mouse_click.assert_called_once_with(1140, 750)

    def test_tenth_row_repeats_bounded_swipes_and_retains_configured_column(self):
        auto = SimpleNamespace(
            screenshot=Image.new("L", (1920, 1080)), mouse_click=Mock(), mouse_swipe_for_scroll=Mock(),
            take_screenshot=Mock(return_value=object()), _run_ocr_for_text=lambda **kwargs: ["观测第5阶层主题卡包"]
        )
        with patch.object(OBSERVATION, "_fitted_scroll", return_value=-320):
            point = OBSERVATION.select_catalogue_card(auto, OBSERVATION.ObservationRule(5, 10, 5), pause=lambda _: None)
        self.assertEqual(point, (1668, 750))
        self.assertEqual(auto.mouse_swipe_for_scroll.call_count, 8)
        auto.mouse_click.assert_called_once_with(1668, 750)


if __name__ == "__main__":
    unittest.main()
