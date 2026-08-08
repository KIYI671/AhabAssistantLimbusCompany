# 编队后服务器错误弹窗恢复 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在编队完成后的开始战斗循环中优先处理“服务器发生错误”弹窗，避免被遮罩的开始战斗按钮被无限点击。

**Architecture:** `Battle.to_battle()` 复用 `tasks.base.retry.handle_server_error_dialog()`，不重复实现 OCR、按钮坐标或 HSV 颜色判断。每轮先保留彩色截图，再在任何普通模板识别前处理服务器错误：可重试时跳过本轮；已置灰并重启时返回失败给调用方。

**Tech Stack:** Python 3.12、pytest、pytest monkeypatch、RapidOCR、Pillow/NumPy、现有 Automation 接口。

## Global Constraints

- 仅修改编队后 `Battle.to_battle()` 的服务器错误拦截路径；不调整经验本、纽本入口、选队或启动页逻辑。
- 复用 `handle_server_error_dialog() -> bool | None`，不在战斗模块复制 OCR 或 HSV 判断。
- 所有生产代码改动前必须先新增并运行失败的回归测试。
- 截图使用 `auto.take_screenshot_with_color()`，以保证处理器可读取 `auto.color_screenshot`。
- `True` 表示弹窗已拦截并继续等待；`False` 表示已关闭弹窗并触发重启，当前流程必须返回 `False`；`None` 才继续原流程。
- 不新增依赖；保持项目 ruff 规则（120 列、E/F/I/T201）。

---

## 文件职责

| 文件 | 修改目的 |
| --- | --- |
| `tests/test_server_error_recovery.py` | 覆盖 `Battle.to_battle()` 在服务器错误弹窗出现时的控制流，证明普通“开始战斗”识图不会并行执行。 |
| `tasks/battle/battle.py` | 在开始战斗循环中刷新彩色帧并优先委托现有服务器错误处理器。 |

### Task 1: 为开始战斗循环建立服务器错误红灯回归测试

**Files:**
- Modify: `tests/test_server_error_recovery.py`
- Test: `tests/test_server_error_recovery.py::test_to_battle_skips_normal_detection_when_server_error_is_handled`
- Test: `tests/test_server_error_recovery.py::test_to_battle_returns_false_when_server_error_restarts_game`

**Interfaces:**
- Consumes: `tasks.battle.battle.Battle.to_battle() -> bool | None`。
- Consumes: `tasks.base.retry.handle_server_error_dialog() -> bool | None` 的既有三态约定。
- Produces: 两个回归测试，分别约束 `True` 与 `False` 分支的行为。

- [ ] **Step 1: 在测试文件中导入战斗模块，并加入最小替身**

在现有 `test_server_error_dialog_matches_the_user_reported_screenshot_layout` 测试后追加：

```python

def test_to_battle_skips_normal_detection_when_server_error_is_handled(monkeypatch) -> None:
    import tasks.battle.battle as battle_module

    class FakeBattleAuto:
        model = ""

        def __init__(self) -> None:
            self.screenshots = 0
            self.find_calls = 0

        def take_screenshot_with_color(self) -> object:
            self.screenshots += 1
            if self.screenshots == 2:
                raise StopIteration
            return object()

        def find_element(self, *_args, **_kwargs) -> None:
            self.find_calls += 1
            raise AssertionError("服务器错误处理期间不应执行开始战斗识图")

    fake_auto = FakeBattleAuto()
    monkeypatch.setattr(battle_module, "auto", fake_auto)
    monkeypatch.setattr(battle_module, "handle_server_error_dialog", lambda: True)

    with pytest.raises(StopIteration):
        battle_module.Battle.to_battle()

    assert fake_auto.find_calls == 0


def test_to_battle_returns_false_when_server_error_restarts_game(monkeypatch) -> None:
    import tasks.battle.battle as battle_module

    class FakeBattleAuto:
        model = ""

        def __init__(self) -> None:
            self.find_calls = 0

        def take_screenshot_with_color(self) -> object:
            return object()

        def find_element(self, *_args, **_kwargs) -> None:
            self.find_calls += 1
            raise AssertionError("重启游戏后不应执行开始战斗识图")

    fake_auto = FakeBattleAuto()
    monkeypatch.setattr(battle_module, "auto", fake_auto)
    monkeypatch.setattr(battle_module, "handle_server_error_dialog", lambda: False)

    assert battle_module.Battle.to_battle() is False
    assert fake_auto.find_calls == 0
```

- [ ] **Step 2: 运行新增测试并确认旧实现在错误位置失败**

Run:

```bash
.venv/Scripts/python.exe -m pytest tests/test_server_error_recovery.py::test_to_battle_skips_normal_detection_when_server_error_is_handled tests/test_server_error_recovery.py::test_to_battle_returns_false_when_server_error_restarts_game -q
```

Expected: FAIL。旧版 `Battle.to_battle()` 调用的是不存在于替身上的 `take_screenshot()`，失败信息包含 `AttributeError`；这证明测试准确要求将循环迁移到彩色截图并调用弹窗处理器。

- [ ] **Step 3: 不修改生产代码，确认失败原因仅来自目标行为缺失**

确认两个失败都来自 `Battle.to_battle()` 尚未调用 `take_screenshot_with_color()` / `handle_server_error_dialog()`，而不是导入、测试语法或环境问题。

- [ ] **Step 4: 记录红灯结果后进入最小实现任务**

不要为使测试通过而放宽替身断言、改为测试内部调用细节，或给替身添加 `take_screenshot()`；这些都会掩盖原始缺陷。

### Task 2: 在开始战斗循环优先处理服务器错误

**Files:**
- Modify: `tasks/battle/battle.py:17, 54-83`
- Test: `tests/test_server_error_recovery.py::test_to_battle_skips_normal_detection_when_server_error_is_handled`
- Test: `tests/test_server_error_recovery.py::test_to_battle_returns_false_when_server_error_restarts_game`

**Interfaces:**
- Consumes: `handle_server_error_dialog() -> bool | None`。
- Produces: `Battle.to_battle() -> False` 在处理器返回 `False` 时停止当前流程；否则保留原有 `None` 返回和普通开始战斗逻辑。

- [ ] **Step 1: 为现有 retry 导入增加服务器错误处理器**

将：

```python
from tasks.base.retry import retry
```

替换为：

```python
from tasks.base.retry import handle_server_error_dialog, retry
```

- [ ] **Step 2: 在 `Battle.to_battle()` 的普通识图前插入三态拦截**

将循环开头：

```python
while True:
    # 自动截图
    if auto.take_screenshot() is None:
        continue
    if click and (
```

替换为：

```python
while True:
    # 自动截图，并保留服务器错误弹窗颜色判定所需的彩色帧。
    if auto.take_screenshot_with_color() is None:
        continue
    server_error_result = handle_server_error_dialog()
    if server_error_result is False:
        return False
    if server_error_result is True:
        continue
    if click and (
```

不修改此片段之后的 `click` 状态机、阈值切换、重试计数或已有模板操作。

- [ ] **Step 3: 运行两个新增测试并确认绿灯**

Run:

```bash
.venv/Scripts/python.exe -m pytest tests/test_server_error_recovery.py::test_to_battle_skips_normal_detection_when_server_error_is_handled tests/test_server_error_recovery.py::test_to_battle_returns_false_when_server_error_restarts_game -q
```

Expected: `2 passed`。第一个测试证明已拦截弹窗时不会进入普通识图；第二个测试证明重启分支向调用方返回失败。

- [ ] **Step 4: 运行既有服务器错误恢复测试**

Run:

```bash
.venv/Scripts/python.exe -m pytest tests/test_server_error_recovery.py -q
```

Expected: `8 passed`。原有六项测试和新增两项均通过。

- [ ] **Step 5: 对变更运行格式与静态检查**

Run:

```bash
.venv/Scripts/python.exe -m ruff check tasks/battle/battle.py tests/test_server_error_recovery.py
.venv/Scripts/python.exe -m ruff format --check tasks/battle/battle.py tests/test_server_error_recovery.py
git diff --check
```

Expected: 三条命令均以零退出状态结束。

- [ ] **Step 6: 提交最小修复**

```bash
git add tasks/battle/battle.py tests/test_server_error_recovery.py
git commit -m "fix: recover server errors before battle starts"
```

### Task 3: 执行完整回归并核对需求

**Files:**
- Verify: `tasks/battle/battle.py`
- Verify: `tasks/base/retry.py`
- Verify: `tests/test_server_error_recovery.py`

**Interfaces:**
- Consumes: Task 2 提供的开始战斗三态拦截。
- Produces: 可交付的验证证据，明确所有范围内需求的结果。

- [ ] **Step 1: 运行全量测试套件**

Run:

```bash
.venv/Scripts/python.exe -m pytest -q
```

Expected: 所有收集到的测试通过，退出码为零。

- [ ] **Step 2: 使用用户截图重跑实际 OCR 与判定闭环**

Run:

```bash
.venv/Scripts/python.exe - <<'PY'
from pathlib import Path

import numpy as np
from PIL import Image

from module.ocr import ocr
from tasks.base.retry import find_server_error_dialog, is_retry_button_enabled

image = Image.open(Path(r"C:/Users/g1582/Desktop/1786128864915.png")).convert("RGB")
result = ocr.run(np.asarray(image.convert("L")))
entries = []
for text, points in zip(result.txts, result.boxes):
    box = np.asarray(points)
    entries.append((text, (int(box[:, 0].min()), int(box[:, 1].min()), int(box[:, 0].max()), int(box[:, 1].max()))))
dialog = find_server_error_dialog(entries)
assert dialog is not None
assert is_retry_button_enabled(np.asarray(image), dialog.retry_bounds)
print(f"dialog={dialog}; retry_enabled=True")
PY
```

Expected: 输出 `dialog=...; retry_enabled=True`，确认用户截图仍可由实际依赖识别，且重试按钮会走可重试分支。

- [ ] **Step 3: 检查最终差异仅限已批准范围**

Run:

```bash
git show --check --stat HEAD
git status --short
git diff HEAD~1..HEAD -- tasks/battle/battle.py tests/test_server_error_recovery.py
```

Expected: 仅存在 `Battle.to_battle()` 的彩色截图和三态弹窗拦截、以及对应两项回归测试；工作区无未提交变更。

- [ ] **Step 4: 交付验证结果**

报告根因、变更文件、针对性测试、全量 pytest、ruff 及截图 OCR 闭环的实际输出；明确说明尚未进行真人 Steam 游戏运行，需用户在经验本或纽本编队完成后观察弹窗出现时的五秒重试与置灰重启行为。
