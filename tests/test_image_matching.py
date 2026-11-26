from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock

import numpy as np
import pytest


@pytest.fixture
def image_utils(monkeypatch):
    # Template matching does not need to initialize the user's GUI/configuration.
    config = ModuleType("module.config")
    config.cfg = SimpleNamespace()
    paths = ModuleType("utils.path_manager")
    paths.path_manager = SimpleNamespace()
    monkeypatch.setitem(sys.modules, "module.config", config)
    monkeypatch.setitem(sys.modules, "utils.path_manager", paths)
    source = Path(__file__).resolve().parents[1] / "utils" / "image_utils.py"
    spec = importlib.util.spec_from_file_location("isolated_image_utils", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.ImageUtils


def test_invalid_screenshot_dimensions_are_rejected_before_matching(monkeypatch, image_utils):
    match = Mock()
    monkeypatch.setattr("cv2.matchTemplate", match)
    assert image_utils.match_template(np.zeros((1, 2, 3, 4)), np.zeros((2, 2)), None) is None
    match.assert_not_called()


@pytest.mark.parametrize("channels", [None, 3])
def test_grayscale_and_color_screenshots_still_match_templates(channels, image_utils):
    shape = (12, 14) if channels is None else (12, 14, channels)
    screenshot = np.random.default_rng(42).integers(0, 255, size=shape, dtype=np.uint8)
    template = screenshot[3:6, 5:8].copy()
    center, score = image_utils.match_template(screenshot, template, None)
    assert center == (6, 4)
    assert score > 0.99
