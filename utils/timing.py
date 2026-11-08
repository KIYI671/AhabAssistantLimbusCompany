"""Opt-in timing variation for gameplay pacing and discrete input holds.

Do not use these helpers for readiness waits, gesture sampling, polling,
calculated scheduling, or deadlines.
"""

from math import isfinite
from random import expovariate, uniform
from time import sleep

INPUT_HOLD_JITTER = 0.001  # Seconds: +/- 1 ms, not a proportional change.


def _validate_delay(delay: float) -> None:
    if not isfinite(delay) or delay < 0:
        raise ValueError("delay must be finite and non-negative")


def sleep_gameplay(delay: float) -> None:
    """Sleep for Exp(mean=delay), clamped to [0.8 * delay, 1.3 * delay].

    Clamping, rather than rejection sampling, preserves a strict timing band.
    The underlying exponential has the original mean; the clamped result has
    an expected value of about 0.977 * delay. Zero remains a zero-length sleep.
    """
    _validate_delay(delay)
    duration = 0.0 if delay == 0 else min(1.3 * delay, max(0.8 * delay, expovariate(1 / delay)))
    sleep(duration)


def sleep_input_hold(delay: float) -> None:
    """Vary a discrete key/button/touch hold uniformly by at most +/- 1 ms.

    Very short holds use a non-negative lower bound. Zero stays zero, so this
    helper does not introduce a hold where there was none.
    """
    _validate_delay(delay)
    duration = 0.0 if delay == 0 else uniform(max(0.0, delay - INPUT_HOLD_JITTER), delay + INPUT_HOLD_JITTER)
    sleep(duration)
