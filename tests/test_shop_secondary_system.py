"""Exercise shop decisions without importing GUI or automation dependencies."""

import ast
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock


SOURCE = Path(__file__).resolve().parents[1] / "tasks" / "mirror" / "in_shop.py"


def load_shop_methods(auto, log):
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    shop = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "Shop")
    methods = [node for node in shop.body if isinstance(node, ast.FunctionDef)
               and node.name in {"after_fuse_IV", "enter_fuse"}]
    namespace = {"auto": auto, "log": log, "sleep": lambda _: None}
    exec(compile(ast.Module(body=methods, type_ignores=[]), str(SOURCE), "exec"), namespace)
    return namespace


class SecondarySystemFusionTests(unittest.TestCase):
    def setUp(self):
        self.auto = Mock()
        self.auto.take_screenshot.return_value = object()
        self.auto.click_element.return_value = True
        self.log = Mock()
        self.methods = load_shop_methods(self.auto, self.log)

    def state(self, enabled, **overrides):
        fields = dict(
            after_level_IV=True, after_level_IV_select=2,
            second_system=True, fuse_IV=True, fuse_second_IV=False,
            second_system_action=[enabled, 1, 1, 1],
            fuse_switch=True, fuse_aggressive_switch=True,
            system="rupture", second_system_select="poise",
        )
        fields.update(overrides)
        return SimpleNamespace(**fields)

    def test_enabled_action_continues_secondary_fusion(self):
        for enabled in (1, True):
            with self.subTest(enabled=enabled):
                state = self.state(enabled, fuse_aggressive_switch=False)
                self.methods["after_fuse_IV"](state)
                self.assertTrue(state.fuse_IV)
                self.assertTrue(state.fuse_switch)
                self.assertTrue(state.fuse_aggressive_switch)

    def test_disabled_action_still_falls_back(self):
        for disabled in (0, False):
            with self.subTest(disabled=disabled):
                state = self.state(disabled)
                self.methods["after_fuse_IV"](state)
                self.assertFalse(state.fuse_switch)
                self.assertFalse(state.fuse_aggressive_switch)

    def test_keyword_matches_action_flag(self):
        for flag, keyword in ((1, "poise"), (True, "poise"), (0, "rupture"), (False, "rupture")):
            with self.subTest(flag=flag):
                self.auto.reset_mock()
                self.assertTrue(self.methods["enter_fuse"](self.state(flag)))
                self.assertEqual(self.auto.click_element.call_args_list[0].args,
                                 (f"mirror/shop/keyword/keyword_{keyword}.png",))

    def test_secondary_keyword_requires_all_other_gates(self):
        for overrides in ({"fuse_IV": False}, {"second_system": False},
                          {"fuse_second_IV": True}, {"fuse_aggressive_switch": False}):
            with self.subTest(overrides=overrides):
                self.auto.reset_mock()
                self.assertTrue(self.methods["enter_fuse"](self.state(1, **overrides)))
                self.assertEqual(self.auto.click_element.call_args_list[0].args,
                                 ("mirror/shop/keyword/keyword_rupture.png",))

    def test_normal_fusion_strategy_stays_non_aggressive(self):
        state = self.state(1, after_level_IV_select=1)
        self.methods["after_fuse_IV"](state)
        self.assertTrue(state.fuse_switch)
        self.assertFalse(state.fuse_aggressive_switch)


if __name__ == "__main__":
    unittest.main()

