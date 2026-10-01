"""隔离图形环境，验证颜色计数和中途接续的楼层状态。"""

import ast
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import cv2
import numpy as np
import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def _load_function(path, name, **namespace):
    tree = ast.parse((ROOT / path).read_text(encoding="utf-8"))
    node = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == name)
    node.decorator_list = []
    exec(compile(ast.Module(body=[node], type_ignores=[]), path, "exec"), namespace)
    return namespace[name]


def test_color_match_distinguishes_empty_result_from_error():
    match = _load_function("utils/image_utils.py", "match_color_regions", np=np, cv2=cv2, log=Mock())
    frame = np.zeros((24, 24, 3), dtype=np.uint8)
    assert match(frame, lambda roi: np.zeros(roi.shape[:2], dtype=np.uint8)) == []
    assert match(frame, lambda roi: np.zeros((1, 1), dtype=np.uint8)) is None


@pytest.mark.parametrize("regions", [None, [], [(10, 10, 300)]])
def test_automation_propagates_result_and_restores_grayscale(regions):
    find = _load_function(
        "module/automation/automation.py",
        "find_color_regions",
        np=np,
        log=Mock(),
        ImageUtils=SimpleNamespace(match_color_regions=Mock(return_value=regions)),
    )
    auto = SimpleNamespace(screenshot=Image.new("RGB", (24, 24)), take_screenshot=Mock(return_value=True))
    assert find(auto, None, lambda roi: None) == regions
    assert auto.screenshot.mode == "L"


@pytest.mark.parametrize("regions, expected", [(None, 4), ([], 1), ([(10, 10, 300)], 2)])
def test_floor_count_preserves_valid_empty_result(regions, expected):
    auto = Mock()
    auto.find_color_regions.return_value = regions
    get_floor = _load_function(
        "tasks/mirror/mirror.py",
        "get_which_floor",
        auto=auto,
        sleep=lambda seconds: None,
        FLOOR_BAND_ROI=(760, 495, 1860, 590),
        FLOOR_CLEAR_MIN_AREA=300,
        clear_badge_mask=lambda roi: None,
    )
    mirror = SimpleNamespace(floor=4, mirror_map=Mock())
    get_floor(mirror)
    assert mirror.floor == expected
    mirror.mirror_map.refresh_floor.assert_called_once_with(expected)


@pytest.mark.parametrize("initial_floor, expected_checks", [(0, 1), (2, 0)])
def test_map_checks_unknown_floor_before_searching(initial_floor, expected_checks):
    class Halt(Exception):
        pass

    mirror = SimpleNamespace(floor=initial_floor, LOOP_COUNT=250)
    mirror.get_which_floor = Mock(side_effect=lambda: setattr(mirror, "floor", 4))
    mirror.search_road = Mock(side_effect=Halt)
    mirror._time_call = lambda fn: fn()
    forfeit = Mock(side_effect=Halt)

    def click(name, *args, **kwargs):
        if name.endswith("towindow&forfeit_confirm_assets.png"):
            return forfeit()
        return False

    auto = SimpleNamespace(
        click_element=click,
        find_element=lambda name, *args, **kwargs: name.endswith("legend_assets.png"),
        take_screenshot=lambda: True,
        mouse_to_blank=lambda: None,
    )
    run = _load_function(
        "tasks/mirror/mirror.py",
        "run",
        auto=auto,
        cfg=SimpleNamespace(floor_3_exit=True),
        retry=lambda: True,
        time=SimpleNamespace(time=lambda: 1),
        sleep=lambda seconds: None,
    )
    with pytest.raises(Halt):
        run(mirror)
    assert mirror.get_which_floor.call_count == expected_checks
    assert forfeit.call_count == expected_checks
    assert mirror.search_road.call_count == 1 - expected_checks
