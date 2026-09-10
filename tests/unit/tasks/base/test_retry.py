import importlib
from types import SimpleNamespace

retry_module = importlib.import_module("tasks.base.retry")


class _RetryAuto:
    def __init__(self):
        self.screenshot_calls = 0
        self.frame_reusable = False

    def can_reuse_current_frame(self):
        return self.frame_reusable

    def get_restore_time(self):
        return 0

    def take_screenshot(self):
        self.screenshot_calls += 1
        return object()

    def find_element(self, *args, **kwargs):
        return None

    def click_element(self, *args, **kwargs):
        return False


def _prepare_retry(monkeypatch):
    fake_auto = _RetryAuto()
    monkeypatch.setattr(retry_module, "auto", fake_auto)
    monkeypatch.setattr(retry_module.cfg.config, "simulator", False)
    monkeypatch.setattr(retry_module, "screen", SimpleNamespace(handle=SimpleNamespace(hwnd=1)))
    monkeypatch.setattr(retry_module, "ensure_simulator_game_started", lambda: False)
    monkeypatch.setattr(retry_module, "check_times", lambda start_time: False)
    return fake_auto


def test_retry_reuses_a_fresh_current_frame_when_requested(monkeypatch):
    fake_auto = _prepare_retry(monkeypatch)

    assert retry_module.retry(skip_first_screenshot=True) is None
    assert fake_auto.screenshot_calls == 0


def test_retry_refreshes_a_dirty_frame_by_default(monkeypatch):
    fake_auto = _prepare_retry(monkeypatch)

    assert retry_module.retry() is None
    assert fake_auto.screenshot_calls == 1


def test_retry_automatically_reuses_an_unchanged_frame(monkeypatch):
    fake_auto = _prepare_retry(monkeypatch)
    fake_auto.frame_reusable = True

    assert retry_module.retry() is None
    assert fake_auto.screenshot_calls == 0
