# 设计：日常战斗事件状态机审计与统一恢复

## 1. 目标与边界

本设计修复日常连续场次把战斗事件残页带入下一次采光入口搜索的问题，但不重写 `Battle.fight()` 的整套战斗识别。核心做法是把**事件页的 OCR 语义识别**抽到 `tasks/event/event_handling.py`，让战斗循环和返回主界面流程共用同一份判定；再在日常入口增加恢复栅栏，保证未知页不会直接消耗 `thread_luxcavation()` 的 30 次入口重试。

事件处理必须继续优先复用现有模板和 `EventHandling.decision_event_handling()`；OCR 只负责 beta 模板失效后的推进按钮及等待状态，不能按“土偶”“罪人”等事件文案分支。所有等待都受既有战斗总超时或新的局部等待上限约束，不能通过重置总开始时间制造无限循环。

## 2. 状态与出口

| 状态 | 识别条件 | 动作 | 成功后状态 | 超时或失败出口 |
| --- | --- | --- | --- | --- |
| 日常入口 / 采光页 | `home/luxcavation_assets`、`luxcavation/*_assets`、`luxcavation/*_enter` 模板 | 按现有经验本/纽本导航和关卡选择 | 编队 | 入口循环耗尽后先执行恢复；恢复失败才返回 `False` |
| 编队 | `teams/identify_assets` | 选择队伍，再调用 `Battle.to_battle()` | 战斗加载或服务器错误 | 选队或开战返回 `False` 时停止本场，绝不盲点开始战斗 |
| 服务器错误倒计时 | OCR 同时命中错误文案与 `重试N` | 不点击，等待游戏倒计时 | 原状态或可重试 | 由 `handle_server_error_dialog()` 拦截，不执行普通识图 |
| 服务器错误可重试 | OCR 弹窗结构 + 金色重试文字 | 5 秒节流点击重试 | 原状态 | 长期不可用转入关闭重启 |
| 服务器错误长期不可用 | OCR 弹窗结构 + 灰色重试持续 15 秒 | 点关闭、重启游戏 | 主界面恢复 | `handle_server_error_dialog()` 返回 `False`，调用方停止当前路径 |
| 战斗进行中 | `battle/pause_assets` 或回合/胜率识别 | 现有战斗操作 | 战斗进行中、事件或结算 | 受总战斗超时限制 |
| 事件选项页 | `choices_assets` 与 `select_first_option_assets` | 现有模板优先；第一选项失效后用多目标选择候选项 | 判定页或事件结果 | 不匹配“土偶/罪人”文案；交给通用事件页 OCR 栅栏 |
| 判定页 | 模板 `perform_the_check_feature_assets`，或 OCR 命中 `进行判定` | 先运行 `decision_event_handling()`；模板未命中时按 OCR 按钮中心点击 | 判定动画/结果页 | 结果页判定仍在则等待；局部等待超时后返回恢复失败 |
| 判定结果页 | OCR 命中 `判定成功` 或 `判定失败`，且可见 `继续` | 点击“继续”的 OCR 外接矩形中心 | 战斗、事件下一页或结算 | 继续尚未出现时返回等待，不消耗战斗 chance |
| 判定结果动画 | OCR 命中结果关键词但没有推进按钮 | 记录一次等待，短暂 sleep，重置战斗 `chance` | 判定结果页 | 受战斗总超时和入口恢复等待上限保护 |
| 普通事件推进页 | OCR 命中 `继续` / `进行判定`，且同时存在事件上下文关键词 | 点击匹配文本中心 | 后续事件或战斗 | 无事件上下文的独立“继续”不得点击，避免误触普通界面 |
| 日常胜利结算 | OCR 同时命中 `战斗胜利` 与 `确认` | 点确认 OCR 中心 | 日常入口或主界面 | 返回到下一场前经过恢复栅栏 |
| 残留事件页 | 入口前的 OCR 解析结果为 click/wait | 点击推进或有界等待，直至不再是事件页 | 可导航页面 | 有界等待耗尽，调用 `back_init_menu()`；该函数失败则取消本场 |
| 其他非采光页 | 没有可推进事件动作，且日常入口循环耗尽 | 调用 `back_init_menu()`，重新从主页导航一次 | 主界面 → 采光入口 | 恢复失败返回 `False`，不把原页继续当纽本入口搜索 |

## 3. 共享 OCR 解析契约

在 `tasks/event/event_handling.py` 增加与 UI 自动化无关的纯解析函数：

```python
@dataclass(frozen=True)
class EventPageResolution:
    state: Literal["advance", "wait"]
    position: tuple[int, int] | None
    reason: str


def resolve_event_page(
    entries: list[tuple[str, tuple[int, int, int, int]]],
) -> EventPageResolution | None:
    ...
```

输入使用 `Automation.get_ocr_entries()` 已提供的 `(文本, (x1, y1, x2, y2))`；函数本身不得截图、睡眠、鼠标点击、改全局状态或依赖当前语言。它负责把 OCR 文本标准化后识别以下有限语义：

1. **`advance`**：存在事件语义（`判定成功`、`判定失败`、`进行判定`，或结果语义配合 `继续`）且能定位目标按钮。优先选择“继续”，其次“进行判定”；坐标恒为该 OCR 文本外接矩形的中心。
2. **`wait`**：存在 `判定成功` / `判定失败` 等结果语义，但尚未识别到对应推进按钮。这是约 40 秒结果动画的已知中间态。
3. **`None`**：没有足够的事件语义。不能因为任意页面出现“继续”就返回点击动作。

此契约将服务器错误的“纯识别函数 + 副作用处理函数”模式复用于事件页：单元测试只喂 OCR 条目，不需要游戏窗口、模板资源或 RapidOCR。

## 4. 运行时编排

### 4.1 `Battle.fight()`

保留现有的模板优先顺序：选项模板、判定模板、`continue` / `proceed` / `commence` / `skip` 模板、日常结算 OCR。模板未推进时，读取当前帧一次 `auto.get_ocr_entries()` 并调用 `resolve_event_page()`：

- `advance`：调用 `auto.mouse_click(*position)`，将 `chance` 重置为 `INIT_CHANCE`，然后进入下一轮；
- `wait`：将 `chance` 重置为 `INIT_CHANCE`，按当前 `waiting` 短暂等待后进入下一轮；
- `None`：完全保留现有 chance、retry 和战斗失败路径。

这里**只重置局部识别机会 `chance`**，不修改 `start_time`。因此事件动画可以超过原先十余轮的识别预算，但仍受 `900 + 300 * combat_count` 秒的总战斗超时约束。`decision_event_handling()` 保持只处理判定对象选择；它不负责结果页按钮。

### 4.2 返回主界面与日常入口

`back_init_menu()` 在普通 `esc` / 空白点击之前也调用同一个解析器：

- 对 `advance` 点击 OCR 目标并继续循环；
- 对 `wait` 以固定的短间隔等待，并保留独立的、有限的事件等待时钟；
- 事件等待超出上限时，遵守现有 `allow_restart` 策略：`allow_restart=False` 返回 `False`，否则走原有重启恢复，绝不无限刷新事件页。

在 `EXP_luxcavation()` 和 `thread_luxcavation()` 的入口循环耗尽处，不应直接打印“无法进入…”。先调用 `back_init_menu()` 恢复到主页，成功后重新开始**一次**完整入口循环；第二次耗尽或恢复失败才返回 `False`。恢复尝试数必须是显式常量，不能在循环内无限重置 `loop_count`。这既覆盖未被战斗循环清掉的事件页，也覆盖其他无法从现有入口模板继续导航的残页，同时没有在每一场开始时无条件回主页，保留连续场次优化。

`onetime_EXP_process()` 与 `onetime_thread_process()` 继续以入口函数的布尔返回值为硬门：入口恢复最终失败时，后续选队、开始战斗、`fight()` 均不执行。

## 5. 失败模型与日志

- 日常入口、事件推进、返回主界面三者均以 `bool`/明确分辨率表示是否可继续；不要吞掉失败后继续寻找纽本入口。
- 使用 `log.debug` 记录 OCR 解析的状态和原因（例如“事件结果页等待继续按钮”）；仅在恢复耗尽、重启或取消本场时使用 `warning` / `error`。
- 不在日志记录完整截图、账号信息或与当前状态无关的 OCR 全文。
- 保留 `retry()` / `handle_server_error_dialog()` 的优先级：服务器错误被拦截时，事件解析和普通入口识图都不运行。

## 6. 验证与回滚

自动化测试分成纯解析、战斗循环集成、日常入口恢复三层，测试夹具仅模拟当前已公开的 `Automation` 方法。完整测试运行 `pytest`；范围静态检查运行 `ruff check tasks/battle/battle.py tasks/event/event_handling.py tasks/base/back_init_menu.py tasks/daily/luxcavation.py tasks/base/script_task_scheme.py tests --ignore E722`，其中 `E722` 是既有基线。

运行风险是 beta OCR 对真实截图的分词可能与日志不同。因此自动测试通过后仍必须由用户完成“纽本多场 + 判定事件”的实机回归；实机失败时保存脱敏 OCR 条目与日志时间段，再扩展解析关键词/空间约束，而不是新增单个事件模板。若新逻辑造成异常点击，可回滚本任务涉及的事件解析和单次入口恢复提交；现有模板路径与每项目结束后的主页/换饼行为保持不变。