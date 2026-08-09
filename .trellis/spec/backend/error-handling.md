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
| Choice page first button is grey | Do not invoke the first-choice template; click only the OCR-located second slot. |
| Choice page first button is not grey | Retry only the first slot (template first, OCR fallback); never infer grey state merely because the page persisted. |
| Choice page has no OCR candidate or does not advance repeatedly | After `EVENT_CHOICE_MAX_RETRY_ATTEMPTS`, return `False`; do not wait for the total battle timeout. |
| Daily battle exits without `战斗胜利 + 确认` settlement | Return `False`; callers must cancel the daily group and top-level task sequence. |

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
- Parameterize EXP and Thread entry tests for one recovery success, recovery failure, renewal-recovery failure, and second exhaustion.
- Test grey first choice → second-slot click, enabled first choice → first-slot retry, absent candidate → bounded `False`, and repeated non-advancing candidate → bounded `False`.
- Test a battle exit without daily settlement and each propagation boundary: single daily process, group, wrapper, startup-resume path, and top-level task sequence.

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

## Scenario: Windows Steam launch and graceful exit recovery

### 1. Scope / Trigger

- Trigger: a forced game termination can leave Steam cloud synchronization incomplete; the next Steam launch can show the Chinese “无法同步” confirmation while the Unity process exists but the game window is not ready.
- Scope: `module.game_and_screen.game`, `module.game_and_screen.steam_cloud`, `module.game_and_screen.screen`, `tasks.base.script_task_scheme`, and every Windows restart/exit caller.
- Goal: perform one bounded launch request, automatically confirm only the user-authorized cloud-sync dialog, and avoid unnecessary forced process termination.

### 2. Signatures

```python
# module/game_and_screen/steam_cloud.py
@dataclass(frozen=True)
class SteamCloudDialog:
    continue_position: tuple[int, int]
    continue_bounds: OcrBounds


def resolve_steam_cloud_dialog(entries: list[OcrEntry]) -> SteamCloudDialog | None: ...
def handle_steam_cloud_sync_dialog(*, on_dialog_detected: Callable[[], None]) -> bool: ...

# module/game_and_screen/game.py
def start_game(self) -> bool: ...
def handle_pending_launch(self) -> bool: ...
def finish_launch_attempt(self) -> None: ...
def close_game(self) -> bool: ...

# module/game_and_screen/screen.py
def init_handle(self, start_if_missing: bool = True) -> bool: ...
```

### 3. Contracts

| Input / outcome | Contract |
| --- | --- |
| Existing game process, no window | Create a pending launch state; do not re-open Steam, but permit one cloud-dialog scan during the bounded wait. |
| Pending launch | `start_game()` is idempotent while the request is pending; no second local-path or Steam URL launch. |
| Valid cloud dialog | Require normalized Chinese title `无法同步`, body fragments `未能将您的存档` and `Steam 云同步`, an exact `仍然进行游戏` button, button below the body, and all anchors in one bounded desktop region. |
| Valid cloud dialog click | Call `on_dialog_detected` before desktop click so a thrown click cannot authorize a second attempt in the same pending launch. |
| Missing/ambiguous dialog evidence | Do not click any Steam control; retain the bounded launch wait only. |
| Launch timeout | Clear pending state and raise `withOutGameWinError`; callers must stop the current task instead of retrying Steam indefinitely. |
| Windows exit | Clear pending state, send `WM_CLOSE` to a valid game window, wait `GAME_GRACEFUL_CLOSE_TIMEOUT_SECONDS`, then use the sole `taskkill /F /IM <exact process name>` fallback. |

### 4. Validation & Error Matrix

| Condition | Required behavior |
| --- | --- |
| Configured local game path exists | Use `os.startfile` once and log the local launch. |
| Configured path missing | Log once with the path-repair hint, then request Steam URL once. |
| Full process filename has different case | Treat it as the game process. |
| Process name merely contains the configured name | Treat it as unrelated; do not suppress launch or terminate it. |
| Cloud anchors come from different desktop regions | Return `None`; never click. |
| Click throws after target recognition | Consume the single confirmation attempt and return `False`; do not retry clicking. |
| Normal close completes during grace period | Do not run `taskkill`. |
| Normal close times out | Log a warning and use the single centralized process-name fallback. |

### 5. Good / Base / Bad Cases

- **Good:** `init_game()` launches once, polls `screen.init_handle(start_if_missing=False)`, sees the complete cloud dialog, consumes its one authorization, clicks `仍然进行游戏`, then receives the game window.
- **Base:** the Unity process exists while Steam still owns the confirmation; keep a pending state and wait up to the launch deadline without re-opening Steam.
- **Bad:** each missing-window poll calls `webbrowser.open`, or a generic desktop OCR keyword clicks a button in another Steam window.

### 6. Tests Required

- Pure dialog tests must reject missing anchors, cancel-only dialogs, a button above the body, and anchors split across desktop regions.
- Test one Steam URL request per pending launch, existing-process pending behavior, local-path preference, and launch-timeout cleanup.
- Test a click exception consumes the confirmation attempt.
- Test exact case-insensitive process matching and reject a similarly named process.
- Test `WM_CLOSE` first, no force kill on normal exit, force kill only on timeout, and every Windows exit/restart wrapper delegates to `Game.close_game()`.
- Top-level script tests that do not test image recognition must stub `auto.click_element`; they must never access the real screenshot/window/process stack.

### 7. Wrong vs Correct

#### Wrong

```python
while not screen.init_handle():
    game_process.start_game()  # Re-opens Steam while a cloud dialog blocks startup.
```

#### Correct

```python
if game_process.start_game():
    while monotonic() < deadline:
        if screen.init_handle(start_if_missing=False):
            game_process.finish_launch_attempt()
            break
        game_process.handle_pending_launch()
        sleep(1)
```

## Common Mistakes

- Do not add a per-event “土偶/罪人” template merely because one result page failed; extend the shared OCR parser with an evidence-backed semantic boundary.
- Do not use `time.time()` for bounded UI waits that should ignore wall-clock adjustments; use `monotonic()`.
- Do not continue to team selection or `Battle.to_battle()` after an entry function returns `False`.
- Do not use “the choice page remained visible” as evidence that the first choice is disabled; only the current RGB/HSV button state authorizes selecting the second choice.
- Do not emit the normal completion toast or perform completion actions after a daily task returns `False`.
