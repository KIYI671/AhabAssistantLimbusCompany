import threading
from types import SimpleNamespace

from module.automation.automation import Automation


def test_mouse_click_waits_until_monitor_resumes_interactions() -> None:
    clicks = []
    automation = object.__new__(Automation)
    automation._interaction_gate = threading.Event()
    automation.input_handler = SimpleNamespace(
        mouse_click=lambda x, y, times=1: clicks.append((x, y, times)) or True,
    )

    started = threading.Event()

    def click() -> None:
        started.set()
        automation.mouse_click(801, 583)

    click_thread = threading.Thread(target=click)
    click_thread.start()
    assert started.wait(timeout=1)
    assert clicks == []

    automation.resume_interactions()
    click_thread.join(timeout=1)

    assert not click_thread.is_alive()
    assert clicks == [(801, 583, 1)]
