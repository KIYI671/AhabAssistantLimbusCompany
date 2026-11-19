"""操作间隔与单次输入的随机等待；不用于就绪等待、手势、轮询、调度或超时。"""

from math import isfinite
from random import expovariate, uniform
from time import sleep

INPUT_HOLD_JITTER = 0.001  # 单位：秒，绝对偏移 ±1 ms，非比例变化。


def _validate_delay(delay: float) -> None:
    """校验等待时长（秒），仅允许非负有限值。"""
    if not isfinite(delay) or delay < 0:
        raise ValueError("delay must be finite and non-negative")


def sleep_gameplay(delay: float) -> None:
    """以 delay（秒）为均值采样指数等待，越界值取 0.8～1.3 倍边界。

    限制后均值约为原值的 0.977 倍；零延迟保持为零。
    """
    _validate_delay(delay)
    duration = 0.0 if delay == 0 else min(1.3 * delay, max(0.8 * delay, expovariate(1 / delay)))
    sleep(duration)


def sleep_input_hold(delay: float) -> None:
    """单次按键、鼠标或触摸的按住时长（秒），在原值 ±1 ms 内均匀采样。

    下界不小于零；零延迟保持为零。
    """
    _validate_delay(delay)
    duration = 0.0 if delay == 0 else uniform(max(0.0, delay - INPUT_HOLD_JITTER), delay + INPUT_HOLD_JITTER)
    sleep(duration)
