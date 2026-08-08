# Journal - galact (Part 1)

> AI development session journal
> Started: 2026-08-08

---

## 2026-08-08 — 日常副本实机回归与待续全量审计

### 当前 Git 状态

- 分支：`fix/daily-team-selection-guard`
- 当前提交：`d04762e fix: recover daily retry and settlements`
- 相对本地 `main` 的提交序列：
  - `d3971a2 docs: specify daily batch navigation`
  - `aeb5da9 docs: plan daily batch navigation`
  - `29080ea fix: guard daily team selection failures`
  - `ba3814b docs: refine daily group navigation`
  - `97741f1 fix: group daily navigation between runs`
  - `f749583 fix: initialize daily tasks from home`
  - `904e9b7 docs: specify daily retry and settlement recovery`
  - `d04762e fix: recover daily retry and settlements`
- 工作区仅有未跟踪的本地代理配置：`.gitattributes`、`.pi/`、`.trellis/`；业务代码工作区干净。
- 未推送、未创建 PR、未合并到本地 `main`。

### 已实现并验证的修复

1. 编队后的服务器错误弹窗会在 `Battle.to_battle()` 中优先处理，不再持续点击被遮罩的“开始战斗”。
2. `重试4` / `重试2` 等游戏自身倒计时会等待，当前不会点击、关闭或重启；普通不可用重试须连续等待 15 秒才会关闭并重启。
3. “预设 #1”不再被当作“编队 #1”；按名称选队失败、进入副本失败时不会继续点“开始战斗”。
4. 日常开始时保留“回主界面 → 换饼”初始化；经验/纽本同一项目的连续场次之间不回主页，项目结束后回主页并换饼一次。
5. 普通日常的“战斗胜利 + 确认”结算页改由 OCR 识别并点击确认，避免镜牢统计模板误判抢占。
6. 自动化验证在 `d04762e` 完成时为：`38 passed`；相关 ruff 范围检查通过（`E722` 为既有基线，命令使用 `--ignore E722`）。

### 本轮实机发现的未解决问题（不要逐个临时补丁）

用户要求停止“发现一个界面、补一个模板”的方式，改为一次状态机级全量审计后统一修复。当前不要继续改代码，先按下述审计计划建立完整可复现状态集和修复设计。

#### 证据与真实表现

- 用户截图：`C:\Users\g1582\Desktop\1786195595062.png`
  - 纽本异常/判定事件中，第一步“献上土偶”不可用后需要改选“献上罪人”；短暂等待后可进入判定。
- 当前日志：`logs/debugLog.log`，约 `21:26:05` 至 `21:26:21`
  - OCR 已识别判定事件及结果：`判定成功`、`继续`；例如 21:26:20 OCR 完整有 `判定成功` 与 `继续`。
  - 事件结果页未被处理，随后 `thread_luxcavation()` 仍在该事件页寻找纽本入口，30 轮后在 21:26:08 报“无法进入纽本”；之后 `back_init_menu()` 也无法从该事件页离开。
  - 现有 `event/continue_assets.png`、`proceed_assets.png`、`commence_assets.png` 等模板在 beta 截图上的相似度不足阈值，故没有点击“继续”。
- 1.5.1 对照日志：`D:\BaiduNetdiskDownload\AALC_V1.5.1\AALC\logs\debugLog.log.10`，约 20831 行。
  - 同类事件“OCR: 似乎只能献上罪人，代替土偶了。”会正确走判定；其“进行判定”/后续按钮模板匹配可达 `0.99` 并点击。
  - 不能仅凭此推断 beta 模板仍适用；必须对实际 beta 截图重建状态出口的可靠识别。

#### 暂定根因（尚未确认实现方案）

日常连续执行改变了原先每场后的回主界面行为，因此把纽本中潜在的事件结果页暴露为“下一次入口寻找”的前置状态。`Battle.fight()` 只尝试模板点击事件按钮；失败后没有 OCR 兜底处理结果页“继续”，且 `onetime_thread_process()` / `Daily_task_wrapper()` 未把 `battle.fight()` 的成功/失败状态作为后续导航的强约束。当前 `back_init_menu()` 也未覆盖该日常事件页。

### 下一会话必须做的事（先审计、后实现）

1. 不要直接添加“土偶/罪人”专用补丁。创建 Trellis 任务并完成 PRD、设计、实施计划，范围为“日常战斗状态机审计与统一恢复”。
2. 读取并对照：
   - `tasks/battle/battle.py::Battle.fight()`（尤其 441–554 行的事件、结算、retry 路径）
   - `tasks/event/event_handling.py`
   - `tasks/daily/luxcavation.py`
   - `tasks/base/script_task_scheme.py`
   - `tasks/base/back_init_menu.py`
   - 1.5.1 同模块或上述日志证据。
3. 建立可自动运行的状态回归表/测试：至少覆盖
   - 采光入口、编队、开始战斗；
   - 服务器错误：倒计时、可重试、长期不可用；
   - 日常事件：选项（第一个禁用）、罪人判定、判定结果“继续”；
   - 战斗胜利确认；
   - 副本入口失败、战斗失败、回主页恢复。
4. 为每个状态定义明确的“识别条件、动作、成功后的下一状态、超时/失败出口”，并确保未知页面不会被错误当作“继续寻找纽本入口”。
5. 在统一实现前先让新增测试红灯；实现后跑全量 pytest、ruff 范围检查，并进行至少一次“纽本多场 + 事件”的实机端到端回归。该实机验证完成前，不要称问题已修好。
6. 处理完成后更新 `.trellis/spec/` 与 `CHANGES.md`（这是跨模块、用户明确要求减少回归的任务），并提交到当前分支；再由用户决定合并/PR。

### 操作提醒

- GUI/游戏可能仍在运行；下一会话先通过 PowerShell 按 `AhabAssistantLimbusCompany.*main.py` 精确确认进程，不要误杀 Steam 或其他 Python。
- 当前配置此前为：`select_team_by_order: true`、`daily_task: true`、`set_EXP_count: 1`、`set_thread_count: 3`、`daily_teams: 1`。开始实机验证前应让用户确认仍要使用这些配置。
- 本项目在 Windows/Git Bash 环境中；`read/write/edit` 使用 Windows 原生路径。

---

## 2026-08-08 — 日常战斗事件状态机实现（自动化验证完成，实机待验收）

### 已提交实现

- `dfa98f4 feat: parse daily event pages from OCR`
  - 新增无 RapidOCR/自动化运行时依赖的 `tasks/event_page.py`：`resolve_event_page()` 以 OCR 条目返回 `advance` / `wait` / `None`；`tasks.event.event_handling` 保持兼容重导出，且 `from tasks.event import event_handling` 的单例 API 通过两种导入顺序回归。
- `ae99681 fix: wait for daily event result actions`
  - `Battle.fight()` 保持模板优先；四类模板推进均未命中后才使用 OCR。事件结果动画和推进都会重置局部 `chance`，不会修改战斗总超时 `start_time`。
- `c6481d9 fix: recover daily event pages before returning home`
  - `back_init_menu()` 会先消费事件推进；结果页最多基于 `monotonic()` 等待 60 秒，等待期间维持通用循环预算，避免约 30 秒时提前退出；服务器错误 `retry()` 仍优先。
- `65d2248 fix: recover daily navigation before next entry`
  - EXP/纽本入口耗尽时共享 `_recover_daily_entry()`，最多回主页恢复一次后完整重试；恢复失败或第二次耗尽都返回 `False`，不允许后续选队/开战。
- `5f1320e fix: stop daily navigation after server recovery`
  - `Battle.fight()` 先保留彩色帧并处理服务器错误；战斗、EXP 和纽本入口统一遵守：`False`（已关闭并重启）立即终止、`True` 跳过本轮、`None` 才继续普通识图。

### 自动化证据

- `uv run pytest`：**75 passed**（服务器错误三态回归补齐后复跑）。
- `uv run ruff check tasks/battle/battle.py tasks/event_page.py tasks/event/event_handling.py tasks/base/back_init_menu.py tasks/daily/luxcavation.py tasks/base/script_task_scheme.py tests --ignore E722`：通过；`E722` 为既有基线豁免。
- `git diff --check`：通过。
- 已更新 `.trellis/spec/backend/` 与根目录 `CHANGES.md`；实机验收前不应将问题标记为已修复。

### 实机验收待用户执行

请先确认配置仍为：`select_team_by_order: true`、`daily_task: true`、`set_EXP_count: 1`、`set_thread_count: 3`、`daily_teams: 1`。

测试“纽本多场 + 包含判定事件”：首选项不可用时改选其他候选项、进入判定、等待约 40 秒结果动画、OCR 点击“继续”、下一场仍能正常进入纽本，且同项目场次之间不额外回主页、项目结束才统一回主页/换饼。若失败，保存脱敏截图、OCR 条目和 `logs/debugLog.log` 的时间段，扩展共享状态解析而非新增单事件模板。
