"""Offline policy/input-dispatch tests; no live screen capture or input imports."""

import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]


def load_policy(name, relative):
    auto = Mock()
    cfg = types.SimpleNamespace(set_win_size=1440, mirror_keyboard_navigation=True)
    modules = {}
    for module_name, attributes in {
        "module.automation": {"auto": auto},
        "module.config": {"cfg": cfg},
        "module.logger": {"log": Mock()},
        "module.my_error.my_error": {"InputAttributeError": RuntimeError},
        "tasks.base.retry": {"retry": Mock(return_value=True)},
        "cv2": {},
    }.items():
        module = types.ModuleType(module_name)
        module.__dict__.update(attributes)
        modules[module_name] = module
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    loaded = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, modules):
        spec.loader.exec_module(loaded)
    return loaded, auto, cfg




class EventExclusionTests(unittest.TestCase):
    def setUp(self):
        self.module, self.auto, self.cfg = load_policy("event_policy_offline", "tasks/event/event_handling.py")
        self.handler = self.module.EventHandling()
        self.auto.find_element.return_value = []
        self.auto._run_ocr_for_text.return_value = {}

    def clicked_index(self):
        x, y = self.auto.mouse_click.call_args.args
        self.assertEqual(y, 1300)
        return round((x - 150) / 140)

    def test_off_preserves_single_template_click(self):
        self.auto.find_element.return_value = (290, 1200)
        self.assertTrue(self.handler.decision_event_handling())
        self.auto.mouse_action_with_pos.assert_called_once_with((290, 1200))
        self.auto._run_ocr_for_text.assert_not_called()
        self.auto.mouse_click.assert_not_called()

    def test_empty_ocr_keeps_original_rotating_fallback(self):
        self.auto.find_text_element.return_value = []
        self.assertTrue(self.handler.decision_event_handling_ocr(now=0))
        self.assertEqual(self.clicked_index(), 0)
        self.assertTrue(self.handler.decision_event_handling_ocr(now=1))
        self.assertEqual(self.clicked_index(), 1)

    def test_template_highest_excluded_never_selected(self):
        self.auto.find_element.return_value = [(290, 1200), (570, 1200)]
        self.assertTrue(self.handler.decision_event_handling([1]))
        self.assertEqual(self.clicked_index(), 3)

    def test_ocr_highest_excluded_selects_next_best_allowed(self):
        self.auto._run_ocr_for_text.return_value = {"Very High": (290, 200), "Normal": (1130, 200)}
        self.assertTrue(self.handler.decision_event_handling_ocr(now=0, excluded_sinners=[1]))
        self.assertEqual(self.clicked_index(), 7)

    def test_all_twelve_indices_have_stable_mapping_with_eleven_exclusions(self):
        for allowed in range(12):
            with self.subTest(allowed=allowed):
                self.handler.reset_exclusion_attempts()
                self.handler.last_action_time = float("-inf")
                excluded = [index for index in range(12) if index != allowed]
                self.assertEqual(len(excluded), 11)
                self.assertTrue(self.handler.decision_event_handling_ocr(now=0, excluded_sinners=excluded))
                self.assertEqual(self.clicked_index(), allowed)

    def test_unavailable_allowed_sinner_is_not_retried_forever(self):
        excluded = list(range(11))
        self.assertTrue(self.handler.decision_event_handling_ocr(now=0, excluded_sinners=excluded))
        self.assertFalse(self.handler.decision_event_handling_ocr(now=1, excluded_sinners=excluded))
        self.assertTrue(self.handler.exclusion_exhausted)
        self.assertEqual(self.auto.mouse_click.call_count, 1)

    def test_template_retry_also_exhausts_without_reselecting_excluded(self):
        self.auto.find_element.return_value = [(290, 1200), (1690, 1200)]
        excluded = list(range(11))
        with patch.object(self.module.time, "monotonic", side_effect=[0, 1]):
            self.assertTrue(self.handler.decision_event_handling(excluded))
            self.assertFalse(self.handler.decision_event_handling(excluded))
        self.assertEqual(self.clicked_index(), 11)
        self.assertTrue(self.handler.exclusion_exhausted)

    def test_invalid_twelve_person_exclusion_fails_closed(self):
        self.assertFalse(self.handler.decision_event_handling_ocr(now=0, excluded_sinners=list(range(12))))
        self.auto.mouse_click.assert_not_called()
        self.assertTrue(self.handler.exclusion_exhausted)

    def test_reset_allows_next_event_and_cooldown_avoids_double_click(self):
        excluded = list(range(11))
        self.assertTrue(self.handler.decision_event_handling_ocr(now=0, excluded_sinners=excluded))
        self.assertFalse(self.handler.decision_event_handling_ocr(now=0.1, excluded_sinners=excluded))
        self.assertFalse(self.handler.exclusion_exhausted)
        self.handler.reset_exclusion_attempts()
        self.assertTrue(self.handler.decision_event_handling_ocr(now=1, excluded_sinners=excluded))
        self.assertEqual(self.auto.mouse_click.call_count, 2)


if __name__ == "__main__":
    unittest.main()
