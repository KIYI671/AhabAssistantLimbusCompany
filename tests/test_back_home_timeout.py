from types import SimpleNamespace

import pytest

from tasks.base import back_init_menu as recovery


@pytest.mark.parametrize("loading", [False, True])
@pytest.mark.parametrize("timeout", [90, 600])
def test_return_home_waits_for_configured_time_even_after_30_loops(monkeypatch, loading, timeout):
    elapsed = 0

    def retry():
        nonlocal elapsed
        elapsed += 1
        return True

    auto = SimpleNamespace(
        model="clam",
        click_element=lambda *args, **kwargs: False,
        find_element=lambda target, **kwargs: loading and target == "base/waiting_assets.png",
        mouse_click_blank=lambda: None,
        key_press=lambda *args: None,
    )
    monkeypatch.setattr(recovery, "auto", auto)
    monkeypatch.setattr(recovery, "monotonic", lambda: elapsed)
    monkeypatch.setattr(recovery, "get_task_stall_timeout", lambda: timeout)
    monkeypatch.setattr(recovery, "retry", retry)
    monkeypatch.setattr(recovery, "ensure_simulator_game_started", lambda: False)
    monkeypatch.setattr(recovery, "update_model_for_retry", lambda *args, **kwargs: None)

    assert recovery.back_init_menu(allow_restart=False) is False
    assert elapsed == timeout
