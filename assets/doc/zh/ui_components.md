# UI 组件开发说明

本文档整理当前项目中常用 UI 组件的分层、配置绑定、样式与翻译约定。新增或调整界面时，优先复用现有组件和模式。

## 组件分层

### 基础控件：`app/base_tools.py`

`base_tools.py` 提供最小粒度的配置控件，通常负责一件事：显示一个控件，并把用户操作同步到配置或 `mediator`。

常用类：

- `BaseCheckBox`：绑定配置名的复选框。若 `cfg.get_value(config_name)` 存在，直接写入全局配置；否则通过 `mediator.team_setting` 发给队伍设置页。
- `BaseComboBox`：绑定配置名的下拉框，`add_items()` 接收显示文本到配置值的映射。
- `BaseSpinBox`：绑定配置名的数字输入框。
- `BaseLineEdit`：队伍设置内使用的文本输入框，通过 `mediator.team_setting` 发送变更。
- `BaseLabel`：统一标签样式，并监听主题变化。
- `ToSettingButton`、`ChangePageButton`：用于队伍页、页面切换等按钮行为。

基础控件一般会保存：

- `self.config_name`：配置项或对象名。
- `self.check_box_title`、`self.text` 等原始文案：用于 `retranslateUi()`。
- 子控件引用，例如 `self.check_box`、`self.combo_box`：用于后续刷新状态或翻译。

如果某个值只在 `__init__()` 中计算一次，后续不再读取，优先使用局部变量，不要挂到 `self` 上。

### 组合控件：`app/base_combination.py`

`base_combination.py` 把基础控件组合成更高层的页面元素，主要负责布局、弹窗和多控件联动。

常用类：

- `CheckBoxWithButton`：复选框 + 跳转按钮。
- `CheckBoxWithComboBox`：复选框 + 下拉框，可追加第二个下拉框。
- `LabelWithComboBox`、`LabelWithSpinBox`、`MirrorSpinBox`：标签 + 输入控件。
- `MirrorTeamCombination`：镜牢队伍选择项，包含队伍复选框、备注名、顺序和设置按钮。
- `SwitchSettingCard`、`ComboBoxSettingCard`、`BasePushSettingCard`：基于 qfluentwidgets 设置卡片封装。
- `DailySettingCard`、`HotkeySettingCard`：带业务弹窗的设置卡。
- `TextProgressBar`：带文本绘制的进度条。

组合控件的典型写法：

```python
class ExampleCombination(QFrame):
    def __init__(self, config_name, title, parent=None):
        super().__init__(parent)
        self.setObjectName(config_name)
        self.title = title
        self.layout = QHBoxLayout(self)
        self.checkbox = BaseCheckBox(config_name, None, title, parent=self)
        self.layout.addWidget(self.checkbox)

    def retranslateUi(self):
        self.checkbox.check_box.setText(self.tr(self.title))
```

保留 `self.title` 是为了语言切换时重新翻译；如果没有 `retranslateUi()` 或后续刷新需求，就不需要保存。

### 页面组装：`app/team_setting_card.py`

`team_setting_card.py` 负责把基础控件和组合控件组织成完整队伍设置页。它通过 `mediator.team_setting` 接收子控件变化，并写入当前队伍的 `TeamSetting` 对象。

常见流程：

1. 子控件发送 `{config_name: value}`。
2. `TeamSettingCard.setting_team()` 根据 key 判断写入普通字段、罪人选择、星光加成、第二体系、商店忽略等结构。
3. 点击保存时调用 `cfg.set_value(..., config_obj=cfg.config.teams)` 写回配置。
4. `read_settings()`、`refresh_starlight_select()`、`refresh_sinner_order()` 负责从 `TeamSetting` 刷新 UI。

新增队伍内配置时，应同步检查：

- `module/config/config_typing.py` 中的 `TeamSetting` 字段。
- `assets/config/config.example.yaml` 默认值。
- `team_setting_card.py` 的读取、保存和刷新逻辑。
- 是否需要加入翻译更新。

## 样式管理

### qfluentwidgets 控件

项目主要使用 qfluentwidgets。对于 qfluentwidgets 控件或基于其封装的控件，优先使用：

```python
setCustomStyleSheet(widget, light_qss, dark_qss)
```

若控件本身已接入 qfluentwidgets 的主题系统，通常不需要额外注册。

### 普通 Qt 控件

部分自定义控件直接继承 `QFrame`、`QPushButton`、`QLabel` 等普通 Qt 控件。若它们需要跟随浅色/深色主题更新，需要先注册到 qfluentwidgets 样式管理器。

`app/starlight_bonus.py` 使用了空样式源：

```python
class EmptyStyleSheet(StyleSheetBase):
    def content(self, theme=None) -> str:
        return ""
```

它本身不提供样式，作用是让普通 Qt 控件参与主题刷新：

```python
setStyleSheet(widget, EmptyStyleSheet())
setCustomStyleSheet(widget, light_qss, dark_qss)
```

不要因为 `EmptyStyleSheet` 内容为空就直接删除。对于普通 Qt 控件，如果需要主题切换后自动刷新自定义 QSS，应保留这类注册逻辑。

### 样式常量

主题相关 QSS 和颜色集中放在 `app/common/ui_config.py`，例如：

- `get_setting_layout_style()`
- `get_pivot_item_qss()`
- `get_starlight_level_button_qss()`
- `get_starlight_paint_colors()`

新增复杂样式时，优先把颜色、QSS 模板、主题分支放到 `ui_config.py`，组件文件只负责调用。

## 自绘组件

### `app/custom_pivot.py`

`FullWidthPivot` 扩展 qfluentwidgets 的 `Pivot`，使用自定义 `PivotItem` 管理选中状态，并在 `paintEvent()` 中绘制全宽指示器和底部分割线。

关键点：

- `PivotItem.setProperty("selected", "...")` 配合 QSS 属性选择器刷新样式。
- `qconfig.themeChanged.connect(self._updateTheme)` 用于主题切换时更新子项颜色。
- `paintEvent()` 中调用 `QWidget.paintEvent(self, e)`，避免默认 `Pivot` 绘制干扰自定义指示器。

### `app/starlight_bonus.py`

`StarlightLevelSelector` 是开局星光的三段选择器，视觉效果主要由自绘和 QSS 共同完成：

- 左段为星光名称和消耗。
- 中段为 `+`。
- 右段为 `++`。
- `paintEvent()` 绘制背景色、边框和分隔线。
- `set_state(selected, level)` 同步选中状态、按钮 checked 状态、消耗显示和重绘。
- 点击后通过 `mediator.team_setting` 分别发送星光是否启用和等级。

此组件虽然使用普通 `QPushButton`，但不是简单按钮。若改为 qfluentwidgets 按钮，为保持现有样式，仍可能需要保留自绘和自定义 QSS。

## 配置绑定约定

### 全局配置

当配置项存在于 `ConfigModel` 中时，基础控件通常直接调用：

```python
cfg.set_value(config_name, value)
```

例如全局开关、设置页选项、快捷键等。

### 队伍配置

队伍设置弹窗内的控件一般不直接保存到文件，而是发送给当前页面：

```python
mediator.team_setting.emit({config_name: value})
```

由 `TeamSettingCard.setting_team()` 写入当前 `self.team_setting`。用户点击保存后再写回 `cfg.config.teams`。

这样可以支持“确认保存”和“取消不保存”的交互。

## 翻译约定

需要运行时切换语言的组件应实现 `retranslateUi()`，并保存原始文案：

```python
self.box_text = check_box_title

def retranslateUi(self):
    self.box.check_box.setText(self.tr(self.box_text))
```

创建固定文案时，优先使用 `QT_TRANSLATE_NOOP` 标记，便于脚本提取翻译。

注意：

- 不要只保存已经翻译后的文本，否则切换语言时无法恢复原始 key。
- 组合控件的 `retranslateUi()` 应继续调用子控件的 `retranslateUi()`。
- Tooltip 文案也需要在 `retranslateUi()` 中刷新。

## 开发检查清单

新增 UI 组件前，先确认是否能复用：

- 只是单个配置控件：优先放在或复用 `base_tools.py`。
- 是多个基础控件的布局组合：优先放在或复用 `base_combination.py`。
- 是某个页面专用的复杂交互：可以放在页面附近的独立文件，例如 `starlight_bonus.py`。
- 是通用样式、颜色、QSS：放到 `app/common/ui_config.py`。

提交前建议检查：

- `config_name` 是否和配置字段一致。
- 是否需要 `setObjectName(config_name)` 方便 `findChild()` 和 QSS 定位。
- 是否正确处理主题切换。
- 是否实现或调用 `retranslateUi()`。
- 是否避免保存只在初始化中使用的一次性值。
- 是否避免把业务保存逻辑散落到子控件里。
- 是否在队伍设置中保持“临时编辑，确认后保存”的模式。
