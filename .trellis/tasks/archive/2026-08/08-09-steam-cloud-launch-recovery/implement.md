# Steam 云同步无人值守恢复实施计划

## 目标

用有界启动状态机替代 Steam 启动无限循环；精确识别 Steam“无法同步”弹窗后自动点击“仍然进行游戏”；并让所有 Windows 游戏退出路径优先正常退出，超时才强杀。

## 影响文件

| 文件 | 变更职责 |
| --- | --- |
| `module/game_and_screen/steam_cloud.py` | 新建：纯 OCR 弹窗识别与可注入的桌面截图/OCR/点击适配器。 |
| `module/game_and_screen/game.py` | 单次启动请求、云同步等待处理、优雅关闭与强杀兜底。 |
| `module/game_and_screen/screen.py` | 为启动轮询添加禁止隐式重新启动的路径。 |
| `tasks/base/script_task_scheme.py` | 将无限窗口等待改为总时限轮询和明确失败。 |
| `tasks/base/retry.py` | 让 `kill_game()` 兼容入口委托公共关闭逻辑。 |
| `module/system_actions.py` | 结束后“退出游戏”委托公共关闭逻辑。 |
| `tests/test_steam_cloud_recovery.py` | 新建：纯识别、I/O 适配、启动状态、关闭语义及调用链回归。 |

## 固定约束

- Windows 非模拟器专用；不得引入新依赖。
- Steam 自动点击仅限精确中文签名“无法同步 + 未能将您的存档 + Steam 云同步 + 仍然进行游戏”。
- 不点击“取消”，不基于固定坐标盲点，不记录截图或完整 OCR。
- 所有轮询均使用 `monotonic()` 和命名时限，禁止新无限循环。
- 启动失败必须以 `withOutGameWinError` 结束当前任务，不能转化为下一次启动请求。
- 改动遵循 pytest Red → Green → Refactor，最终运行全量 pytest 与 Ruff。

## Task 1：Steam 云同步对话框识别（Red → Green）

**文件：**
- 新建 `tests/test_steam_cloud_recovery.py`
- 新建 `module/game_and_screen/steam_cloud.py`

**产物接口：**

```python
OcrBounds = tuple[int, int, int, int]
OcrEntry = tuple[str, OcrBounds]

@dataclass(frozen=True)
class SteamCloudDialog:
    continue_position: tuple[int, int]
    continue_bounds: OcrBounds


def resolve_steam_cloud_dialog(entries: list[OcrEntry]) -> SteamCloudDialog | None: ...
def handle_steam_cloud_sync_dialog() -> bool: ...
```

- [ ] 写纯函数失败用例：完整用户截图 OCR 布局产生 `(594, 351)`；缺“无法同步”、缺存档正文、缺“Steam 云同步”、缺“仍然进行游戏”、仅出现“取消”、目标按钮在正文上方均返回 `None`。
- [ ] 运行 `uv run pytest tests/test_steam_cloud_recovery.py -q`，确认因模块/函数缺失失败。
- [ ] 新建 `steam_cloud.py`：用不可变 dataclass 和局部 `_entry_with_text()` 聚合文本；用正文底部与继续按钮中心的相对位置验证布局；不得导入 OCR、自动化、配置或日志。
- [ ] 重跑上述纯函数用例，确认通过。
- [ ] 为 I/O 适配写失败用例：注入截图、OCR、点击函数时，完整签名只点击 `continue_position`；截图为空、OCR 为空、识别不完整、OCR 抛异常均返回 `False` 且不点击。
- [ ] 实现 `handle_steam_cloud_sync_dialog()`：生产侧延迟导入 `pyautogui` 和 `module.ocr.ocr`，用桌面截图与同帧 OCR 框得到绝对坐标；只在 `resolve_steam_cloud_dialog()` 成功后点击，异常写 `debug` 并返回 `False`。
- [ ] 运行 `uv run pytest tests/test_steam_cloud_recovery.py -q`，确认所有 Task 1 用例通过。

## Task 2：有界启动请求（Red → Green）

**文件：**
- 修改 `tests/test_steam_cloud_recovery.py`
- 修改 `module/game_and_screen/game.py`
- 修改 `module/game_and_screen/screen.py`
- 修改 `tasks/base/script_task_scheme.py`

**产物接口：**

```python
# module/game_and_screen/game.py
GAME_LAUNCH_TIMEOUT_SECONDS = 120.0

def start_game(self) -> bool: ...
def handle_pending_launch(self) -> bool: ...
def finish_launch_attempt(self) -> None: ...

# module/game_and_screen/screen.py
def init_handle(self, start_if_missing: bool = True) -> bool: ...
```

- [ ] 写失败用例：失效路径的首次启动仅调用一次 Steam URL；启动请求仍待处理时第二次 `start_game()` 不调用 URL/本地启动；`handle_pending_launch()` 对同一请求至多点击一次云同步；窗口出现和超时都会清除请求状态。
- [ ] 写失败用例：`Screen.init_handle(start_if_missing=False)` 找不到窗口时不调用 `Game.start_game()`；`init_game()` 在固定次数/时限内只调用该无隐式启动变体，超时抛 `withOutGameWinError`，不永久循环。
- [ ] 运行对应单测，确认行为与当前重复 Steam 调用/无限等待冲突而失败。
- [ ] 在 `Game` 中实现私有待启动时间戳、单次云同步点击标记与一次性路径失效日志标记；本地路径存在时优先 `os.startfile()`，否则调用 URL；请求等待期间不重新发起启动。
- [ ] 调整 `Screen.init_handle()`：默认调用点保持兼容；传 `False` 时只尝试获得窗口、记录失败，不启动游戏。
- [ ] 调整 `init_game()`：发起一次启动，然后用 `monotonic()` 截止时间轮询窗口；每轮对待启动调用云同步处理；窗口成功时清理启动请求并继续，超时时清理并抛 `withOutGameWinError("游戏窗口启动超时")`。
- [ ] 运行 `uv run pytest tests/test_steam_cloud_recovery.py -q`，确认 Task 1/2 用例全绿。

## Task 3：统一优雅关闭与回归防护（Red → Green）

**文件：**
- 修改 `tests/test_steam_cloud_recovery.py`
- 修改 `module/game_and_screen/game.py`
- 修改 `tasks/base/retry.py`
- 修改 `module/system_actions.py`

**产物接口：**

```python
# module/game_and_screen/game.py
GAME_GRACEFUL_CLOSE_TIMEOUT_SECONDS = 30.0

def close_game(self) -> bool: ...

# tasks/base/retry.py，保留兼容入口
def kill_game() -> None: ...
```

- [ ] 写失败用例：`close_game()` 有有效窗口时先发送 `WM_CLOSE`；进程在宽限期内退出时不调用终止；超时时才按进程名终止；没有游戏进程时返回成功而不终止。
- [ ] 写失败用例：`retry.kill_game()` 和 `system_actions._action_exit_game()` 都委托 `game_process.close_game()`，不再各自调用 `taskkill /F`。
- [ ] 运行对应测试，确认当前直接 `taskkill /F` 实现失败。
- [ ] 在 `Game.close_game()` 使用 `win32gui.PostMessage(hwnd, WM_CLOSE, 0, 0)` 请求正常退出，按命名时限轮询 `check_game_alive()`；超时后用 `subprocess.run(["taskkill", "/F", "/IM", process_name])` 作为唯一强杀兜底，并按成功/失败记录日志。
- [ ] 将 `retry.kill_game()` 改为委托 `game_process.close_game()`；删除该函数内重复的窗口 PID 强杀和轮询。将 `_action_exit_game()` 的 Windows 分支委托同一方法，保留模拟器分支不变。
- [ ] 运行 `uv run pytest tests/test_steam_cloud_recovery.py -q`，确认关闭语义及全文件用例通过。

## Task 4：全量验证与审计

**文件：**
- 修改 `.trellis/tasks/08-09-steam-cloud-launch-recovery/prd.md`（完成状态与实际验证结果）
- 如有新的可复用启动恢复约束，修改 `.trellis/spec/backend/error-handling.md` 与 `quality-guidelines.md`

- [ ] 运行 `uv run pytest tests/test_steam_cloud_recovery.py tests/test_server_error_recovery.py -q`。
- [ ] 运行 `uv run ruff check module/game_and_screen/steam_cloud.py module/game_and_screen/game.py module/game_and_screen/screen.py tasks/base/retry.py tasks/base/script_task_scheme.py module/system_actions.py tests/test_steam_cloud_recovery.py --ignore E722`。
- [ ] 运行 `uv run pytest`，逐条修复本任务引入的失败。
- [ ] 执行 `python -m compileall module/game_and_screen tasks/base module/system_actions.py`。
- [ ] 审查 `git diff --check`、`git diff -- <affected files>`，确认没有日志敏感信息、无限轮询或 Steam“取消”点击路径。
- [ ] 更新任务 PRD、设计和实施清单中的实际测试证据；把通用的有界启动/关闭错误处理契约更新到 Trellis spec。
- [ ] 提交前复查用户验收：云同步弹窗仅点击“仍然进行游戏”、启动不会重复唤起 Steam、退出优先正常关闭。

## 实际执行证据

- Red：初始 `tests/test_steam_cloud_recovery.py` 因 `ModuleNotFoundError: module.game_and_screen.steam_cloud` 失败；启动状态、窗口轮询、云同步一次确认、优雅关闭、旁路截图恢复和进程名精确匹配测试均在对应功能缺失时红灯后实现。
- Green：`uv run pytest tests/test_steam_cloud_recovery.py tests/test_server_error_recovery.py -q` 通过；独立审查修复了跨桌面区域锚点误点、已有进程未进入 pending、点击异常重试、子串进程名匹配和关闭后残留 pending 等边界。
- 完整验证：`uv run pytest` 输出 `128 passed in 1.60s`；Ruff、`compileall` 和 `git diff --check` 均通过。
- 顶层日常失败测试补充 `auto.click_element` 桩以隔离本断言外的真实截图/窗口栈；此前该未隔离调用在新的优雅关闭恢复路径下阻塞进程枚举。

## 回滚点

- Task 1 之后：删除 `steam_cloud.py` 与对应测试，不影响现有启动路径。
- Task 2 之后：若真实 Steam UI 无法可靠 OCR，禁用 `handle_pending_launch()` 内的点击调用；保留有限启动超时，禁止恢复无限循环。
- Task 3 之后：若某 Windows 环境不响应 `WM_CLOSE`，30 秒后仍会走现有强杀等价路径；无需恢复分散的 `taskkill` 实现。
