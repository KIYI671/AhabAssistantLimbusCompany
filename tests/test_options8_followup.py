"""First-confirm adjustment and Victory delay, without physical game input."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from PIL import Image
from test_optional_battle import FakeAuto, animation
from test_pack_observation import OBSERVATION


@pytest.mark.parametrize("height", [1080, 1440])
@pytest.mark.parametrize("ocr", [False, True])
def test_only_catalogue_confirmation_moves_up_for_ocr_and_fallback(height, ocr):
    width = round(height * 16 / 9)
    scale = height / 1080
    auto = SimpleNamespace(screenshot=Image.new("RGB", (width, height)))
    auto.find_language_text = Mock(return_value=(1185 * scale, 870 * scale - height * .76) if ocr else None)
    first = OBSERVATION.catalogue_confirm_button(auto)
    assert first == pytest.approx((1185 * scale, 860 * scale))
    auto.find_language_text.return_value = None
    assert OBSERVATION.modal_button(auto, True) == pytest.approx((1146 * scale, 730 * scale))
    assert OBSERVATION.modal_button(auto, False) == pytest.approx((772 * scale, 740 * scale))
    assert OBSERVATION._button(auto, "取消", "Cancel", OBSERVATION.coordinates((width, height))["cancel"]) == pytest.approx((765 * scale, 870 * scale))




