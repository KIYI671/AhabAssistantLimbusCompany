# 2026-03-05 Sidebar Layout (Settings Page) – Design

## 背景
- 需求：设置页增加左侧固定导航栏，点击即可跳转到对应分组；右侧继续展示现有分组内容。
- 现状：SettingInterface 继承 ScrollArea，setWidget(scroll_widget)，内部用 ExpandLayout 纵向堆叠各 BaseSettingCardGroup。无侧边导航，分组只能滚动浏览。

## 目标
- 在左侧提供固定宽度的导航栏，列出现有分组；点击导航项滚动右侧内容到对应分组；滚动时高亮当前分组。
- 保持现有分组/卡片创建逻辑和样式，右侧依旧为可滚动的设置分组列表。
- 兼容主题模式（AUTO/LIGHT/DARK），保持良好对比度。

## 设计方案
### 1) 布局架构
- SettingInterface 继续作为容器，但 setWidget 指向 main_widget，main_layout 使用 QHBoxLayout（或类似）形成双列：
  - 左列：nav_frame（QFrame），固定宽度 ~180px，竖直布局导航按钮。
  - 右列：content_scroll（QScrollArea），内部内容为现有 scroll_widget + expand_layout（原有分组堆叠保持不变）。
- ScrollArea 的 setWidgetResizable(True) 仍开启；左列不随右侧滚动，右侧独立竖直滚动。

### 2) 导航项与锚点
- 导航项来源：当前分组顺序（游戏设置、镜牢主题包、模拟器设置、启动游戏、定时执行、个性化、更新、日志、关于、实验性）。
- 构建 nav_items 列表/字典：{ key, title, widget }，widget 为对应 BaseSettingCardGroup。
- 点击导航项：调用 content_scroll.ensureWidgetVisible(target_widget, xMargin=0, yMargin≈12) 或通过 verticalScrollBar() 设置值，滚动到分组顶部附近。

### 3) 交互与状态
- 点击导航：立即滚动；可加小偏移防止分组贴边。
- 滚动高亮：监听 content_scroll.verticalScrollBar().valueChanged，计算当前视窗内最接近顶部的分组，更新导航高亮。
- 默认高亮：进入页面高亮第一个分组。导航按钮可用 QPushButton 或 qfluentwidgets 按钮，支持键盘 Tab 焦点。

### 4) 样式与适配
- 左栏宽度：170–190px（取 180px），上下 padding 约 12px，项间距 4–6px。
- 主题：沿用 qfluentwidgets 主题；导航选中态使用主题强调色/半透明背景，文字用当前前景色；悬停态略浅背景。
- 滚动条：左栏无滚动条，右侧沿用现有；整体背景保持透明，与当前 set_style_sheet 一致。
- 可选图标：可用 FIF 图标，若不需要则保留纯文本。

### 5) 测试要点
- 导航点击跳转准确，且分组未被遮挡。
- 手动滚动时，高亮能随当前分组变化。
- 主题 AUTO/LIGHT/DARK 下，导航选中/悬停可读性良好。
- 不同缩放设置（zoom_scale）下，左栏宽度与内容区域布局正常。
- 首次进入默认高亮第一项。

## 影响范围
- 主要改动文件：app/setting_interface.py（布局与导航逻辑）。
- 可能新增少量样式定义（如需 QSS，优先内联 setStyleSheet 于 nav_frame/按钮）。
- 无需改动分组/卡片创建逻辑。

## 后续实现思路（预告）
- 重构 setWidget 指向 main_widget（双列布局），保留现有 expand_layout 内容。
- 构建 nav_items + ensureWidgetVisible 滚动 + 滚动监听高亮。
- 补充最小样式（选中/悬停态）并验证三种主题与缩放。
