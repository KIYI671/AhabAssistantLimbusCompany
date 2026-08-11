import importlib
from types import SimpleNamespace

import numpy as np
import pytest
from PIL import Image

automation_module = importlib.import_module("module.automation.automation")
Automation = automation_module.Automation


def _make_automation(image):
    instance = object.__new__(Automation)
    instance.screenshot = image
    instance.img_cache = {}
    instance.memory_protection = False
    instance._last_memory_check_time = 0.0
    instance.model = "clam"
    instance._reset_frame_cache(image)
    return instance


def test_screenshot_array_is_reused_and_direct_assignment_invalidates_cache():
    first = Image.fromarray(np.arange(16, dtype=np.uint8).reshape(4, 4))
    second = Image.fromarray(np.full((4, 4), 7, dtype=np.uint8))
    instance = _make_automation(first)

    first_array = instance.get_screenshot_array()
    assert instance.get_screenshot_array() is first_array

    instance._frame_match_cache["old"] = True
    instance.screenshot = second
    second_array = instance.get_screenshot_array()

    assert second_array is not first_array
    assert np.all(second_array == 7)
    assert instance._frame_match_cache == {}


def test_single_image_match_is_cached_for_current_frame(monkeypatch):
    instance = _make_automation(Image.fromarray(np.zeros((20, 20), dtype=np.uint8)))
    calls = 0

    monkeypatch.setattr(automation_module.path_manager, "current_theme", "default")
    monkeypatch.setattr(automation_module.path_manager, "current_language", "en")
    monkeypatch.setattr(automation_module.path_manager, "active_paths", ["default/en"])
    monkeypatch.setattr(automation_module.ImageUtils, "existing_image_paths", lambda target: ["default/en"])
    monkeypatch.setattr(instance, "_load_template_for_path", lambda target, path, cacheable: (np.zeros((2, 2)), None))

    def match_template(*args, **kwargs):
        nonlocal calls
        calls += 1
        return (5, 6), 0.95

    monkeypatch.setattr(automation_module.ImageUtils, "match_template", match_template)

    assert instance.find_image_element("target.png", 0.8) == (5, 6)
    assert instance.find_image_element("target.png", 0.8) == (5, 6)
    assert calls == 1

    instance.screenshot = Image.fromarray(np.ones((20, 20), dtype=np.uint8))
    assert instance.find_image_element("target.png", 0.8) == (5, 6)
    assert calls == 2


def test_multiple_image_match_cache_returns_a_defensive_copy(monkeypatch):
    instance = _make_automation(Image.fromarray(np.zeros((20, 20), dtype=np.uint8)))
    calls = 0

    monkeypatch.setattr(automation_module.path_manager, "current_theme", "default")
    monkeypatch.setattr(automation_module.path_manager, "current_language", "en")
    monkeypatch.setattr(automation_module.path_manager, "active_paths", ["default/en"])
    monkeypatch.setattr(automation_module.ImageUtils, "existing_image_paths", lambda target: ["default/en"])
    monkeypatch.setattr(instance, "_load_template_for_path", lambda target, path, cacheable: (np.zeros((2, 2)), None))

    def match_multiple(*args, **kwargs):
        nonlocal calls
        calls += 1
        return [(3, 4)]

    monkeypatch.setattr(automation_module.ImageUtils, "match_template_with_multiple_targets", match_multiple)

    first = instance.find_image_with_multiple_targets("target.png", 0.8)
    first.append((9, 9))
    second = instance.find_image_with_multiple_targets("target.png", 0.8)

    assert second == [(3, 4)]
    assert calls == 1


def test_ocr_result_is_cached_per_frame_and_crop(monkeypatch):
    instance = _make_automation(Image.fromarray(np.zeros((20, 20), dtype=np.uint8)))
    calls = 0
    result = SimpleNamespace(txts=["Turn"], boxes=[])

    def run_ocr(image):
        nonlocal calls
        calls += 1
        return result

    monkeypatch.setattr(automation_module.ocr, "run", run_ocr)

    assert instance._get_cached_ocr_result((0, 0, 10, 10)) is result
    assert instance._get_cached_ocr_result((0, 0, 10, 10)) is result
    assert calls == 1

    instance.screenshot = Image.fromarray(np.ones((20, 20), dtype=np.uint8))
    assert instance._get_cached_ocr_result((0, 0, 10, 10)) is result
    assert calls == 2


def test_memory_pressure_check_is_throttled(monkeypatch):
    instance = _make_automation(Image.fromarray(np.zeros((2, 2), dtype=np.uint8)))
    instance.memory_protection = True
    instance._last_memory_check_time = 100.0
    times = iter([101.0, 106.0])
    calls = 0

    monkeypatch.setattr(automation_module.time, "monotonic", lambda: next(times))

    def virtual_memory():
        nonlocal calls
        calls += 1
        return SimpleNamespace(percent=50)

    monkeypatch.setattr(automation_module.psutil, "virtual_memory", virtual_memory)

    instance._check_memory_pressure()
    instance._check_memory_pressure()
    assert calls == 1


def test_screenshot_call_can_use_a_short_local_interval_without_changing_config(monkeypatch):
    image = Image.fromarray(np.zeros((4, 4), dtype=np.uint8))
    instance = _make_automation(image)
    instance.last_screenshot_time = 9.9
    sleeps = []
    configured_interval = automation_module.cfg.screenshot_interval

    times = iter([9.95, 10.0, 10.15, 10.15])
    monkeypatch.setattr(automation_module.time, "monotonic", lambda: next(times))
    monkeypatch.setattr(automation_module.time, "sleep", sleeps.append)
    monkeypatch.setattr(automation_module.ScreenShot, "take_screenshot", lambda gray: image)

    assert instance.take_screenshot(interval=0.25) is image
    assert sleeps == [pytest.approx(0.15)]
    assert automation_module.cfg.screenshot_interval == configured_interval
    assert instance.can_reuse_current_frame()


def test_successful_input_marks_the_current_frame_dirty():
    instance = _make_automation(Image.fromarray(np.zeros((4, 4), dtype=np.uint8)))
    instance._frame_dirty = False
    wrapped = instance._mark_frame_dirty_after(lambda: True)

    assert wrapped() is True
    assert not instance.can_reuse_current_frame()


def test_failed_input_does_not_invalidate_the_current_frame():
    instance = _make_automation(Image.fromarray(np.zeros((4, 4), dtype=np.uint8)))
    instance._frame_dirty = False
    wrapped = instance._mark_frame_dirty_after(lambda: False)

    assert wrapped() is False
    assert instance.can_reuse_current_frame()


def test_old_frame_is_not_reused_even_without_input(monkeypatch):
    instance = _make_automation(Image.fromarray(np.zeros((4, 4), dtype=np.uint8)))
    instance._frame_dirty = False
    instance.last_screenshot_time = 10.0
    monkeypatch.setattr(automation_module.time, "monotonic", lambda: 10.6)

    assert not instance.can_reuse_current_frame(max_age=0.5)


def test_click_cooldown_blocks_only_the_same_target(monkeypatch):
    instance = _make_automation(Image.fromarray(np.zeros((4, 4), dtype=np.uint8)))
    instance._last_target_action_time = {}
    actions = []
    times = iter([10.0, 10.1, 10.1])

    monkeypatch.setattr(instance, "find_element", lambda *_args, **_kwargs: (1, 2))
    monkeypatch.setattr(instance, "mouse_action_with_pos", lambda *args, **_kwargs: actions.append(args) or True)
    monkeypatch.setattr(automation_module.time, "monotonic", lambda: next(times))

    assert instance.click_element("first.png", interval=0.5)
    assert not instance.click_element("first.png", interval=0.5)
    assert instance.click_element("second.png", interval=0.5)
    assert len(actions) == 2


def test_click_cooldown_allows_the_same_target_after_expiry(monkeypatch):
    instance = _make_automation(Image.fromarray(np.zeros((4, 4), dtype=np.uint8)))
    instance._last_target_action_time = {}
    actions = []
    times = iter([10.0, 10.6, 10.6])

    monkeypatch.setattr(instance, "find_element", lambda *_args, **_kwargs: (1, 2))
    monkeypatch.setattr(instance, "mouse_action_with_pos", lambda *args, **_kwargs: actions.append(args) or True)
    monkeypatch.setattr(automation_module.time, "monotonic", lambda: next(times))

    assert instance.click_element("target.png", interval=0.5)
    assert instance.click_element("target.png", interval=0.5)
    assert len(actions) == 2


def test_first_mouse_action_does_not_wait_for_a_nonexistent_previous_click(monkeypatch):
    instance = _make_automation(Image.fromarray(np.zeros((4, 4), dtype=np.uint8)))
    instance.last_click_time = 0
    clicks = []
    sleeps = []

    monkeypatch.setattr(instance, "calculate_click_position", lambda *_args: (1, 2))
    monkeypatch.setattr(
        instance,
        "mouse_click",
        lambda x, y, times=1: clicks.append((x, y, times)),
        raising=False,
    )
    monkeypatch.setattr(instance, "mouse_drag", lambda *_args, **_kwargs: None, raising=False)
    monkeypatch.setattr(instance, "mouse_drag_down", lambda *_args, **_kwargs: None, raising=False)
    monkeypatch.setattr(instance, "mouse_scroll", lambda *_args, **_kwargs: None, raising=False)
    monkeypatch.setattr(automation_module.time, "monotonic", lambda: 10.0)
    monkeypatch.setattr(automation_module.time, "sleep", sleeps.append)

    assert instance.mouse_action_with_pos((1, 2), interval=0.2)
    assert clicks == [(1, 2, 1)]
    assert sleeps == []
    assert instance.last_click_time == 10.0


def test_later_mouse_action_waits_only_for_remaining_cooldown(monkeypatch):
    instance = _make_automation(Image.fromarray(np.zeros((4, 4), dtype=np.uint8)))
    instance.last_click_time = 9.9
    sleeps = []
    times = iter([10.0, 10.2])

    monkeypatch.setattr(instance, "calculate_click_position", lambda *_args: (1, 2))
    monkeypatch.setattr(instance, "mouse_click", lambda *_args, **_kwargs: None, raising=False)
    monkeypatch.setattr(instance, "mouse_drag", lambda *_args, **_kwargs: None, raising=False)
    monkeypatch.setattr(instance, "mouse_drag_down", lambda *_args, **_kwargs: None, raising=False)
    monkeypatch.setattr(instance, "mouse_scroll", lambda *_args, **_kwargs: None, raising=False)
    monkeypatch.setattr(automation_module.time, "monotonic", lambda: next(times))
    monkeypatch.setattr(automation_module.time, "sleep", sleeps.append)

    assert instance.mouse_action_with_pos((1, 2), interval=0.2)
    assert sleeps == [pytest.approx(0.1)]
    assert instance.last_click_time == 10.2


def test_mouse_action_does_not_yield_after_cooldown_has_elapsed(monkeypatch):
    instance = _make_automation(Image.fromarray(np.zeros((4, 4), dtype=np.uint8)))
    instance.last_click_time = 9.0
    sleeps = []
    times = iter([10.0, 10.0])

    monkeypatch.setattr(instance, "calculate_click_position", lambda *_args: (1, 2))
    monkeypatch.setattr(instance, "mouse_click", lambda *_args, **_kwargs: None, raising=False)
    monkeypatch.setattr(instance, "mouse_drag", lambda *_args, **_kwargs: None, raising=False)
    monkeypatch.setattr(instance, "mouse_drag_down", lambda *_args, **_kwargs: None, raising=False)
    monkeypatch.setattr(instance, "mouse_scroll", lambda *_args, **_kwargs: None, raising=False)
    monkeypatch.setattr(automation_module.time, "monotonic", lambda: next(times))
    monkeypatch.setattr(automation_module.time, "sleep", sleeps.append)

    assert instance.mouse_action_with_pos((1, 2), interval=0.2)
    assert sleeps == []


def test_wait_for_element_polls_new_frames_until_target_appears(monkeypatch):
    instance = _make_automation(Image.fromarray(np.zeros((4, 4), dtype=np.uint8)))
    instance._frame_dirty = True
    clock = [0.0]
    screenshots = []
    find_calls = [0]

    def take_screenshot(gray=True, interval=None):
        del gray
        clock[0] += interval
        screenshots.append(interval)
        instance._frame_dirty = False
        return instance.screenshot

    def find_element(*_args, **_kwargs):
        find_calls[0] += 1
        return (1, 2) if find_calls[0] == 3 else None

    monkeypatch.setattr(instance, "take_screenshot", take_screenshot)
    monkeypatch.setattr(instance, "find_element", find_element)
    monkeypatch.setattr(automation_module.time, "monotonic", lambda: clock[0])

    assert instance.wait_for_element("target.png", timeout=1.0, poll_interval=0.1) == (1, 2)
    assert screenshots == [0.1, 0.1, 0.1]


def test_wait_for_element_reuses_a_clean_current_frame(monkeypatch):
    instance = _make_automation(Image.fromarray(np.zeros((4, 4), dtype=np.uint8)))
    instance._frame_dirty = False
    screenshots = []

    monkeypatch.setattr(instance, "take_screenshot", lambda **_kwargs: screenshots.append(True))
    monkeypatch.setattr(instance, "find_element", lambda *_args, **_kwargs: (1, 2))

    assert instance.wait_for_element("target.png") == (1, 2)
    assert screenshots == []


def test_region_stability_waits_for_change_then_consecutive_stable_samples(monkeypatch):
    black = np.zeros((20, 20), dtype=np.uint8)
    white = np.full((20, 20), 255, dtype=np.uint8)
    instance = _make_automation(Image.fromarray(black))
    frames = iter([white, white, white])
    intervals = []
    clock = [0.0]

    def take_screenshot(gray=True, interval=None):
        del gray
        image = Image.fromarray(next(frames))
        instance.screenshot = image
        instance._reset_frame_cache(image)
        intervals.append(interval)
        return image

    def monotonic():
        clock[0] += 0.1
        return clock[0]

    monkeypatch.setattr(instance, "take_screenshot", take_screenshot)
    monkeypatch.setattr(automation_module.time, "monotonic", monotonic)

    assert instance.wait_until_region_stable(
        (0, 0, 20, 20),
        timeout=2.0,
        poll_interval=0.2,
        stable_samples=2,
        initial_sample=black,
        require_change=True,
    )
    assert intervals == [0.2, 0.2, 0.2]


def test_region_stability_does_not_accept_continuously_moving_region(monkeypatch):
    black = np.zeros((20, 20), dtype=np.uint8)
    white = np.full((20, 20), 255, dtype=np.uint8)
    instance = _make_automation(Image.fromarray(black))
    frame_index = [0]
    clock = [0.0]

    def take_screenshot(gray=True, interval=None):
        del gray, interval
        frame = white if frame_index[0] % 2 == 0 else black
        frame_index[0] += 1
        image = Image.fromarray(frame)
        instance.screenshot = image
        instance._reset_frame_cache(image)
        return image

    def monotonic():
        clock[0] += 0.1
        return clock[0]

    monkeypatch.setattr(instance, "take_screenshot", take_screenshot)
    monkeypatch.setattr(automation_module.time, "monotonic", monotonic)

    assert not instance.wait_until_region_stable(
        (0, 0, 20, 20),
        timeout=0.6,
        stable_samples=2,
        initial_sample=black,
        require_change=True,
    )


def test_region_stability_requires_a_real_transition_when_requested(monkeypatch):
    black = np.zeros((20, 20), dtype=np.uint8)
    instance = _make_automation(Image.fromarray(black))
    clock = [0.0]

    def take_screenshot(gray=True, interval=None):
        del gray, interval
        image = Image.fromarray(black)
        instance.screenshot = image
        instance._reset_frame_cache(image)
        return image

    def monotonic():
        clock[0] += 0.1
        return clock[0]

    monkeypatch.setattr(instance, "take_screenshot", take_screenshot)
    monkeypatch.setattr(automation_module.time, "monotonic", monotonic)

    assert not instance.wait_until_region_stable(
        (0, 0, 20, 20),
        timeout=0.4,
        stable_samples=1,
        initial_sample=black,
        require_change=True,
    )
