import asyncio
import threading

from module.automation.input_handlers.simulator.mumu_control import MumuControl


def test_nemu_ipc_calls_are_serialized_across_threads() -> None:
    control = object.__new__(MumuControl)
    control._ev = asyncio.new_event_loop()
    control._ev_lock = threading.RLock()
    first_entered = threading.Event()
    release_first = threading.Event()
    second_entered = threading.Event()
    errors: list[Exception] = []

    def first_call() -> int:
        first_entered.set()
        assert release_first.wait(timeout=1)
        return 0

    def second_call() -> int:
        second_entered.set()
        return 0

    def run_call(func) -> None:
        try:
            control.ev_run_sync(func)
        except Exception as exc:
            errors.append(exc)

    first_thread = threading.Thread(target=run_call, args=(first_call,))
    second_thread = threading.Thread(target=run_call, args=(second_call,))

    try:
        first_thread.start()
        assert first_entered.wait(timeout=1)

        second_thread.start()
        assert not second_entered.wait(timeout=0.1)

        release_first.set()
        first_thread.join(timeout=1)
        second_thread.join(timeout=1)

        assert not first_thread.is_alive()
        assert not second_thread.is_alive()
        assert second_entered.is_set()
        assert errors == []
    finally:
        release_first.set()
        first_thread.join(timeout=1)
        second_thread.join(timeout=1)
        control._ev.close()
