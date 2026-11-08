# Timing policies

Timing variation is opt-in through `utils/timing.py`. Do not replace every
`sleep()` call: many waits are required for readiness or gesture correctness.

## Gameplay pacing

`sleep_gameplay(delay)` samples an exponential distribution with the existing
delay as its mean, then **clamps** the result to `[0.8 * delay, 1.3 * delay]`.
For example, a 0.5-second pause becomes 0.4–0.65 seconds.

This is clamping, not rejection sampling: out-of-range samples land on the
bounds. The underlying exponential retains the original mean, but the final
clamped mean is approximately `0.977 * delay`. Zero delays remain zero.

Use this for deliberate pauses between discrete player actions, such as
P → Enter, repeated selection clicks, and selection → confirmation. A direct
inter-action pause may use `cfg.mouse_action_interval`; this does not change
the separate elapsed-time scheduling logic in `Automation`.

## Discrete input holds

`sleep_input_hold(delay)` samples uniformly within ±1 ms of the original hold.
A 15 ms key/touch hold therefore becomes 14–16 ms. The lower bound cannot be
negative, and zero stays zero.

- Background clicks vary only their additional 30 ms pressed interval; fixed
  dispatch sleeps remain unchanged, so total hold variation is still ±1 ms.
- Window-move clicks explicitly opt in. Drag/swipe callers retain fixed timing.
- MuMu key, tap, and long-click holds vary; post-release waits do not.
- PyAutoGUI/ADB-managed input timing is not overridden with new hold durations.

## Unchanged timing

Keep readiness/loading/animation waits, gesture sampling and settling,
polling/retries/synchronization, calculated action/screenshot schedules,
resource countdowns, and timeouts/deadlines unchanged.

## Tests

Run `python -m pytest tests/test_timing.py tests/test_timing_integration.py`.
The integration tests exercise extracted production function bodies with
mocked backends, avoiding Windows/Qt/emulator imports and real sleeps.
They do not replace live Windows or emulator testing.
