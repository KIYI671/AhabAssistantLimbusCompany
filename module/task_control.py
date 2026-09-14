import threading

from module.my_error.my_error import userStopError

_stop_event = threading.Event()


def reset_stop_request() -> None:
    """Reset cooperative cancellation before a new script run."""
    _stop_event.clear()


def request_stop() -> None:
    """Ask the active script and its connection recovery code to stop."""
    _stop_event.set()


def stop_requested() -> bool:
    return _stop_event.is_set()


def raise_if_stop_requested() -> None:
    if stop_requested():
        raise userStopError("用户主动终止程序")
