# Logging Guidelines

> Logging conventions for the Python automation layer.

## Overview

Logs must describe state transitions and recovery decisions without dumping frames, full OCR payloads, account data, or other irrelevant screen content. Automation is timing-sensitive: a log should tell a maintainer whether the system recognized a state, intentionally waited, recovered, or abandoned the current action.

## Event and recovery levels

| Level | Use | Example |
| --- | --- | --- |
| `debug` | Expected, repeatable recognition or waiting within a bounded normal path. | `OCR推进日常事件页: continue`; `事件结果页等待推进按钮出现` |
| `info` | User-relevant but non-failing state changes already handled by an existing subsystem. | Server-error countdown or an enabled retry click. |
| `warning` | A safe fallback, degraded recognition, recovery attempt, or timeout about to invoke recovery. | Missing action coordinate; entry recognition exhausted and returning home once. |
| `error` | Recovery has no remaining exit and the current action is cancelled. | Entry recovery already consumed; cannot enter EXP/Thread. |

## Required transition evidence

For event recovery code, record the semantic reason rather than raw OCR text:

```python
log.debug(f"OCR推进日常事件页: {resolution.reason}")
log.debug("事件结果页等待推进按钮出现")
log.warning(f"{log_prefix}入口识别耗尽，尝试返回主界面后重新导航")
```

A message must make it possible to distinguish the following outcomes:

1. event action clicked;
2. event result intentionally waiting for its animation;
3. one allowed recovery invoked;
4. recovery budget exhausted and current action stopped.

## Do not log

- Screenshot pixels, screenshots, or the full OCR result list.
- Account identifiers, user configuration dumps, access tokens, or external service credentials.
- A warning or error for every normal animation polling iteration; use bounded `debug` messages instead.

## Review checklist

- Are routine template/OCR matches logged at `debug` rather than `warning` or `error`?
- Does every `warning` identify the fallback or bound that changed behavior?
- Does every terminal `False` have an `error` path at its owning recovery boundary?
- Can logs distinguish an event timeout from an ordinary missing daily entry?
