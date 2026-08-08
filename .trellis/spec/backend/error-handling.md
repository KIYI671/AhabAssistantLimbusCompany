# Error Handling

> Executable error-handling conventions for the Python automation layer.

## Overview

Automation loops must expose a bounded, explicit outcome instead of treating an unrecognized frame as the next navigation screen. For the daily battle flow, callers use `None` for “not this state”, `True` for “handled; retry the current loop”, and `False` for “terminal failure; do not continue this action”.

## Scenario: Daily event page and entry recovery

### 1. Scope / Trigger

- Trigger: a beta event result page can remain visible after battle while its template button is unavailable for about 40 seconds.
- Scope: `Battle.fight()`, `back_init_menu()`, and daily EXP/Thread entry navigation.
- Goal: an event result page must not be treated as a failed Thread entry, and recovery must have an explicit upper bound.

### 2. Signatures

```python
# tasks/event_page.py
OcrBounds = tuple[int, int, int, int]
OcrEntry = tuple[str, OcrBounds]

@dataclass(frozen=True)
class EventPageResolution:
    state: Literal["advance", "wait"]
    position: tuple[int, int] | None
    reason: str


def resolve_event_page(entries: list[OcrEntry]) -> EventPageResolution | None: ...

# tasks/daily/luxcavation.py
MAX_ENTRY_RECOVERY_ATTEMPTS = 1

def _recover_daily_entry(recovery_attempts: int, log_prefix: str) -> bool: ...
```

### 3. Contracts

| Input / outcome | Contract |
| --- | --- |
| `advance` | The OCR parser found an event action and supplies the target text-box center in `position`. |
| `wait` | A result (`判定成功` / `判定失败`) is visible but its continuation is not; `position` is `None`. |
| `None` | The OCR frame does not prove an event page; preserve the caller’s pre-existing state handling. |
| `advance` with `position is None` | Treat as bounded `wait`; never unpack or click `None`. |
| `back_init_menu(allow_restart=False)` event timeout | Return `False`; do not press ESC, click blank space, kill, or restart. |
| Daily entry budget exhausted | Run `_recover_daily_entry()` at most once; recovery failure or a second exhaustion returns `False`. |

`Battle.fight()` may reset its local `chance` for `advance` or `wait`, but must not reset `start_time`; the existing total battle timeout remains authoritative. `back_init_menu()` waits at most `EVENT_PAGE_WAIT_TIMEOUT` seconds according to `monotonic()` and refreshes its ordinary loop budget while that event-specific clock is active.

### 4. Validation & Error Matrix

| Condition | Required behavior |
| --- | --- |
| Result + `继续` OCR | Click the OCR center, log debug, continue the current loop. |
| Result without action | Wait one second, retain only the bounded event timer, continue. |
| OCR action template works | Keep the template-first path; do not run the OCR fallback first. |
| Server-error handler returns `True` | Skip normal page/event recognition for that iteration. |
| Server-error handler returns `False` | Stop the current action; do not continue navigation. |
| Event wait exceeds 60 seconds | `allow_restart=False`: return `False`; otherwise reuse the established restart branch. |
| Entry recovery succeeds once | Reset entry loop state and perform one complete retry. |
| Entry recovery is unavailable or already used | Return `False`; callers must not select a team or start battle. |

### 5. Good / Base / Bad Cases

- **Good:** `判定成功` and `继续` are both OCR-visible; click the continuation center and resume battle.
- **Base:** a result remains visible during its animation; wait without consuming the battle chance or the general return-home loop budget.
- **Bad:** a standalone `继续` or `进行判定` is insufficient evidence. A “进行判定” target must have a separate event-context OCR entry; the button text itself cannot supply that context.

### 6. Tests Required

- Pure parser tests must import `tasks.event_page` and run without RapidOCR installed.
- Test result success and failure without a button → `wait`; result plus continuation → `advance` at the OCR center.
- Test all event contexts (`事件`, `判定`, `选项`) and ensure standalone/annotated “进行判定” buttons do not self-authorize.
- Test `Battle.fight()` with an exhausted local chance: wait and advance must still reach settlement; removing either reset must fail the test.
- Test `back_init_menu()` after 40 event-wait iterations, at 60-second timeout, after a non-event reset, and with `allow_restart=False`.
- Parameterize EXP and Thread entry tests for one recovery success, recovery failure, and second exhaustion.

### 7. Wrong vs Correct

#### Wrong

```python
if loop_count < 0:
    return False
# A result animation can exhaust this 30-iteration budget before its button appears.
```

#### Correct

```python
if event_wait_started_at is not None and monotonic() - event_wait_started_at < EVENT_PAGE_WAIT_TIMEOUT:
    loop_count = LOOP_COUNT
    sleep(1)
    continue
```

The monotonic event timer, not the general navigation loop, controls event-result patience.

## Common Mistakes

- Do not add a per-event “土偶/罪人” template merely because one result page failed; extend the shared OCR parser with an evidence-backed semantic boundary.
- Do not use `time.time()` for bounded UI waits that should ignore wall-clock adjustments; use `monotonic()`.
- Do not continue to team selection or `Battle.to_battle()` after an entry function returns `False`.
