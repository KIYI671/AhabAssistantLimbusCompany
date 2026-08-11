import importlib

from tasks.event.event_handling import EventHandling, extract_levels

event_module = importlib.import_module("tasks.event.event_handling")


class _FakeAuto:
    def __init__(self, matched_asset=None, ocr_data=False):
        self.matched_asset = matched_asset
        self.ocr_data = ocr_data
        self.find_calls = []
        self.position_clicks = []
        self.coordinate_clicks = []

    def find_element(self, asset, threshold=0.8):
        self.find_calls.append((asset, threshold))
        if asset == self.matched_asset:
            return (320, 640)
        return None

    def mouse_action_with_pos(self, position):
        self.position_clicks.append(position)

    def find_text_element(self, target, only_text=False):
        assert target == ""
        assert only_text is True
        return self.ocr_data

    def mouse_click(self, x, y):
        self.coordinate_clicks.append((x, y))


def test_extract_levels_accepts_exact_success_rate_text() -> None:
    assert extract_levels(["Very Low", "High", "Normal"]) == ["very low", "high", "normal"]


def test_decision_accepts_scaled_very_low_match(monkeypatch) -> None:
    fake_auto = _FakeAuto(matched_asset="event/very_low.png")
    monkeypatch.setattr(event_module, "auto", fake_auto)
    monkeypatch.setattr(event_module.time, "monotonic", lambda: 10.0)
    handler = EventHandling()

    assert handler.decision_event_handling() is True
    assert fake_auto.position_clicks == [(320, 640)]
    assert fake_auto.find_calls[-1] == ("event/very_low.png", EventHandling.SUCCESS_LEVEL_THRESHOLD)


def test_ocr_failure_rotates_fallback_without_click_spam(monkeypatch) -> None:
    fake_auto = _FakeAuto(ocr_data=False)
    timestamps = iter((10.0, 10.2, 11.0))
    monkeypatch.setattr(event_module, "auto", fake_auto)
    monkeypatch.setattr(event_module.time, "monotonic", lambda: next(timestamps))
    handler = EventHandling()

    assert handler.decision_event_handling() is True
    assert handler.decision_event_handling() is False
    assert handler.decision_event_handling() is True

    scale = event_module.cfg.set_win_size / 1440
    assert fake_auto.coordinate_clicks == [
        (150 * scale, 1300 * scale),
        (290 * scale, 1300 * scale),
    ]
