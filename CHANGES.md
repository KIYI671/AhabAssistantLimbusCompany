# 修改记录 — Ahab Assistant Limbus Company

## 2026-08-08 — 日常战斗事件状态机与恢复栅栏

### 背景与目标
- 日常连续场次不再每场回主界面后，纽本判定结果页可能残留；旧模板在 beta 截图上无法识别“继续”，下一场会错误地在事件页寻找纽本入口。
- 新增通用 OCR 事件页解析、事件结果动画等待、主页恢复和日常入口的一次性恢复，避免按单个事件文案堆叠模板补丁。

### 影响与兼容性
- 涉及战斗事件、返回主界面和经验本/纽本入口恢复；不新增依赖、不修改用户配置，也不取消“同项目连续场次不回主页、项目结束后统一换饼”的现有行为。
- `tasks.event.event_handling` 继续重导出事件解析接口，`from tasks.event import event_handling` 仍返回原有 `EventHandling` 单例。
- 可按本次 5 个提交分别回滚；不需要数据迁移。

### 文件与实现
| 操作 | 路径 | 说明 |
|---|---|---|
| 新增 | `tasks/event_page.py` | 无运行时 OCR/自动化依赖的纯 OCR 事件页解析器。 |
| 修改 | `tasks/event/event_handling.py` | 重导出解析接口，保留既有判定对象选择行为。 |
| 修改 | `tasks/battle/battle.py` | 模板推进失败时以 OCR 处理事件“继续/进行判定”，结果动画期间重置局部识别机会而不重置战斗总超时。 |
| 修改 | `tasks/base/back_init_menu.py` | 返回主页前推进或有界等待事件结果页；最长等待 60 秒。 |
| 修改 | `tasks/daily/luxcavation.py` | 经验本/纽本入口耗尽后最多执行一次统一主页恢复并完整重试；服务器错误重启后立即停止当前入口。 |
| 新增 | `tests/test_daily_event_recovery.py` | 覆盖 OCR 解析、战斗等待、主页恢复和入口恢复。 |
| 修改 | `tests/test_server_error_recovery.py` | 覆盖战斗、经验本和纽本对服务器错误“终止/跳过/继续”三态的优先处理。 |
| 新增 | `tests/test_event_import_compatibility.py` | 锁定事件包的原有单例导入契约。 |

### 验证
- `uv run pytest`：75 passed；覆盖事件结果“继续”、结果动画等待、60 秒上限、40 秒后按钮出现、主页恢复、入口一次恢复、服务器错误三态优先级和既有日常硬门。
- `uv run ruff check tasks/battle/battle.py tasks/event_page.py tasks/event/event_handling.py tasks/base/back_init_menu.py tasks/daily/luxcavation.py tasks/base/script_task_scheme.py tests --ignore E722`：通过；`E722` 为既有基线豁免。
- `git diff --check`：通过。

### 已知限制与后续
- 自动化测试已通过，但尚未完成真实游戏中的“纽本多场 + 判定事件”端到端回归；在该实机验证前，不能宣称问题已在 beta 游戏界面修复。
- 实机验收应保持已知配置：`select_team_by_order: true`、`daily_task: true`、`set_EXP_count: 1`、`set_thread_count: 3`、`daily_teams: 1`；观察首选项不可用后的判定、约 40 秒结果动画、OCR 点击继续和下一场正常进入纽本。
