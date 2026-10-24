"""Global mirror option schema and real offscreen widget persistence checks."""

import ast
import subprocess
import sys
import unittest
from pathlib import Path

from ruamel.yaml import YAML

ROOT = Path(__file__).resolve().parents[1]
GLOBAL_KEYS = ("mirror_lower_chain", "battle_speed_hold", "disable_mirror_rewards")


class GlobalMirrorOptionTests(unittest.TestCase):
    def test_defaults_live_only_in_example_and_are_off(self):
        tree = ast.parse((ROOT / "module/config/config_typing.py").read_text(encoding="utf-8"))
        model = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "ConfigModel")
        fields = {node.target.id: node for node in model.body if isinstance(node, ast.AnnAssign)}
        example = YAML(typ="safe").load((ROOT / "assets/config/config.example.yaml").read_text(encoding="utf-8"))
        for key in GLOBAL_KEYS:
            self.assertIsNone(fields[key].value)
            self.assertIs(example[key], False)
        self.assertEqual(set(fields), set(example))

    def test_globals_are_not_registered_as_team_checkboxes(self):
        tree = ast.parse((ROOT / "app/__init__.py").read_text(encoding="utf-8"))
        names = next(
            ast.literal_eval(node.value)
            for node in tree.body
            if isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Name) and target.id == "all_checkbox_config_name" for target in node.targets)
        )
        for key in GLOBAL_KEYS:
            self.assertNotIn(key, names)

    def test_offscreen_page_saves_and_reopens_global_controls(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "tests/render_global_mirror_options.py")],
            cwd=ROOT, capture_output=True, text=True, timeout=60,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("disk reload, reopen, independence and daily isolation passed", result.stdout)


if __name__ == "__main__":
    unittest.main()
