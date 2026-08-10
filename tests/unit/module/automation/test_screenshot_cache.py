import threading

from PIL import Image

from module.automation.automation import Automation
from module.automation.screenshot import ScreenShot


def _automation_without_input_handler() -> Automation:
    automation = Automation.__new__(Automation)
    automation._screenshot_lock = threading.RLock()
    automation._latest_screenshot = None
    automation._latest_screenshot_monotonic = 0.0
    return automation


def test_monitor_reuses_recent_business_screenshot(monkeypatch) -> None:
    automation = _automation_without_input_handler()
    business_frame = Image.new("L", (6, 4), color=32)
    automation._remember_screenshot(business_frame)
    monkeypatch.setattr(
        ScreenShot,
        "take_screenshot",
        lambda gray=True: (_ for _ in ()).throw(AssertionError("must reuse cached frame")),
    )

    assert automation.take_monitor_screenshot(max_age=3.0) is business_frame


def test_monitor_takes_fresh_screenshot_after_cache_invalidation(monkeypatch) -> None:
    automation = _automation_without_input_handler()
    stale_frame = Image.new("L", (6, 4), color=32)
    fresh_frame = Image.new("L", (6, 4), color=64)
    automation._remember_screenshot(stale_frame)
    automation.invalidate_screenshot_cache()
    captures = []

    def take_screenshot(gray=True):
        captures.append(gray)
        return fresh_frame

    monkeypatch.setattr(ScreenShot, "take_screenshot", take_screenshot)

    assert automation.take_monitor_screenshot(max_age=3.0) is fresh_frame
    assert captures == [True]
