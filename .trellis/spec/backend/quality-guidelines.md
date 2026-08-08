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

## Forbidden patterns

- **Do not** reset a total task timeout just because a UI animation is being waited on; reset only the local recognition budget when the state is known.
- **Do not** add per-event text/template branches for a common event transition. Extend the shared parser and its state table instead.
- **Do not** duplicate EXP and Thread recovery budgets. Use one helper and one named maximum.
- **Do not** put a pure parser behind a package initializer that eagerly imports the OCR runtime; this makes unit tests depend on a game runtime unnecessarily.
- **Do not** treat a failed entry recovery as permission to proceed to team selection or battle start.

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
- both EXP and Thread’s one-recovery success/failure/second-exhaustion paths;
- original `from tasks.event import event_handling` singleton behavior when import order changes.

## Code review checklist

- Is a new state recognized by a pure semantic parser when it is shared by battle and recovery flows?
- Are every click target and `None`/timeout outcome checked before side effects?
- Can a general loop budget preempt a documented longer animation wait?
- Does a new fallback run after server-error handling and after existing template matches?
- Did the implementation preserve group-level navigation rather than adding an unconditional per-battle return home?
