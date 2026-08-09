# 退出后 Steam 云同步导致无法启动

## Goal

在 AALC 因任务完成后的操作、异常恢复或用户操作而关闭《边狱巴士》后，下一次启动不能因 Steam 云同步确认弹窗而无限重试、卡住或反复唤起 Steam；应以可诊断、可恢复的方式处理“游戏进程存在但窗口尚不可用”和“Steam 等待用户确认”两类状态。

## Background

用户截图显示 Steam 弹窗“无法同步”：Steam 未能将存档与 Steam 云同步，提供“仍然进行游戏”和“取消”。用户明确要求适配无人值守挂机：识别到该精确弹窗时，AALC 自动点击“仍然进行游戏”，而非等待人工干预。

日志 `logs/debugLog.log` 的 2026-08-09 13:28:46 起记录了同一故障链：

1. `module/game_and_screen/game.py:52` 判定配置的游戏路径 `C:\Program Files (x86)\Steam\steamapps\common\Limbus Company\LimbusCompany.exe` 不存在；
2. `game.py:58` 因而反复调用 `steam://rungameid/1973530`；
3. 窗口枚举始终能看到无标题 `UnityWndClass`，但 `screen.init_handle()` 无法取得名为 `LimbusCompany` 的窗口；
4. `screen.py:314-332` 每轮都会重新调用启动逻辑，外层 `script_task_scheme.py:184-186` 又无限循环，因此每约 15 或 35 秒再次触发 Steam，直至人工干预。

对比上游 `KIYI671/AhabAssistantLimbusCompany` 的 `module/game_and_screen/game.py` 与 `tasks/base/script_task_scheme.py`：相关 Steam URL 启动、路径回退以及无限等待逻辑与当前版本相同。故不能将本次故障归因为日常战斗状态机分支；它是上游已有的启动恢复缺陷，加上当前配置中已失效的游戏路径和 Steam 云同步弹窗而被稳定触发。

## Confirmed Facts

- 当前配置的 `game_path` 不存在，导致 AALC 无法直接启动正确的本地可执行文件。
- 用户已明确授权：Steam 的“无法同步”弹窗出现时，AALC 自动点击“仍然进行游戏”，满足夜间无人值守挂机。
- 当前启动恢复把“进程存在但窗口未完成启动 / 被 Steam 弹窗阻断”与“游戏未启动”等同，形成重复 Steam 调用循环。
- `retry.py`、`back_init_menu.py` 等多条恢复路径会调用 `kill_game()` / `restart_game()`，因此修复需要覆盖公共启动恢复边界，而不能只修 `script_task_scheme.init_game()`。

## Requirements

### R1 启动状态区分与有限等待

公共启动逻辑必须区分：游戏进程仍在退出、Steam 已被调用且等待游戏窗口、游戏窗口可用、启动超时。等待中的状态不得重复触发 Steam URL，不得无限循环。

### R2 Steam 云同步无人值守恢复

当 Steam 云同步确认阻止游戏窗口出现时，AALC 必须仅在精确识别“无法同步”正文及“仍然进行游戏”按钮的前提下，自动点击该按钮并等待游戏窗口出现。不得基于坐标盲点，不得点击“取消”或任何其他 Steam 对话框。若自动点击后仍无法启动，则结束本轮恢复并记录可诊断日志，不得无限重试。

### R3 失效路径的可诊断与回退

当配置的游戏路径不存在时，日志必须指出该路径失效以及修复配置的方式。若安全地可用本地启动路径，优先使用它；Steam URL 只能作为受节流保护的回退，不能构成循环唤起。

### R4 退出后的重新启动稳定性

由 `kill_game()`、`restart_game()`、任务结束后的操作所引出的下一次启动，必须复用同一套状态与超时约束。关闭时优先走正常退出并等待进程结束及 Steam 同步窗口期；只有正常退出超时才强制结束，避免不必要地制造云同步冲突。

### R5 自动化回归

新增 pytest 回归测试，至少覆盖：

- 游戏进程存在但窗口未就绪时不重复启动；
- Steam 已请求启动但窗口未出现时按有限次数/超时退出；
- 失效本地路径时的诊断与回退节流；
- 精确匹配云同步弹窗后只自动点击“仍然进行游戏”，不匹配或缺少目标按钮时不点击；
- 既有直接路径启动与已存在可用游戏进程不回归。

## Out of Scope

- 不自动点击“取消”，不修改、删除或覆盖 Steam 云存档。
- 不处理除“无法同步 → 仍然进行游戏”以外的 Steam 客户端 UI。
- 不处理 Steam 或 Project Moon 服务端导致的实际云同步失败。
- 不在本任务中改动日常战斗/事件状态机。

## Acceptance Criteria

- [x] Steam 云同步弹窗阻断启动时，AALC 只在精确匹配后自动点击“仍然进行游戏”；不匹配时不点击任何 Steam 控件，也不反复调用 Steam URL 或无限等待。
- [x] 失效游戏路径被一次性明确诊断，且不会让启动恢复进入高频循环。
- [x] 游戏已在启动/退出过渡阶段时，公共启动逻辑不重复发起 Steam 启动。
- [x] 所有启动入口（首次任务、超时恢复、`restart_game()`）采用同一套有限等待/失败语义。
- [x] 新增回归测试先红后绿，并且全量 pytest、Ruff 检查通过。

## Decision

用户授权无人值守处理：检测到精确的 Steam“无法同步”弹窗时，自动点击“仍然进行游戏”。此授权不扩展到“取消”或其他 Steam 弹窗。

## Verification Evidence

- `uv run pytest`：128 passed（2026-08-09）。
- `uv run ruff check module/game_and_screen/steam_cloud.py module/game_and_screen/game.py module/game_and_screen/screen.py module/automation/automation.py module/automation/screenshot.py tasks/base/retry.py tasks/base/script_task_scheme.py module/system_actions.py tests/test_steam_cloud_recovery.py tests/test_server_error_recovery.py tests/test_daily_team_selection.py --ignore E722`：通过。
- `python -m compileall module/game_and_screen module/automation tasks/base module/system_actions.py`：通过。
- `git diff --check`：通过。
- 尚待用户实机验证 Steam 云同步弹窗出现时的自动点击与后续游戏窗口就绪；该限制不影响已验证的单元/集成回归结果。
