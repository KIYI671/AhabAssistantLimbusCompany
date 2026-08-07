from types import SimpleNamespace

from tasks.base import retry


def test_task_stall_timeout_uses_configured_value(monkeypatch) -> None:
    monkeypatch.setattr(
        retry,
        "cfg",
        SimpleNamespace(get_value=lambda key, default: 720),
    )

    assert retry.get_task_stall_timeout() == 720


def test_task_stall_timeout_enforces_safe_minimum(monkeypatch) -> None:
    monkeypatch.setattr(
        retry,
        "cfg",
        SimpleNamespace(get_value=lambda key, default: 0),
    )

    assert retry.get_task_stall_timeout() == retry.MIN_TASK_STALL_TIMEOUT


def test_check_times_uses_configured_timeout_by_default(monkeypatch) -> None:
    start_time = 1_700_000_000.0
    actions: list[str] = []
    monkeypatch.setattr(retry, "get_task_stall_timeout", lambda: 600)
    monkeypatch.setattr(retry.time, "time", lambda: start_time + 599)
    monkeypatch.setattr(retry, "kill_game", lambda: actions.append("kill"))
    monkeypatch.setattr(retry, "restart_game", lambda: actions.append("restart"))

    assert retry.check_times(start_time, logs=False) is False
    assert actions == []

    monkeypatch.setattr(retry.time, "time", lambda: start_time + 601)

    assert retry.check_times(start_time, logs=False) is True
    assert actions == ["kill", "restart"]


def test_check_times_preserves_explicit_flow_timeout(monkeypatch) -> None:
    start_time = 1_700_000_000.0
    actions: list[str] = []
    monkeypatch.setattr(retry, "get_task_stall_timeout", lambda: 600)
    monkeypatch.setattr(retry.time, "time", lambda: start_time + 901)
    monkeypatch.setattr(retry, "kill_game", lambda: actions.append("kill"))
    monkeypatch.setattr(retry, "restart_game", lambda: actions.append("restart"))

    assert retry.check_times(start_time, timeout=1_200, logs=False) is False
    assert actions == []
