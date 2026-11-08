from unittest.mock import Mock

import pytest

from utils import timing


@pytest.mark.parametrize("delay", [0.1, 0.5, 1.0, 3.0])
@pytest.mark.parametrize("sample_ratio", [0.0, 0.5, 0.8, 1.0, 1.3, 5.0])
def test_gameplay_sleep_samples_original_mean_and_clamps(monkeypatch, delay, sample_ratio):
    sampler = Mock(return_value=delay * sample_ratio)
    sleeper = Mock()
    monkeypatch.setattr(timing, "expovariate", sampler)
    monkeypatch.setattr(timing, "sleep", sleeper)

    timing.sleep_gameplay(delay)

    sampler.assert_called_once_with(1 / delay)
    sleeper.assert_called_once_with(pytest.approx(delay * min(1.3, max(0.8, sample_ratio))))


def test_gameplay_sleep_draws_a_fresh_sample_for_each_action(monkeypatch):
    sampler = Mock(side_effect=[0.01, 0.5, 10.0])
    sleeper = Mock()
    monkeypatch.setattr(timing, "expovariate", sampler)
    monkeypatch.setattr(timing, "sleep", sleeper)

    for _ in range(3):
        timing.sleep_gameplay(0.5)

    assert sampler.call_count == 3
    assert [call.args[0] for call in sleeper.call_args_list] == pytest.approx([0.4, 0.5, 0.65])


@pytest.mark.parametrize("delay", [0.0005, 0.01, 0.015, 0.03, 0.12, 2.0])
@pytest.mark.parametrize("fraction", [0.0, 0.5, 1.0])
def test_input_hold_uses_absolute_one_millisecond_uniform_jitter(monkeypatch, delay, fraction):
    lower = max(0.0, delay - 0.001)
    upper = delay + 0.001
    sample = lower + fraction * (upper - lower)
    sampler = Mock(return_value=sample)
    sleeper = Mock()
    monkeypatch.setattr(timing, "uniform", sampler)
    monkeypatch.setattr(timing, "sleep", sleeper)

    timing.sleep_input_hold(delay)

    sampler.assert_called_once_with(pytest.approx(lower), pytest.approx(upper))
    sleeper.assert_called_once_with(sample)
    assert lower >= 0


@pytest.mark.parametrize("helper", [timing.sleep_gameplay, timing.sleep_input_hold])
def test_zero_delay_does_not_introduce_a_wait_or_sample(monkeypatch, helper):
    exponential = Mock()
    uniform = Mock()
    sleeper = Mock()
    monkeypatch.setattr(timing, "expovariate", exponential)
    monkeypatch.setattr(timing, "uniform", uniform)
    monkeypatch.setattr(timing, "sleep", sleeper)

    helper(0)

    sleeper.assert_called_once_with(0)
    exponential.assert_not_called()
    uniform.assert_not_called()


@pytest.mark.parametrize("helper", [timing.sleep_gameplay, timing.sleep_input_hold])
@pytest.mark.parametrize("delay", [-1.0, float("nan"), float("inf"), float("-inf")])
def test_invalid_delays_fail_before_sampling_or_sleeping(monkeypatch, helper, delay):
    exponential = Mock()
    uniform = Mock()
    sleeper = Mock()
    monkeypatch.setattr(timing, "expovariate", exponential)
    monkeypatch.setattr(timing, "uniform", uniform)
    monkeypatch.setattr(timing, "sleep", sleeper)

    with pytest.raises(ValueError, match="finite and non-negative"):
        helper(delay)

    sleeper.assert_not_called()
    exponential.assert_not_called()
    uniform.assert_not_called()
