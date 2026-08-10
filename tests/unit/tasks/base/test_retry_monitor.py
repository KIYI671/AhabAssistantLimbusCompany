from types import SimpleNamespace

import numpy as np

from tasks.base import retry_monitor


def test_check_once_clicks_strict_retry_match(monkeypatch) -> None:
    screenshot = object()
    clicks = []
    gates = []
    fake_auto = SimpleNamespace(
        check_pause=lambda: False,
        monitor_mouse_click=lambda x, y: clicks.append((x, y)),
        suspend_interactions=lambda: gates.append("suspend"),
        resume_interactions=lambda: gates.append("resume"),
        invalidate_screenshot_cache=lambda: None,
    )
    monitor = retry_monitor.RetryMonitor(click_cooldown=0)
    monitor._templates = (np.zeros((2, 2), dtype=np.uint8),)

    monkeypatch.setattr(retry_monitor, "auto", fake_auto)
    monkeypatch.setattr(monitor, "_find_retry_button", lambda _screenshot: (927, 583))

    assert monitor.check_once(screenshot) is True
    assert clicks == [(927, 583)]
    assert gates == ["suspend"]


def test_check_once_does_not_click_while_task_is_paused(monkeypatch) -> None:
    fake_auto = SimpleNamespace(
        check_pause=lambda: True,
        monitor_mouse_click=lambda *_args: (_ for _ in ()).throw(AssertionError("must not click")),
        suspend_interactions=lambda: None,
        resume_interactions=lambda: None,
        invalidate_screenshot_cache=lambda: None,
    )
    monitor = retry_monitor.RetryMonitor(click_cooldown=0)

    monkeypatch.setattr(retry_monitor, "auto", fake_auto)
    monkeypatch.setattr(
        monitor,
        "_find_retry_button",
        lambda _screenshot: (_ for _ in ()).throw(AssertionError("must not match while paused")),
    )

    assert monitor.check_once(object()) is False


def test_check_once_resumes_business_after_two_clear_frames(monkeypatch) -> None:
    gates = []
    fake_auto = SimpleNamespace(
        check_pause=lambda: False,
        monitor_mouse_click=lambda _x, _y: None,
        suspend_interactions=lambda: gates.append("suspend"),
        resume_interactions=lambda: gates.append("resume"),
        invalidate_screenshot_cache=lambda: None,
    )
    monitor = retry_monitor.RetryMonitor(click_cooldown=0)

    monkeypatch.setattr(retry_monitor, "auto", fake_auto)
    matches = iter(((927, 583), None, None))
    monkeypatch.setattr(monitor, "_find_retry_button", lambda _screenshot: next(matches))

    assert monitor.check_once(object()) is True
    assert monitor.check_once(object()) is False
    assert monitor.check_once(object()) is False
    assert gates == ["suspend", "resume"]


def test_stop_always_restores_business_interactions(monkeypatch) -> None:
    gates = []
    fake_auto = SimpleNamespace(resume_interactions=lambda: gates.append("resume"))
    monitor = retry_monitor.RetryMonitor()
    monitor._handling_retry = True

    monkeypatch.setattr(retry_monitor, "auto", fake_auto)

    monitor.stop()

    assert monitor._handling_retry is False
    assert gates == ["resume"]
