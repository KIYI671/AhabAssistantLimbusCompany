# Steam 云同步无人值守恢复设计

## 目标与边界

在 Windows 桌面版启动《边狱巴士》时，把 Steam 云同步弹窗、游戏进程、游戏窗口三个独立状态统一为有限状态恢复。AALC 仅处理用户明确授权的一种 Steam 对话框：中文“无法同步”且同时包含“未能将您的存档”“Steam 云同步”和“仍然进行游戏”。命中后点击该 OCR 文本框中心；缺少任一证据时不点击。

不控制 Steam 的“取消”按钮，不处理其他 Steam 窗口，不重试到无限期。游戏实际云端同步失败仍由 Steam/网络负责；AALC 的职责是让授权的“离线继续本地游戏”选择可无人值守地完成。

## 状态与数据流

```text
init_game/restart_game
  -> Game.start_game() 一次发起本地路径或 Steam URL
  -> 有限轮询 Screen.init_handle(start_if_missing=False)
       -> 有游戏窗口: 设置窗口，成功
       -> 无窗口: Game.handle_pending_launch()
            -> 全桌面截图 -> OCR 条目 -> resolve_steam_cloud_dialog()
               -> 精确匹配: pyautogui 点击“仍然进行游戏”中心，继续等待
               -> 不匹配: 不点击，继续到固定启动时限
  -> 超过时限: 记录 error，抛出既有 withOutGameWinError，停止本轮任务
```

启动请求由 `Game` 单一持有：`_launch_requested_at` 代表一段尚未结束的启动窗口。其存在期间不得再次打开 `steam://rungameid/1973530`。进程存在但窗口未就绪也属于等待态，不能作为再次启动理由。请求成功（窗口得到）或失败（超时）后清除该状态。

## 模块边界

### `module/game_and_screen/steam_cloud.py`

新模块分离纯识别与 Windows I/O：

- `resolve_steam_cloud_dialog(entries) -> SteamCloudDialog | None` 是无 OCR、无截图、无点击、无配置依赖的纯函数。它验证所有中文语义锚点、目标按钮边界非空、并验证按钮位于弹窗正文下方。
- `handle_steam_cloud_sync_dialog(capture, recognize, click) -> bool` 在可注入 I/O 边界上调用纯函数；返回 `True` 仅表示已执行一次授权点击。
- 生产适配器使用现有 `pyautogui.screenshot()` 获取全桌面帧、现有 `module.ocr.ocr.run()` 得到文本框、`pyautogui.click()` 点击桌面绝对坐标。它不复用 `auto`，因为 `auto` 依赖尚未出现的游戏窗口。

全桌面坐标、OCR 输出与点击动作由同一帧和同一坐标系产生，防止把 Steam 的坐标当作游戏客户区坐标。每个启动请求最多自动确认一次，避免对画面残留或点击无效时重复点击。

### `module/game_and_screen/game.py`

`Game` 负责启动及优雅退出：

- 启动本地配置路径存在时优先 `os.startfile()`；路径无效时记录一次可行动的错误后使用 Steam URL 回退。
- `start_game()` 只创建一次待启动请求；请求仍在等待窗口时只检查一次云同步确认，不重复启动。
- `finish_launch_attempt()` 清理待启动状态，供成功或终止路径调用。
- `close_game()` 先向有效游戏窗口发送 `WM_CLOSE`，轮询进程退出；达到正常退出时限后才终止同名游戏进程并记录 warning。进程枚举按完整文件名大小写无关匹配，避免旧句柄导致漏关。

### 调用点

- `Screen.init_handle(start_if_missing: bool = True)` 支持被启动轮询调用时禁用隐式重启；现有独立调用维持旧的“可尝试启动”语义。
- `tasks/base/script_task_scheme.init_game()` 负责固定总时限轮询，成功才设置窗口；超时后调用 `finish_launch_attempt()` 并抛出既有 `withOutGameWinError`，不再 `while` 无限等待。
- `tasks/base/retry.kill_game()` 变为 `game_process.close_game()` 的兼容包装；`module/system_actions._action_exit_game()` 同样委托该公共方法，保证异常恢复和“任务结束后退出游戏”遵循同一优雅退出策略。

## 失败与日志

| 事件 | 行为 | 日志级别 |
| --- | --- | --- |
| 本地路径不存在 | 一次性说明路径无效和将使用 Steam 回退 | warning |
| 发起启动请求 | 记录本地/Steam 启动方式 | info |
| 云同步精确匹配 | 点击“仍然进行游戏”，本请求仅一次 | warning |
| Steam 截图/OCR 失败 | 不点击，等待后续轮询 | debug |
| 未识别的 Steam 窗口 | 不点击，保持等待直至启动时限 | debug |
| 启动时限耗尽 | 清理请求并停止本轮任务 | error |
| 正常关闭超时并强制结束 | 记录为降级恢复 | warning |

日志不记录全量 OCR、截图或存档信息。

## 兼容性与回滚

仅在 Windows 非模拟器路径执行 Steam 桌面识别；模拟器维持既有启动/关闭实现。没有新增第三方依赖，使用项目已有 `pyautogui`、`pywin32`、Pillow 与 RapidOCR。

如新识别出现误匹配风险，移除 `handle_pending_launch()` 的云同步调用即可恢复为“有限等待后失败”的安全行为；启动无限循环仍将被修复，不会回退。

## 测试策略

1. 对 `resolve_steam_cloud_dialog()` 写纯单测：完整签名、缺“无法同步”、缺正文、缺目标按钮、只有“取消”、按钮不在正文下方均不授权点击。
2. 对 I/O 适配层注入截图、OCR、点击回调：完整签名仅点击目标中心一次；空/异常识别不点击。
3. 对 `Game` 注入进程、文件、URL/本地启动、单调时间及云同步处理依赖：验证待启动期间不重复触发 Steam、路径回退受限、已运行进程不启动、成功/超时清除状态。
4. 对 `init_game()` 与 `Screen.init_handle()` 打桩：验证窗口未就绪最终有界失败、不调用隐式启动；窗口出现时正常设置窗口。
5. 对关闭公共路径打桩：验证先 `WM_CLOSE`、正常退出不强杀、超时才终止，并且 `retry.kill_game()` 与结束后退出均委托公共方法。
