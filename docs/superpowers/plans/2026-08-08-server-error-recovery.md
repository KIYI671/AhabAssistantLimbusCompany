# 服务器错误弹窗恢复 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在新版 Steam 中文服务器错误弹窗出现时，以 5 秒节流连续点击可用的“重试”，按钮置灰后关闭弹窗、重启游戏，并阻断任务层误点。

**Architecture:** 在 `Automation` 增加一次截取彩色帧但保持既有灰度匹配帧的接口；`tasks.base.retry` 从同一帧 OCR 结果构建纯数据的弹窗状态。`retry()` 在既有旧模板恢复前优先处理新弹窗：可用则节流重试，置灰则关闭并使用现有游戏重启入口退出当前任务循环。

**Tech Stack:** Python 3.12+、pytest、RapidOCR、Pillow、NumPy、现有 Win32/Automation 输入抽象。

## Global Constraints

- 仅支持本次用户确认的简体中文游戏界面；不改动英文旧模板恢复逻辑。
- 不新增依赖、不增加配置项、不使用固定分辨率坐标、不写入游戏或 Steam 数据。
- 服务器错误的可用“重试”最多每 5 秒点击一次，不设置点击次数上限。
- 重试置灰后只关闭一次并调用既有 `kill_game()`/`restart_game()`，然后返回 `False` 中止当前旧任务循环。
- 所有新增生产行为先有失败测试；测试不得操作真实窗口、鼠标、进程或 OCR 模型。
- 遵循 Ruff：120 列、E/F/I/T201 规则；所有文件 UTF-8。

---

## 文件结构

| 路径 | 职责 |
|---|---|
| `module/automation/automation.py` | 新增一帧彩色截图同时缓存灰度匹配图的接口，不改变现有 `take_screenshot()` 语义。 |
| `tasks/base/retry.py` | 定义服务器错误弹窗数据、OCR/按钮状态判定及 5 秒节流恢复入口，并在 `retry()` 的旧模板前调用。 |
| `tasks/daily/luxcavation.py` | 在经验本与纽本的每帧循环中优先调用恢复入口，阻断底部“开始游戏”误点。 |
| `tests/test_server_error_recovery.py` | 覆盖弹窗结构识别、金色/灰色判定、节流与关闭重启分支。 |

### Task 1: 为服务器错误恢复写失败测试

**Files:**
- Create: `tests/test_server_error_recovery.py`
- Modify: `tasks/base/retry.py`

**Interfaces:**
- Consumes: `tasks.base.retry` 中现有 `retry()`、`auto`、`kill_game()`、`restart_game()`。
- Produces: `ServerErrorDialog` 数据类型、`find_server_error_dialog(ocr_result)`、`is_retry_button_enabled(image, bounds)`、`handle_server_error_dialog(now: float | None = None) -> bool | None`。

- [ ] **Step 1: 写弹窗结构的失败测试**

```python
from tasks.base.retry import find_server_error_dialog


def _ocr_entry(text: str, box: tuple[int, int, int, int]) -> tuple[str, tuple[int, int, int, int]]:
    return text, box


def test_find_server_error_dialog_requires_message_and_ordered_buttons() -> None:
    dialog = find_server_error_dialog(
        [
            _ocr_entry("服务器发生错误。", (600, 300, 900, 340)),
            _ocr_entry("请稍后再试。", (650, 350, 850, 390)),
            _ocr_entry("关闭", (400, 600, 500, 650)),
            _ocr_entry("重试", (700, 600, 800, 650)),
        ]
    )

    assert dialog is not None
    assert dialog.close_position == (450, 625)
    assert dialog.retry_position == (750, 625)
    assert find_server_error_dialog([]) is None
    assert find_server_error_dialog(
        [
            _ocr_entry("服务器发生错误。", (600, 300, 900, 340)),
            _ocr_entry("请稍后再试。", (650, 350, 850, 390)),
            _ocr_entry("关闭", (700, 600, 800, 650)),
            _ocr_entry("重试", (400, 600, 500, 650)),
        ]
    ) is None
```

- [ ] **Step 2: 运行测试，确认因接口不存在而失败**

Run: `uv run pytest tests/test_server_error_recovery.py::test_find_server_error_dialog_requires_message_and_ordered_buttons -v`

Expected: FAIL，显示无法从 `tasks.base.retry` 导入 `find_server_error_dialog`。

- [ ] **Step 3: 写按钮可用性的失败测试**

```python
import numpy as np

from tasks.base.retry import is_retry_button_enabled


def test_is_retry_button_enabled_accepts_gold_text_and_rejects_gray_text() -> None:
    gold = np.zeros((20, 40, 3), dtype=np.uint8)
    gold[5:15, 10:30] = (236, 203, 163)
    gray = np.zeros((20, 40, 3), dtype=np.uint8)
    gray[5:15, 10:30] = (180, 180, 180)

    assert is_retry_button_enabled(gold, (0, 0, 40, 20)) is True
    assert is_retry_button_enabled(gray, (0, 0, 40, 20)) is False
```

- [ ] **Step 4: 运行测试，确认因接口不存在而失败**

Run: `uv run pytest tests/test_server_error_recovery.py::test_is_retry_button_enabled_accepts_gold_text_and_rejects_gray_text -v`

Expected: FAIL，显示无法导入 `is_retry_button_enabled`。

- [ ] **Step 5: 写恢复状态机的失败测试**

```python
from types import SimpleNamespace

import numpy as np

import tasks.base.retry as retry_module


class FakeAuto:
    def __init__(self, entries, image):
        self.entries = entries
        self.color_screenshot = image
        self.clicks = []

    def get_ocr_entries(self):
        return self.entries

    def mouse_click(self, x, y):
        self.clicks.append((x, y))


def test_handle_server_error_dialog_throttles_and_restarts_after_gray(monkeypatch) -> None:
    entries = [
        ("服务器发生错误。", (60, 10, 180, 30)),
        ("请稍后再试。", (70, 35, 170, 55)),
        ("关闭", (20, 80, 60, 100)),
        ("重试", (100, 80, 140, 100)),
    ]
    gold = np.zeros((120, 200, 3), dtype=np.uint8)
    gold[80:100, 100:140] = (236, 203, 163)
    fake_auto = FakeAuto(entries, gold)
    monkeypatch.setattr(retry_module, "auto", fake_auto)
    monkeypatch.setattr(retry_module, "_last_server_error_retry_time", 0.0)

    assert retry_module.handle_server_error_dialog(now=10.0) is True
    assert fake_auto.clicks == [(120, 90)]
    assert retry_module.handle_server_error_dialog(now=14.9) is True
    assert fake_auto.clicks == [(120, 90)]
    assert retry_module.handle_server_error_dialog(now=15.0) is True
    assert fake_auto.clicks == [(120, 90), (120, 90)]

    gray = np.zeros((120, 200, 3), dtype=np.uint8)
    gray[80:100, 100:140] = (180, 180, 180)
    fake_auto.color_screenshot = gray
    calls = []
    monkeypatch.setattr(retry_module, "kill_game", lambda: calls.append("kill"))
    monkeypatch.setattr(retry_module, "restart_game", lambda: calls.append("restart"))

    assert retry_module.handle_server_error_dialog(now=20.0) is False
    assert fake_auto.clicks[-1] == (40, 90)
    assert calls == ["kill", "restart"]
```

- [ ] **Step 6: 运行新增测试文件，确认失败原因仅为缺失的实现**

Run: `uv run pytest tests/test_server_error_recovery.py -v`

Expected: FAIL，失败集中于尚未定义的数据类型与三个接口；没有真实窗口/进程访问。

- [ ] **Step 7: 提交 RED 测试**

```bash
git add tests/test_server_error_recovery.py
git commit -m "test: cover server error recovery"
```

### Task 2: 实现彩色帧、弹窗判定与恢复状态机

**Files:**
- Modify: `module/automation/automation.py`
- Modify: `tasks/base/retry.py`
- Modify: `tasks/daily/luxcavation.py`
- Test: `tests/test_server_error_recovery.py`

**Interfaces:**
- Consumes: Task 1 的 `ServerErrorDialog`、`find_server_error_dialog`、`is_retry_button_enabled` 和 `handle_server_error_dialog` 测试约束。
- Produces: `Automation.take_screenshot_with_color() -> Image | None` 和 `Automation.get_ocr_entries() -> list[tuple[str, tuple[int, int, int, int]]]`；`retry()` 能返回 `False` 表示置灰后重启，或只在弹窗未处理时进入旧逻辑。

- [ ] **Step 1: 实现最小彩色截图接口**

在 `Automation` 中实现下列方法，复用现有截图间隔与超时策略：

```python
def take_screenshot_with_color(self) -> Image | None:
    """截取彩色帧，同时保留供模板匹配使用的灰度帧。"""
    result = ScreenShot.take_screenshot(False)
    if result is None:
        return None
    self.color_screenshot = result.convert("RGB")
    self.screenshot = self.color_screenshot.convert("L")
    self.last_screenshot_time = time.time()
    return self.screenshot
```

将方法的异常处理、截图间隔和 60 秒恢复逻辑抽取/复用自 `take_screenshot()`，确保错误处理语义不退化；初始化 `self.color_screenshot = None`。

- [ ] **Step 2: 实现一次 OCR 转换接口**

在 `Automation` 中实现下列方法，使用一次 `_run_ocr_for_text()` 所依赖的 `ocr.run(self.screenshot)` 等价输入，并保留每条文字的外接矩形：

```python
def get_ocr_entries(self) -> list[tuple[str, tuple[int, int, int, int]]]:
    """返回当前灰度帧中的 OCR 文本及其 (x1, y1, x2, y2) 外接矩形。"""
```

对于空 OCR 返回空列表。用 `box` 四角的最小/最大 x、y 规范化边界；不改变 `find_text_element()` 及其返回类型。

- [ ] **Step 3: 在 `retry.py` 实现纯数据与判定函数**

```python
@dataclass(frozen=True)
class ServerErrorDialog:
    close_position: tuple[int, int]
    close_bounds: tuple[int, int, int, int]
    retry_position: tuple[int, int]
    retry_bounds: tuple[int, int, int, int]


def _entry_with_text(entries, target: str) -> tuple[str, tuple[int, int, int, int]] | None:
    return next((entry for entry in entries if target in entry[0]), None)


def find_server_error_dialog(
    entries: list[tuple[str, tuple[int, int, int, int]]],
) -> ServerErrorDialog | None:
    error = _entry_with_text(entries, "服务器发生错误")
    later = _entry_with_text(entries, "请稍后再试")
    close = _entry_with_text(entries, "关闭")
    retry = _entry_with_text(entries, "重试")
    if not all((error, later, close, retry)):
        return None
    _, error_bounds = error
    _, later_bounds = later
    _, close_bounds = close
    _, retry_bounds = retry
    close_position = ((close_bounds[0] + close_bounds[2]) // 2, (close_bounds[1] + close_bounds[3]) // 2)
    retry_position = ((retry_bounds[0] + retry_bounds[2]) // 2, (retry_bounds[1] + retry_bounds[3]) // 2)
    if retry_position[0] <= close_position[0] or min(close_position[1], retry_position[1]) <= max(error_bounds[3], later_bounds[3]):
        return None
    return ServerErrorDialog(close_position, close_bounds, retry_position, retry_bounds)


def is_retry_button_enabled(image: np.ndarray, bounds: tuple[int, int, int, int]) -> bool:
    x1, y1, x2, y2 = bounds
    height, width = image.shape[:2]
    crop = image[max(0, y1 - 4):min(height, y2 + 4), max(0, x1 - 4):min(width, x2 + 4)]
    if crop.size == 0:
        return False
    hsv = cv2.cvtColor(crop, cv2.COLOR_RGB2HSV)
    gold_pixels = (hsv[:, :, 1] > 20) & (hsv[:, :, 2] > 100)
    return int(gold_pixels.sum()) >= 8
```

仅接受同时包含“服务器发生错误”“请稍后再试”“关闭”“重试”的条目；选择文本框中心，要求 `retry_center_x > close_center_x` 且两个按钮位于错误正文下方。将按钮文本框向四周扩 4 像素并裁剪至图片边界；将 RGB 转 HSV，统计明度大于 100 且饱和度大于 20 的像素数量。至少 8 个该类像素才认定金色可用；灰色像素则为不可用。

- [ ] **Step 4: 实现 `handle_server_error_dialog`**

```python
SERVER_ERROR_RETRY_INTERVAL = 5.0
_last_server_error_retry_time = 0.0


def handle_server_error_dialog(now: float | None = None) -> bool | None:
    """处理服务器错误：True 为已拦截重试，False 为关闭重启，None 为非目标弹窗。"""
```

流程：从 `auto.get_ocr_entries()` 构建弹窗；未命中返回 `None`；没有 `auto.color_screenshot` 时记录警告并返回 `True`，保持拦截而不误点；可用按钮且已过 5 秒时点击重试、更新时间并返回 `True`；5 秒内不点击仍返回 `True`；置灰时点击关闭、调用 `kill_game()`、调用 `restart_game()` 并返回 `False`。

- [ ] **Step 5: 将恢复分支接入 `retry()` 与纽本/经验本循环**

将 `retry()` 循环内原先的：

```python
if auto.take_screenshot() is None:
    continue
```

替换为先调用 `auto.take_screenshot_with_color()`；在 `connecting_assets.png` 与旧模板检测前调用：

```python
server_error_result = handle_server_error_dialog()
if server_error_result is False:
    return False
if server_error_result is True:
    continue
```

在 `tasks/daily/luxcavation.py` 的 `EXP_luxcavation()` 和 `thread_luxcavation()` 各自 `auto.take_screenshot()` 成功后、任何 `find_element()` 或 `click_element()` 前加入：

```python
server_error_result = handle_server_error_dialog()
if server_error_result is False:
    return
if server_error_result is True:
    continue
```

并将导入改为：

```python
from tasks.base.retry import handle_server_error_dialog
```

这样弹窗存在时，既不会执行旧模板，也不会落入经验本/纽本的普通开始按钮逻辑；只有关闭重启才返回当前任务循环。

- [ ] **Step 6: 运行定向测试，确认全部通过**

Run: `uv run pytest tests/test_server_error_recovery.py -v`

Expected: PASS，三类测试均通过；可用状态只在 5 秒间隔后点击，灰色状态关闭并重启。

- [ ] **Step 7: 运行原有全量测试和静态检查**

Run: `uv run pytest -q && uv run ruff check module/automation/automation.py tasks/base/retry.py tests/test_server_error_recovery.py`

Expected: pytest 全绿，Ruff 无输出且退出码为 0。

- [ ] **Step 8: 提交 GREEN 实现**

```bash
git add module/automation/automation.py tasks/base/retry.py tests/test_server_error_recovery.py
git commit -m "fix: recover from disabled server retry dialog"
```

### Task 3: 用用户截图进行离线回归验证

**Files:**
- Modify: `tests/test_server_error_recovery.py`
- Test: `tests/test_server_error_recovery.py`

**Interfaces:**
- Consumes: Task 2 的 `find_server_error_dialog()`、`is_retry_button_enabled()`。
- Produces: 对用户提供截图的结构识别回归保障；不将用户桌面路径、截图或个人数据提交到仓库。

- [ ] **Step 1: 写基于内嵌合成 OCR 条目的回归测试**

在测试中建立与 `C:\Users\g1582\Desktop\1786128864915.png` 已验证 OCR 坐标等价的条目，并断言：

```python
entries = [
    ("服务器发生错误。", (275, 143, 456, 168)),
    ("请稍后再试。", (300, 177, 433, 204)),
    ("关闭", (218, 323, 275, 356)),
    ("重试", (469, 324, 527, 356)),
]
dialog = find_server_error_dialog(entries)
assert dialog is not None
assert dialog.close_position == (246, 339)
assert dialog.retry_position == (498, 340)
```

- [ ] **Step 2: 运行该测试并确认通过**

Run: `uv run pytest tests/test_server_error_recovery.py -v`

Expected: PASS；测试不读取用户桌面路径，不把截图加入 Git。

- [ ] **Step 3: 在本机离线验证用户截图**

Run:

```bash
uv run python - <<'PY'
from pathlib import Path
from PIL import Image
from module.automation import auto
from tasks.base.retry import find_server_error_dialog

image_path = Path(r"C:\Users\g1582\Desktop\1786128864915.png")
auto.screenshot = Image.open(image_path).convert("L")
dialog = find_server_error_dialog(auto.get_ocr_entries())
assert dialog is not None
assert dialog.close_position == (246, 339)
assert dialog.retry_position == (498, 340)
print(dialog)
PY
```

Expected: 输出包含关闭与重试中心坐标的 `ServerErrorDialog`；不保存或提交该截图。

- [ ] **Step 4: 最终验证**

Run: `uv run pytest -q && uv run ruff check module/automation/automation.py tasks/base/retry.py tests/test_server_error_recovery.py && git diff --check`

Expected: 所有 pytest 通过、Ruff 无错误、diff 检查无空白错误。

- [ ] **Step 5: 提交回归测试**

```bash
git add tests/test_server_error_recovery.py
git commit -m "test: add server error dialog regression"
```
