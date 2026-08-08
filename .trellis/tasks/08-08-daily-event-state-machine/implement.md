# 日常战斗事件状态机审计与统一恢复：实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在不取消日常连续场次优化的前提下，用可单测的 OCR 事件页状态解析和有界入口恢复，阻止纽本判定结果残页被误当成下一场采光入口。

**Architecture:** `tasks.event.event_handling` 持有无副作用的 OCR 状态解析契约；`Battle.fight()`、`back_init_menu()` 都消费该契约，但分别保留自己的循环与超时策略。`luxcavation` 在入口搜索耗尽时只进行一次统一恢复重试，调用方仍以布尔结果阻止后续选队和开战。

**Tech Stack:** Python 3.12、pytest、Ruff、RapidOCR（经现有 `Automation.get_ocr_entries()`）、OpenCV/模板识别（仅复用，未新增依赖）。

## 全局约束

- 不新增第三方依赖；保持现有中文游戏路径，不扩展多语言和模拟器兼容范围。
- 模板识别仍优先；OCR 仅作为 beta 事件推进按钮的兜底，不能按“土偶”“罪人”等具体事件文案硬编码。
- 纯 OCR 解析不得截图、睡眠、点击、读取 `cfg` 或改全局变量；输入/输出固定为 OCR 条目和不可变数据对象。
- 不重置 `Battle.fight()` 的总战斗超时 `start_time`；事件动画只能重置局部 `chance`。
- 日常入口恢复最多一次，不能在循环中无限重置 `loop_count`；恢复最终失败时必须返回 `False`，且不得进入选队或开战。
- 服务器错误拦截优先于普通识图和事件处理；沿用 `handle_server_error_dialog()` 的 `True`（已处理）/`False`（已重启）/`None`（无弹窗）语义。
- 日志中：事件等待用 `debug`，恢复/取消本场用 `warning` 或 `error`；不记录截图、账户信息或无关 OCR 全文。
- 不改变“同一日常项目连续场次不回主页，项目结束后主页 + 换饼一次”的现有行为。
- 执行前载入 `.trellis/spec/backend/{index,error-handling,logging-guidelines,quality-guidelines}.md` 以及 `.trellis/spec/guides/code-reuse-thinking-guide.md`；其中项目 spec 仍有占位内容时，实际代码与本计划优先遵循已验证的同目录模式。

---

## 文件职责地图

| 文件 | 改动职责 |
| --- | --- |
| `tasks/event/event_handling.py` | 定义 `EventPageResolution` 与纯函数 `resolve_event_page()`，保持现有判定对象选择逻辑不变。 |
| `tasks/battle/battle.py` | 在已有模板事件路径未推进时应用 OCR 解析结果；推进/等待均重置局部 chance。 |
| `tasks/base/back_init_menu.py` | 返回主页过程中先消费 OCR 事件推进/等待状态，并为等待设置有界时钟。 |
| `tasks/daily/luxcavation.py` | 入口搜索耗尽后只恢复并完整重试一次，第二次耗尽时返回 `False`。 |
| `tasks/base/script_task_scheme.py` | 仅在测试暴露失败传播问题时最小化调整；维持现有入口失败硬门和分组导航。 |
| `tests/test_daily_event_recovery.py` | 覆盖纯解析、战斗 OCR 回退、主页恢复、入口恢复与失败硬门。 |
| `tests/test_daily_team_selection.py` | 在既有连续导航断言旁补充“恢复失败后不选队/不开战”的集成断言（若独立新测试无法复用既有夹具）。 |
| `CHANGES.md` | 全部自动化和实机验收完成后，记录面向用户的行为变更、限制与实机验证状态。 |

## 公共接口契约

任务 1 产出以下接口；后续任务只能依赖这些名称和含义：

```python
# tasks/event/event_handling.py
from dataclasses import dataclass
from typing import Literal

OcrBounds = tuple[int, int, int, int]
OcrEntry = tuple[str, OcrBounds]

@dataclass(frozen=True)
class EventPageResolution:
    state: Literal["advance", "wait"]
    position: tuple[int, int] | None
    reason: str


def resolve_event_page(entries: list[OcrEntry]) -> EventPageResolution | None:
    """仅从 OCR 条目判定事件推进、等待或非事件页。"""
```

- `advance` 的 `position` 必须非空且为目标文本框中心；`reason` 为稳定、可记录的事件原因（例如 `continue`、`perform_check`）。
- `wait` 的 `position` 必须为 `None`；只表示已识别到判定结果但按钮尚未出现。
- `None` 表示信息不足或非事件页，调用方必须走原有逻辑，不能点击任意“继续”。

## Task 1：建立纯 OCR 事件状态解析（Red → Green）

**Files:**
- Modify: `tasks/event/event_handling.py:1-20`
- Create: `tests/test_daily_event_recovery.py`

**Consumes:** `Automation.get_ocr_entries()` 输出的 `(text, (x1, y1, x2, y2))` 元组格式。

**Produces:** `EventPageResolution`、`resolve_event_page(entries)`；Task 2 和 Task 3 使用。

- [ ] **Step 1：写解析器的失败测试。**

  在 `tests/test_daily_event_recovery.py` 创建 OCR 条目工厂，并准确断言下列行为：

  ```python
  from tasks.event.event_handling import resolve_event_page

  def entry(text: str, bounds: tuple[int, int, int, int]):
      return text, bounds

  def test_resolve_event_page_advances_from_result_continue() -> None:
      result = resolve_event_page([
          entry("判定成功", (500, 200, 700, 240)),
          entry("继续", (680, 800, 760, 840)),
      ])
      assert result is not None
      assert result.state == "advance"
      assert result.position == (720, 820)
      assert result.reason == "continue"

  def test_resolve_event_page_waits_for_result_animation() -> None:
      result = resolve_event_page([entry("判定失败", (500, 200, 700, 240))])
      assert result is not None
      assert result.state == "wait"
      assert result.position is None

  def test_resolve_event_page_advances_perform_check_only_in_event_context() -> None:
      result = resolve_event_page([
          entry("事件", (450, 100, 550, 140)),
          entry("进行判定", (680, 800, 840, 840)),
      ])
      assert result is not None
      assert result.state == "advance"
      assert result.position == (760, 820)
      assert result.reason == "perform_check"

  def test_resolve_event_page_ignores_normal_pages_and_ambiguous_continue() -> None:
      assert resolve_event_page([]) is None
      assert resolve_event_page([entry("继续", (680, 800, 760, 840))]) is None
      assert resolve_event_page([entry("战斗胜利", (500, 200, 700, 240))]) is None
  ```

  同时覆盖 OCR 把“判定成功”与“继续”分行或文本前后附带空白的情况，确保先选择事件上下文明确的“继续”，而不是输入顺序中的任意短文本。

- [ ] **Step 2：运行定向测试，确认当前缺少接口而失败。**

  Run: `pytest tests/test_daily_event_recovery.py -q`

  Expected: 因 `resolve_event_page` / `EventPageResolution` 尚不存在而收集或导入失败；不能通过先跳过测试来制造绿灯。

- [ ] **Step 3：以最小实现加入不可变解析结果和文本/坐标辅助函数。**

  在 `tasks/event/event_handling.py` 的导入与 `EventHandling` 类之前新增代码。实现需要：

  ```python
  @dataclass(frozen=True)
  class EventPageResolution:
      state: Literal["advance", "wait"]
      position: tuple[int, int] | None
      reason: str

  def _entry_center(bounds: OcrBounds) -> tuple[int, int]:
      return ((bounds[0] + bounds[2]) // 2, (bounds[1] + bounds[3]) // 2)
  ```

  `resolve_event_page()` 必须先将空白压缩/去除并检查结果语义（`判定成功`、`判定失败`）；有结果语义时找“继续”，找到则 `advance`，否则 `wait`。没有结果语义时，仅在存在事件上下文（最小集合：`事件`、`判定`、`选项`）时接受“进行判定”。不得从 `auto`、`cfg`、`time` 或模板资源读取任何内容。

- [ ] **Step 4：运行解析测试，确认转绿。**

  Run: `pytest tests/test_daily_event_recovery.py -q`

  Expected: 新增解析测试通过；此时尚未声明整个任务完成。

- [ ] **Step 5：审查解析器边界。**

  Run: `ruff check tasks/event/event_handling.py tests/test_daily_event_recovery.py --ignore E722`

  Expected: 退出码 0。确认“独立继续”返回 `None`，且 `wait` 没有按钮坐标。

- [ ] **Step 6：提交独立的解析器变更。**

  ```bash
  git add tasks/event/event_handling.py tests/test_daily_event_recovery.py
  git commit -m "feat: parse daily event pages from OCR"
  ```

## Task 2：让战斗循环消费 OCR 兜底而不耗尽 chance

**Files:**
- Modify: `tasks/battle/battle.py:11-25, 485-507`
- Modify: `tests/test_daily_event_recovery.py`

**Consumes:** Task 1 的 `resolve_event_page(entries)`。

**Produces:** 当模板未匹配的结果页出现时，`Battle.fight()` 点击 OCR “继续”或在动画页等待，且两种情况都回到下一轮并重置 `chance`。

- [ ] **Step 1：写战斗事件 OCR 回退的失败测试。**

  使用最小 fake auto 按顺序提供：首次截图、所有模板未命中、`get_ocr_entries()` 返回“判定成功 + 继续”、`mouse_click()` 记录坐标。通过 monkeypatch 让第二帧返回一个可被现有日常结算分支识别的“战斗胜利 + 确认”，使 `fight()` 自然退出；断言：

  ```python
  assert clicks == [(720, 820), (1400, 700)]
  assert retry_calls == []
  ```

  再写“仅判定成功”的序列：第一帧返回 `wait`，第二帧返回“判定成功 + 继续”，断言没有调用 `retry()`、没有走 `back_init_menu()`，并最终点击继续。测试中将 `sleep` monkeypatch 为无操作，避免等待。

- [ ] **Step 2：运行战斗回退测试，确认失败。**

  Run: `pytest tests/test_daily_event_recovery.py -q -k "fight"

  Expected: 当前实现不读 `get_ocr_entries()`，因此点击记录缺少 `(720, 820)` 或循环耗尽；不能修改 fake 的模板匹配让测试伪绿。

- [ ] **Step 3：在模板事件路径后接入解析器。**

  在 `Battle.fight()` 中现有 `choice_event_handling` 的四个模板点击（`continue/proceed/commence/skip`）全部未 `continue` 后、镜牢奖励卡检测前，加入：

  ```python
  if choice_event_handling:
      event_resolution = resolve_event_page(auto.get_ocr_entries())
      if event_resolution is not None:
          if event_resolution.state == "advance":
              auto.mouse_click(*event_resolution.position)
              log.debug(f"OCR 推进日常事件页: {event_resolution.reason}")
          else:
              log.debug("事件判定结果动画中，等待推进按钮出现")
          chance = self.INIT_CHANCE
          sleep(waiting)
          continue
  ```

  导入解析函数，不复制 Task 1 的关键词判断。保留模板优先级、`EventHandling.decision_event_handling()`、现有结算 OCR 和 `retry()` 分支的顺序。`event_resolution.position` 在 `advance` 时由接口契约保证非空；为防御损坏输入，若为空则只记录 warning 并按 `wait` 处理，不能解包 `None`。

- [ ] **Step 4：运行战斗回退与旧结算回归。**

  Run: `pytest tests/test_daily_event_recovery.py tests/test_battle_settlement.py -q`

  Expected: 新的 `fight` 路径点击 OCR “继续”；等待路径不提前失败；既有日常结算确认仍通过。

- [ ] **Step 5：运行局部静态检查并检查 chance 不变量。**

  Run: `ruff check tasks/battle/battle.py tasks/event/event_handling.py tests/test_daily_event_recovery.py --ignore E722`

  Expected: 退出码 0。人工复核：只赋值 `chance = self.INIT_CHANCE`，没有在 OCR 事件路径改写 `start_time`。

- [ ] **Step 6：提交战斗循环接入。**

  ```bash
  git add tasks/battle/battle.py tests/test_daily_event_recovery.py
  git commit -m "fix: wait for daily event result actions"
  ```

## Task 3：把事件残页纳入主页恢复

**Files:**
- Modify: `tasks/base/back_init_menu.py:1-90`
- Modify: `tests/test_daily_event_recovery.py`

**Consumes:** Task 1 的解析器；现有 `allow_restart`、`LOOP_COUNT`、`LOADING_TIMEOUT` 策略。

**Produces:** 返回主页时先推进/等待可识别事件页，等待上限耗尽后遵循既有允许/禁用重启语义。

- [ ] **Step 1：写主页恢复的失败测试。**

  创建 FakeAuto，第一帧 `get_ocr_entries()` 返回“判定成功 + 继续”，断言 `back_init_menu(allow_restart=False)` 点击 `(720, 820)` 后再识别主页模板并返回 `True`。另建只返回“判定成功”的 fake，monkeypatch 单调时钟越过新事件等待上限，断言函数返回 `False`、不调用 `kill_game` 或 `restart_game`。

- [ ] **Step 2：运行主页恢复测试，确认当前失败。**

  Run: `pytest tests/test_daily_event_recovery.py -q -k "back_init_menu"`

  Expected: 当前函数只会空白点击/ESC，未调用 OCR 解析器，故推进点击断言失败。

- [ ] **Step 3：加入有界事件恢复分支。**

  在 `tasks/base/back_init_menu.py` 定义显式常量（例如 `EVENT_PAGE_WAIT_TIMEOUT = 60`，实际值可依据实机 40 秒动画和总恢复预算调整）并维护 `event_wait_started_at: float | None`。在服务器重试之后、普通主页/返回键逻辑之前：

  ```python
  resolution = resolve_event_page(auto.get_ocr_entries())
  if resolution is not None:
      if resolution.state == "advance" and resolution.position is not None:
          auto.mouse_click(*resolution.position)
          event_wait_started_at = None
          continue
      if event_wait_started_at is None:
          event_wait_started_at = monotonic()
      if monotonic() - event_wait_started_at < EVENT_PAGE_WAIT_TIMEOUT:
          sleep(1)
          continue
      if not allow_restart:
          log.warning("事件结果页等待推进按钮超时，返回主页失败")
          return False
      # 将 loop_count 置为耗尽态，复用既有 kill/restart 分支。
      loop_count = 0
      continue
  event_wait_started_at = None
  ```

  若当前帧是 `None`，保持既有主页/剧情/战斗处理顺序。不得为事件结果页直接按 ESC 或空白点击；不得复制解析关键词。

- [ ] **Step 4：运行主页恢复和服务器错误回归。**

  Run: `pytest tests/test_daily_event_recovery.py tests/test_server_error_recovery.py -q`

  Expected: 事件推进/有界等待的测试通过；服务器错误处理期间依旧不执行普通识图。

- [ ] **Step 5：提交主页恢复。**

  ```bash
  git add tasks/base/back_init_menu.py tests/test_daily_event_recovery.py
  git commit -m "fix: recover daily event pages before returning home"
  ```

## Task 4：在采光入口设置一次恢复栅栏

**Files:**
- Modify: `tasks/daily/luxcavation.py:42-128, 130-328`
- Modify: `tests/test_daily_event_recovery.py`
- Modify (only if required by a failing test): `tasks/base/script_task_scheme.py:50-95`
- Modify (only if test reuse is clearer): `tests/test_daily_team_selection.py`

**Consumes:** `back_init_menu() -> bool` 和既有 `EXP_luxcavation()` / `thread_luxcavation()` 返回值。

**Produces:** 入口失败时进行一次主页恢复和重新导航；恢复失败或第二次入口耗尽时返回 `False`，调用方不选队不开战。

- [ ] **Step 1：写入口恢复的失败测试。**

  参数化经验本与纽本。FakeAuto 的第一轮始终不命中入口，令循环耗尽；将模块内 `back_init_menu` monkeypatch 为记录 `"recover"` 并返回 `True`；第二轮返回编队模板。断言各入口函数返回 `True` 且 `calls == ["recover"]`。再写恢复返回 `False` 的分支，断言函数返回 `False` 且恢复恰好调用一次。

  将 `onetime_EXP_process` / `onetime_thread_process` 的入口函数 monkeypatch 为 `False`，继续断言 `select_battle_team` 与 `battle.to_battle` 均未被调用，确保既有硬门没有被恢复逻辑绕过。

- [ ] **Step 2：运行入口恢复测试，确认失败。**

  Run: `pytest tests/test_daily_event_recovery.py tests/test_daily_team_selection.py -q -k "luxcavation or daily_process_stops"`

  Expected: 当前入口函数第一次耗尽即返回 `False`，不调用 `back_init_menu()`。

- [ ] **Step 3：抽取单一、可复用的有界入口循环包装。**

  避免复制经验本/纽本的恢复计数。新增私有辅助函数（位置可在 `luxcavation.py` 顶部）：

  ```python
  MAX_ENTRY_RECOVERY_ATTEMPTS = 1

  def _recover_daily_entry(recovery_attempts: int, log_prefix: str) -> bool:
      if recovery_attempts >= MAX_ENTRY_RECOVERY_ATTEMPTS:
          log.error(f"{log_prefix}入口恢复已耗尽，取消本场")
          return False
      from tasks.base.back_init_menu import back_init_menu
      log.warning(f"{log_prefix}入口识别耗尽，尝试返回主界面后重新导航")
      return back_init_menu()
  ```

  两个入口函数均维护 `recovery_attempts`：第一次 `loop_count < 0` 时调用该函数；成功则加一、重置 `loop_count = 30` 和 `auto.model = "clam"` 后继续；失败或第二次耗尽则保留对应的“无法进入经验本/纽本”错误并 `return False`。若测试采用模块级 monkeypatch，应在模块级导入 `back_init_menu` 或调整测试 patch 目标，二者只能选一个且不可对两个入口复制恢复代码。

- [ ] **Step 4：运行入口恢复、组导航及服务错误完整回归。**

  Run: `pytest tests/test_daily_event_recovery.py tests/test_daily_team_selection.py tests/test_server_error_recovery.py -q`

  Expected: 单次恢复后可进入编队；恢复失败后停止；连续场次仍不会在每场无条件回主页；服务器错误分支保持优先。

- [ ] **Step 5：提交入口恢复栅栏。**

  ```bash
  git add tasks/daily/luxcavation.py tasks/base/script_task_scheme.py tests/test_daily_event_recovery.py tests/test_daily_team_selection.py
  git commit -m "fix: recover daily navigation before next entry"
  ```

## Task 5：全范围验证、实机验收与交接记录

**Files:**
- Modify: `.trellis/spec/backend/*.md`（仅将本任务验证出的实际可执行约定写入对应已有文档）
- Modify: `CHANGES.md`
- Modify: `.trellis/workspace/galact/journal-1.md`

**Consumes:** Tasks 1–4 的实现、自动测试结果、用户提供的实机回归结果。

**Produces:** 可复现验证证据、规范更新、面向用户的变更记录；实机验证未完成时明确标注未完成而非宣称修复完成。

- [ ] **Step 1：运行全部测试。**

  Run: `pytest`

  Expected: 全部通过；记录 pass 数和任何既有 skip/警告。若失败，先按失败状态回到对应 Task 的 Red/Green 步骤，不在本步骤添加临时模板。

- [ ] **Step 2：运行范围 Ruff。**

  Run: `ruff check tasks/battle/battle.py tasks/event/event_handling.py tasks/base/back_init_menu.py tasks/daily/luxcavation.py tasks/base/script_task_scheme.py tests --ignore E722`

  Expected: 退出码 0；`E722` 仅为已知基线豁免，不得用它掩盖新增问题。

- [ ] **Step 3：进行代码复核。**

  Run:

  ```bash
  rg -n "resolve_event_page|MAX_ENTRY_RECOVERY_ATTEMPTS|EVENT_PAGE_WAIT_TIMEOUT|判定成功|判定失败" tasks tests
  git diff --check
  ```

  Expected: OCR 关键词只存在于 `event_handling.py`（测试除外）；两个日常入口共享同一恢复策略；没有空白行尾、冲突标记或重复的状态判断。

- [ ] **Step 4：请求用户执行实机端到端回归。**

  先请用户确认仍使用交接记录中的配置（`select_team_by_order: true`、`daily_task: true`、`set_EXP_count: 1`、`set_thread_count: 3`、`daily_teams: 1`），再执行“纽本多场 + 包含判定事件”。验收时记录：事件选项首项不可用、选择其他候选项、判定、约 40 秒结果动画、OCR 点击继续、后续一场成功进入纽本、项目结束仍只回主页/换饼一次。实机失败时收集脱敏 OCR 条目、日志时间段和截图，由解析器/状态表统一修正；不要增加单事件模板。

- [ ] **Step 5：更新规范、变更记录和 Journal。**

  自动和实机均通过后，更新 `.trellis/spec/backend/` 中与错误恢复、日志和质量相关的真实约定；更新 `CHANGES.md`，按用户可见行为说明 OCR 结果页推进、入口恢复边界及实机环境；在 Journal 追加命令输出、配置、实机结果与遗留风险。若实机尚未执行，只记录“自动验证通过、实机待用户验收”，不得标记任务完成。

- [ ] **Step 6：提交最终文档与规范。**

  ```bash
  git add .trellis/spec CHANGES.md .trellis/workspace/galact/journal-1.md
  git commit -m "docs: record daily event recovery behavior"
  ```

## 覆盖映射与回滚点

| PRD 要求 | 实施任务 | 验证 |
| --- | --- | --- |
| R1 状态机审计 | 设计第 2 节、Tasks 1–4 | 状态表 + 对应测试名 |
| R2 OCR 兜底与耐心 | Tasks 1–2 | 结果“继续”、仅结果等待、空/普通 OCR |
| R3 连续场次统一恢复 | Tasks 3–4 | 残留事件→主页→入口，恢复失败停止 |
| R4 自动化回归 | Tasks 1–5 | 定向 pytest、全量 pytest、Ruff |
| 实机“纽本多场 + 事件” | Task 5 | 用户实机验收记录 |

提交边界为：Task 1 纯解析、Task 2 战斗接入、Task 3 主页恢复、Task 4 入口恢复、Task 5 文档。任何回归可回滚到前一提交而不影响已经验证的相邻职责；不能通过回滚到“每场无条件回主页”来规避问题。