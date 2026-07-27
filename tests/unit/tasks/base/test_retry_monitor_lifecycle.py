from tasks.base import script_task_scheme


def test_terminating_script_stops_retry_monitor(monkeypatch) -> None:
    monitor_stops = []
    monkeypatch.setattr(
        script_task_scheme.retry_monitor,
        "stop",
        lambda: monitor_stops.append(True),
    )
    task = script_task_scheme.my_script_task()

    task.terminate()

    assert monitor_stops == [True]
