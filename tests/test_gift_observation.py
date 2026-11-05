"""Test-version gift tab geometry and the real selection method, with no game input."""

import ast
import importlib.util
import re
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("gift_geometry", ROOT / "tasks/mirror/observation_rules.py")
rules = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rules)


@pytest.mark.parametrize("scale", [0.75, 1, 1.5])
def test_tabs_use_measured_pitch_at_each_window_scale(scale):
    points = rules.tab_positions((100 * scale, 100 * scale), (220 * scale, 100 * scale), scale)
    assert len(points) == 11
    assert points[10] == (1300 * scale, 100 * scale)
    assert points[10][0] != 100 * scale + 1100 * scale


@pytest.mark.parametrize("index", range(11))
def test_reset_only_uses_real_tabs_and_ends_on_requested_category(index):
    reset, target = rules.reset_tab_indices(index)
    assert 0 <= reset <= 10 and 0 <= target <= 10
    assert reset != target and target == index


class GiftScreen:
    def __init__(self, *, general=(1600, 65), count=1, anchors=True, name="锐利的针与线"):
        self.screenshot = SimpleNamespace(size=(2560, 1440))
        self.general, self.count, self.anchors, self.name = general, count, anchors, name
        self.events = []

    def find_element(self, path, **kwargs):
        if path.endswith("/burn.png"):
            return (100, 100) if self.anchors else None
        if path.endswith("/bleed.png"):
            return (220, 100) if self.anchors else None
        if "Level_" in path:
            return (200, 400)
        return None

    def find_language_text(self, chinese, english, *args, **kwargs):
        self.events.append(("text", chinese))
        if chinese == "泛用":
            return self.general
        return (2200, 1200) if chinese == "选择" else False

    def mouse_click(self, *point):
        self.events.append(("click", *point))

    def mouse_drag(self, *args, **kwargs):
        self.events.append(("drag", args, kwargs))

    def take_screenshot(self):
        return self.screenshot

    def _run_ocr_for_text(self, *, my_crop, only_text):
        if my_crop[0] == 1800:
            self.events.append(("count",))
            return [f"{self.count}/3"]
        return [self.name]

    def click_element(self, path, **kwargs):
        self.events.append(("confirm", path))
        return True


def selection(screen, gifts):
    tree = ast.parse((ROOT / "tasks/mirror/mirror.py").read_text(encoding="utf-8"))
    mirror = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "Mirror")
    method = next(node for node in mirror.body if isinstance(node, ast.FunctionDef) and node.name == "select_observe_ego_gift")
    boxes = {"gift_box_bbox.png": (50, 200, 1700, 1200), "select_gift_bbox.png": (1800, 1100, 2500, 1300),
             "reject_gift_bbox.png": (1700, 1100, 1800, 1300)}
    namespace = dict(auto=screen, cfg=SimpleNamespace(set_win_size=1440), log=Mock(), re=re,
                     sleep=lambda _: None, observe_system={0: "burn", 1: "bleed"},
                     ImageUtils=SimpleNamespace(load_image=lambda path: boxes[Path(path).name], get_bbox=lambda value: value))
    for name in ("tab_positions", "reset_tab_indices", "verify_count", "verify_known_name"):
        namespace[name] = getattr(rules, name)
    exec(compile(ast.Module(body=[method], type_ignores=[]), "gift_selection_offline", "exec"), namespace)
    namespace[method.name](SimpleNamespace(observe_ego_gift_selected=gifts, observe_bbox=(0,0,2560,200)))


def test_general_text_center_overrides_extrapolation_and_selects_configured_row_column():
    screen = GiftScreen()
    selection(screen, ["general_3_3_3"])
    clicks = [event[1:] for event in screen.events if event[0] == "click"]
    assert clicks[:5] == [(220,100),(100,100),(100, 100), (1600, 100), (530, 800)]
    assert screen.events.index(("count",)) < screen.events.index(("text", "选择"))


def test_unreadable_general_label_uses_measured_pitch():
    screen = GiftScreen(general=False)
    selection(screen, ["general_3_3_3"])
    clicks = [event[1:] for event in screen.events if event[0] == "click"]
    assert clicks[2:4] == [(100, 100), (1300, 100)]


def test_first_category_resets_to_bleed_then_returns_to_burn():
    screen = GiftScreen()
    selection(screen, ["burn_3_1_1"])
    clicks = [event[1:] for event in screen.events if event[0] == "click"]
    assert clicks[2:4] == [(220, 100), (100, 100)]


def test_partial_selection_does_not_confirm_wrong_observation():
    screen = GiftScreen(count=0)
    with pytest.raises(RuntimeError, match="实际仅 0"):
        selection(screen, ["general_3_3_3"])
    assert ("text", "选择") not in screen.events


def test_missing_anchors_do_not_make_guessed_category_clicks():
    screen = GiftScreen(anchors=False)
    selection(screen, ["general_3_3_3"])
    assert not any(event[0] == "click" for event in screen.events)


def test_known_gift_identity_check_is_retained_from_test_version():
    screen = GiftScreen(name="其他饰品")
    with pytest.raises(RuntimeError, match="未在已选列表核实"):
        selection(screen, ["general_3_3_3"])
    assert ("text", "选择") not in screen.events
