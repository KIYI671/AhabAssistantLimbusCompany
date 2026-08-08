# Quality Guidelines

> Code quality standards for the Python automation layer.

## Overview

Automation behavior is a state machine over screenshots. New recognition paths must be bounded, testable without a live game, and unable to silently convert an unknown page into a navigation attempt.

## Required patterns

### Pure recognition boundaries

Place OCR-only parsing in a module that has no `Automation`, OCR engine, configuration, logging, sleep, or click dependency. Keep side effects in the caller.

```python
# Good: pure, importable in a lightweight test process.
def resolve_event_page(entries: list[OcrEntry]) -> EventPageResolution | None: ...

# Caller owns I/O and state changes.
resolution = resolve_event_page(auto.get_ocr_entries())
if resolution is not None and resolution.position is not None:
    auto.mouse_click(*resolution.position)
```

`tasks.event_page` is the current shared boundary for daily event OCR recognition. `tasks.event.event_handling` may re-export its public interface for compatibility, but new pure tests should import the lightweight module directly.

### Bounded recovery

Every page-recovery loop needs an explicit authority for its timeout. If a specialized wait is longer than a general retry loop, the specialized monotonic timeout must keep the general budget from expiring first. A recovery retry count must be a named constant and shared across equivalent flows.

### Template first, OCR second

Keep existing templates as the preferred recognition path. OCR fallback runs only after the relevant templates did not advance the page. A generic OCR keyword without enough page context is not a safe click target.

### Choice availability is a visual state, not a retry count

Daily event choices have an extra safety boundary: choose a second candidate only after the **first button itself** is confirmed grey in the RGB frame. `Automation.take_screenshot_with_color()` preserves RGB, so `is_first_event_choice_disabled()` may use `cv2.COLOR_RGB2HSV`. A persistent selection page is not evidence that the first option became unavailable.

```python
if is_first_event_choice_disabled(auto.color_screenshot, first_choice, choice_slot_spacing=spacing):
    auto.mouse_click(*second_choice)
else:
    # The first button is still usable: template first, then its OCR center.
    auto.click_element("event/select_first_option_assets.png") or auto.mouse_click(*first_choice)
```

Keep a named local retry limit (`EVENT_CHOICE_MAX_RETRY_ATTEMPTS`) for a stable selection page. It must terminate to `False`; it must not consume the event-result animation budget or reset the total battle timeout.

## Forbidden patterns

- **Do not** reset a total task timeout just because a UI animation is being waited on; reset only the local recognition budget when the state is known.
- **Do not** add per-event text/template branches for a common event transition. Extend the shared parser and its state table instead.
- **Do not** duplicate EXP and Thread recovery budgets. Use one helper and one named maximum.
- **Do not** put a pure parser behind a package initializer that eagerly imports the OCR runtime; this makes unit tests depend on a game runtime unnecessarily.
- **Do not** treat a failed entry recovery as permission to proceed to team selection or battle start.
- **Do not** use a one-time “first choice attempted” flag that makes a non-advancing choice page wait forever or changes selection to the second option without a grey-state observation.
- **Do not** flatten a terminal `False` into `None` at a battle, daily-group, startup-resume, or top-level task boundary.

## Testing requirements

Run project tests through the managed environment:

```bash
uv run pytest
uv run ruff check tasks/battle/battle.py tasks/event_page.py tasks/event/event_handling.py tasks/base/back_init_menu.py tasks/daily/luxcavation.py tasks/base/script_task_scheme.py tests --ignore E722
```

`E722` is an existing baseline exemption, not permission to introduce new lint failures.

For daily event changes, tests must include:

- a pure OCR parser test runnable without RapidOCR;
- behavior-driven mutation-sensitive coverage showing event `wait` and `advance` do not exhaust the local battle budget;
- a 40-second event animation path and a 60-second bounded timeout path;
- server-error priority over all normal OCR/page handling;
- both EXP and Thread’s one-recovery success/failure/renewal-failure/second-exhaustion paths;
- RGB/HSV grey-choice recognition at beta, 720p, and 900p candidate spacing; grey first choice must choose the second slot, enabled first choice must retry the first slot;
- bounded failure when selection OCR is absent or its valid target does not advance;
- daily failure propagation through a single battle, group, wrapper, startup-resume path, and top-level task runner (including no completion toast/action);
- original `from tasks.event import event_handling` singleton behavior when import order changes.

## Code review checklist

- Is a new state recognized by a pure semantic parser when it is shared by battle and recovery flows?
- Are every click target and `None`/timeout outcome checked before side effects?
- Can a general loop budget preempt a documented longer animation wait?
- Does a new fallback run after server-error handling and after existing template matches?
- Did the implementation preserve group-level navigation rather than adding an unconditional per-battle return home?
