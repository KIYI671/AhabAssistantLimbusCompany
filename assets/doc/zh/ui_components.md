# UI 组件开发说明

本文档整理当前项目中常用 UI 组件的分层、配置绑定、样式与翻译约定。新增或调整界面时，优先复用现有组件和模式。

## UI 架构层次

当前 UI 不是单纯的 `PySide6 + qfluentwidgets`，而是由几层共同组成：

- `PySide6`：窗口、布局、信号槽、线程、托盘、翻译和自绘等 Qt 基础能力。
- `qfluentwidgets`：Fluent 风格控件、设置卡片、导航、弹窗、进度环和主题系统。
- `qframelesswindow`：无边框窗口、标题栏和无边框弹窗。
- `app/base_tools.py`：复选框、下拉框、按钮、标签等基础控件。
- `app/base_combination.py`：设置卡片、队伍选择、进度条等组合控件。
- `app/card/messagebox_custom.py`：确认框、警告框、更新弹窗、输入弹窗和提示条。
- `app/custom_pivot.py`：顶部 `Pivot` 导航和选中指示器。
- `app/starlight_bonus.py`：开局星光按钮、等级选择器和 Tooltip。
- `app/my_app.py`：主窗口、顶层页面切换、托盘、公告和更新进度。
- `app/farming_interface.py`：主功能页（左栏放任务列表面板、亚哈共鸣和结束后操作）、日志栏和脚本启停。
- `app/page_card.py`：设置页基类 `PageCard`，窗口设置、镜牢和帮助文档页面。
- `app/task_queue/`：主界面和定时任务编辑框共用的任务列表（`queue_list.py`）、主界面左栏的列表面板（`queue_panel.py`）、绑定当前任务的设置控件（`task_fields.py`、`task_store.py`）、日常 / 奖励 / 狂气换体等任务设置页（`task_pages.py`）和任务类型名等显示文字（`texts.py`）。
- `app/schedule/`：设置页「定时执行」的卡片和分组（`setting_group.py`）、编辑框（`editor_dialog.py`）和显示文字（`texts.py`）。控件通过 `module/schedule/book.py` 的 `ScheduleBook` 增删改定时任务，不直接读写 `cfg`。
- `app/setting_interface.py`：游戏、模拟器、定时执行、个性化、更新、日志和关于设置。
- `app/team_setting_card.py`：镜牢队伍、罪人选择、体系、商店策略、星光加成和统计信息。
- `app/tools_interface.py`：自动战斗、自动换饼、截图等小工具入口。
- UI 服务层：`cfg` 配置读写、`mediator` 跨页面信号、`LanguageManager` 运行时翻译、`app/common/ui_config.py` 主题 QSS，以及日志分发、Windows Toast、全局快捷键等桌面交互。

### 新功能的分层

新功能按三层放，每层用同一个功能名（做法同 MAA 的 `Configuration` / `ViewModels` / `Views`）：

| 层 | 放什么 | 任务列表 | 定时任务 |
|---|---|---|---|
| 配置模型 | 保存在 `config.yaml` 里的 pydantic 模型、旧配置迁移 | `module/config/task_queue.py`、`task_queue_legacy.py` | `Schedule` 也在 `module/config/task_queue.py` |
| 业务逻辑 | 状态怎么变、有副作用的操作；不 `import` Qt，有单元测试 | `module/task_queue/` | `module/schedule/` |
| 界面 | 只负责显示和把点击转给业务逻辑 | `app/task_queue/` | `app/schedule/` |

- 运行前检查和执行计划在 `tasks/base/run_plan.py`。
- `app/<功能>/` 里不直接读写 `cfg`。由创建它的页面把配置里的数据传进去，例如 `app/setting_interface.py` 创建 `ScheduleBook` 时传入 `cfg.config.schedules`。
- `app/task_queue/__init__.py` 要保持为空：`page_card.py` 在定义 `PageCard` 之前 `import` `task_fields`，如果 `__init__.py` 里 `import` 了 `task_pages`，会循环 `import`。
