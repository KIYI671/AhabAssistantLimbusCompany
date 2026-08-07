import threading
from types import SimpleNamespace

from module.automation.automation import Automation


def test_mouse_click_waits_until_monitor_resumes_interactions() -> None:
    clicks = []
    automation = object.__new__(Automation)
    automation._interaction_gate = threading.Event()
    automation._input_lock = threading.RLock()
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


def test_blank_click_uses_the_same_interaction_gate() -> None:
    clicks = []
    automation = object.__new__(Automation)
    automation._interaction_gate = threading.Event()
    automation._input_lock = threading.RLock()
    automation.input_handler = SimpleNamespace(
        mouse_click_blank=lambda: clicks.append("blank") or True,
    )

    click_thread = threading.Thread(target=automation.mouse_click_blank)
    click_thread.start()

    click_thread.join(timeout=0.1)
    assert click_thread.is_alive()
    assert clicks == []

    automation.resume_interactions()
    click_thread.join(timeout=1)

    assert not click_thread.is_alive()
    assert clicks == ["blank"]


def test_monitor_and_business_inputs_cannot_enter_handler_concurrently() -> None:
    monitor_entered = threading.Event()
    release_monitor = threading.Event()
    business_entered = threading.Event()
    automation = object.__new__(Automation)
    automation._interaction_gate = threading.Event()
    automation._interaction_gate.set()
    automation._input_lock = threading.RLock()

    def monitor_click(_x, _y, times=1):
        monitor_entered.set()
        assert release_monitor.wait(timeout=1)
        return True

    def blank_click():
        business_entered.set()
        return True

    automation.input_handler = SimpleNamespace(
        mouse_click=monitor_click,
        mouse_click_blank=blank_click,
    )

    monitor_thread = threading.Thread(target=lambda: automation.monitor_mouse_click(927, 583))
    monitor_thread.start()
    assert monitor_entered.wait(timeout=1)

    business_thread = threading.Thread(target=automation.mouse_click_blank)
    business_thread.start()
    assert not business_entered.wait(timeout=0.1)

    release_monitor.set()
    monitor_thread.join(timeout=1)
    business_thread.join(timeout=1)

    assert not monitor_thread.is_alive()
    assert not business_thread.is_alive()
    assert business_entered.is_set()


def test_business_input_rechecks_gate_after_waiting_for_input_lock() -> None:
    business_entered = threading.Event()
    automation = object.__new__(Automation)
    automation._interaction_gate = threading.Event()
    automation._interaction_gate.set()
    automation._input_lock = threading.RLock()
    automation.input_handler = SimpleNamespace(
        mouse_click_blank=lambda: business_entered.set() or True,
    )

    automation._input_lock.acquire()
    business_thread = threading.Thread(target=automation.mouse_click_blank)
    business_thread.start()
    automation.suspend_interactions()
    automation._input_lock.release()

    assert not business_entered.wait(timeout=0.1)

    automation.resume_interactions()
    business_thread.join(timeout=1)

    assert not business_thread.is_alive()
    assert business_entered.is_set()
