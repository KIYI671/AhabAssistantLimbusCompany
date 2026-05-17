# 应用 UI 配置
from PySide6.QtCore import QT_TRANSLATE_NOOP, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QFrame
from qfluentwidgets import isDarkTheme, qconfig

BORDER_STYLE = {
    "dark": """border: 1px solid #545454; border-radius: {radius}px;""",
    "light": """border: 1px solid #c0c0c0; border-radius: {radius}px;""",
}

# 全局字体配置
FONT_FAMILIES = [
    "Segoe UI",  # Windows 现代UI字体
    "Microsoft YaHei",  # 微软雅黑
    "微软雅黑",  # 微软雅黑中文名
    "Noto Sans CJK SC",  # 跨平台中文字体
    "sans-serif",  # 最后回退到无衬线字体
    "SansSerif",  # 无衬线字体另一个名称
    "SimSun",  # 宋体
]

# 主窗口样式配置
MAIN_WINDOW_STYLES = {
    "dark": {"bg_color": "rgba(28, 28, 28, 1)"},
    "light": {"bg_color": "rgba(255, 255, 255, 1)"},
}

# 标题栏样式配置
TITLE_BAR_STYLES = {
    "dark": {"text_color": "white", "btn_color": Qt.white},
    "light": {"text_color": "black", "btn_color": Qt.black},
}


def apply_font_config():
    """应用全局字体配置"""
    qconfig.fontFamilies.value = FONT_FAMILIES


def get_main_window_style(is_dark: bool) -> dict:
    """获取主窗口样式"""
    return MAIN_WINDOW_STYLES["dark"] if is_dark else MAIN_WINDOW_STYLES["light"]


def get_title_bar_style(is_dark: bool) -> dict:
    """获取标题栏样式"""
    return TITLE_BAR_STYLES["dark"] if is_dark else TITLE_BAR_STYLES["light"]


# 设置卡片样式配置
SETTING_LAYOUT_STYLES = {
    "dark": {
        "border": "1px solid rgba(255, 255, 255, 0.25)",
        "border_hover": "1px solid rgba(255, 255, 255, 0.25)",
    },
    "light": {
        "border": "1px solid rgba(0, 0, 0, 0.25)",
        "border_hover": "1px solid rgba(0, 0, 0, 0.25)",
    },
}


def get_setting_layout_style(is_dark: bool) -> dict:
    """获取设置卡片样式"""
    return SETTING_LAYOUT_STYLES["dark"] if is_dark else SETTING_LAYOUT_STYLES["light"]


LOG_TEXT_EDIT_STYLES = {
    "dark": """
        TextEdit {
            color: rgba(255, 255, 255, 0.75);
            background-color: rgba(255, 255, 255, 0.01);
            border: 1px solid rgba(255, 255, 255, 0.25);
            border-radius: 5px;
            padding: 10px;
        }
        TextEdit:hover {
            background-color: rgba(255, 255, 255, 0.01);
            border: 1px solid rgba(255, 255, 255, 0.25);
        }
        TextEdit:focus {
            background-color: rgba(255, 255, 255, 0.01);
            border: 1px solid rgba(255, 255, 255, 0.25);
        }
    """,
    "light": """
        TextEdit {
            color: rgba(0, 0, 0, 0.75);
            background-color: rgba(0, 0, 0, 0.01);
            border: 1px solid rgba(0, 0, 0, 0.25);
            border-radius: 5px;
            padding: 10px;
        }
        TextEdit:hover {
            background-color: rgba(0, 0, 0, 0.01);
            border: 1px solid rgba(0, 0, 0, 0.25);
        }
        TextEdit:focus {
            background-color: rgba(0, 0, 0, 0.01);
            border: 1px solid rgba(0, 0, 0, 0.25);
        }
    """,
}


def get_log_text_edit_qss() -> tuple[str, str]:
    """Return (light_qss, dark_qss) for the log TextEdit."""
    return LOG_TEXT_EDIT_STYLES["light"], LOG_TEXT_EDIT_STYLES["dark"]


THEME_AWARE_TEXT_BROWSER_STYLES = {
    "dark": """
        ThemeAwareTextBrowser,
        ThemeAwareTextBrowser:hover,
        ThemeAwareTextBrowser:focus,
        ThemeAwareTextBrowser:focus:hover {
            background-color: rgba(28, 28, 28, 1);
            border: none;
        }
    """,
    "light": """
        ThemeAwareTextBrowser,
        ThemeAwareTextBrowser:hover,
        ThemeAwareTextBrowser:focus,
        ThemeAwareTextBrowser:focus:hover {
            background-color: rgba(255, 255, 255, 1);
            border: none;
        }
    """,
}


def get_theme_aware_text_browser_qss() -> tuple[str, str]:
    """Return (light_qss, dark_qss) for ThemeAwareTextBrowser."""
    return (
        THEME_AWARE_TEXT_BROWSER_STYLES["light"],
        THEME_AWARE_TEXT_BROWSER_STYLES["dark"],
    )


# Pivot Item 样式配置
# 注意：{theme_color} 需要在运行时替换
PIVOT_ITEM_STYLES = {
    "light": """
        PivotItem[pivotItem="true"] {{
            background-color: transparent;
            border: none;
            padding: 8px 16px;
            font-family: 'Segoe UI', 'Microsoft YaHei', 'PingFang SC';
            font-size: 14px;
            font-weight: 400;
            text-align: center;
            color: rgba(0, 0, 0, 0.7);
        }}
        PivotItem[pivotItem="true"]:hover {{
            color: rgba(0, 0, 0, 0.9);
        }}
        PivotItem[pivotItem="true"][selected="true"] {{
            color: {theme_color};
        }}
    """,
    "dark": """
        PivotItem[pivotItem="true"] {{
            background-color: transparent;
            border: none;
            padding: 8px 16px;
            font-family: 'Segoe UI', 'Microsoft YaHei', 'PingFang SC';
            font-size: 14px;
            font-weight: 400;
            text-align: center;
            color: rgba(255, 255, 255, 0.7);
        }}
        PivotItem[pivotItem="true"]:hover {{
            color: rgba(255, 255, 255, 0.9);
        }}
        PivotItem[pivotItem="true"][selected="true"] {{
            color: {theme_color};
        }}
    """,
}


def get_pivot_item_qss(theme_color: str) -> tuple[str, str]:
    light_qss = PIVOT_ITEM_STYLES["light"].format(theme_color=theme_color)
    dark_qss = PIVOT_ITEM_STYLES["dark"].format(theme_color=theme_color)
    return light_qss, dark_qss


# SegmentedWidget 样式配置
SEGMENTED_WIDGET_STYLES = {
    "light": """
        SegmentedWidget {{
            background: transparent;
            border: none;
        }}
        SegmentedItem[pivotItem="true"] {{
            padding: 6px 16px;
            font-size: 14px;
            font-weight: 400;
            color: rgba(0, 0, 0, 0.7);
            background: transparent;
            border: none;
        }}
        SegmentedItem[pivotItem="true"]:hover {{
            color: rgba(0, 0, 0, 0.9);
        }}
        SegmentedItem[pivotItem="true"][selected="true"] {{
            color: {theme_color};
            font-weight: bold;
        }}
    """,
    "dark": """
        SegmentedWidget {{
            background: transparent;
            border: none;
        }}
        SegmentedItem[pivotItem="true"] {{
            padding: 6px 16px;
            font-size: 14px;
            font-weight: 400;
            color: rgba(255, 255, 255, 0.7);
            background: transparent;
            border: none;
        }}
        SegmentedItem[pivotItem="true"]:hover {{
            color: rgba(255, 255, 255, 0.9);
        }}
        SegmentedItem[pivotItem="true"][selected="true"] {{
            color: {theme_color};
            font-weight: bold;
        }}
    """,
}


def get_segmented_widget_qss(theme_color: str) -> tuple[str, str]:
    """Return (light_qss, dark_qss) for SegmentedWidget."""
    light_qss = SEGMENTED_WIDGET_STYLES["light"].format(theme_color=theme_color)
    dark_qss = SEGMENTED_WIDGET_STYLES["dark"].format(theme_color=theme_color)
    return light_qss, dark_qss


# 星光加成配置
STARLIGHT_BONUS_NAMES = [
    QT_TRANSLATE_NOOP("CustomizeSettingsModule", "起始之星"),
    QT_TRANSLATE_NOOP("CustomizeSettingsModule", "层积星云"),
    QT_TRANSLATE_NOOP("CustomizeSettingsModule", "星际旅行"),
    QT_TRANSLATE_NOOP("CustomizeSettingsModule", "倾落的流星雨"),
    QT_TRANSLATE_NOOP("CustomizeSettingsModule", "双星商店"),
    QT_TRANSLATE_NOOP("CustomizeSettingsModule", "卫星商店"),
    QT_TRANSLATE_NOOP("CustomizeSettingsModule", "星云的宠爱"),
    QT_TRANSLATE_NOOP("CustomizeSettingsModule", "星芒的引导"),
    QT_TRANSLATE_NOOP("CustomizeSettingsModule", "偶然的彗星"),
    QT_TRANSLATE_NOOP("CustomizeSettingsModule", "全面的可能性"),
]

STARLIGHT_BONUS_COSTS = [10, 10, 20, 20, 30, 30, 40, 40, 50, 60]

STARLIGHT_BONUS_TIPS = [
    {
        "buff": "buff：\n经费+\n卡包+\n饰品+\n刷新+",
        "buff+": "buff+：\n经费+\\yellow{+}\n卡包+\n饰品+\n刷新+",
        "buff++": "buff++：\n经费+\\yellow{+}\n卡包+\n饰品+\n刷新+\\yellow{+}",
    },
    {
        "buff": "buff：\n过层经费+\n售卖经费+",
        "buff+": "buff+：\n过层经费+\\yellow{+}\n售卖经费+\\yellow{+}",
        "buff++": "buff++：\n过层经费+\\yellow{+}\\yellow{+}\n售卖经费+\\yellow{+}\\yellow{+}",
    },
    {
        "buff": "buff：\n卡包+\n卡包刷新+\n人格等级+",
        "buff+": "buff+：\n卡包+\n卡包刷新+\\yellow{+}\n人格等级+\n拼点\\yellow{+}",
        "buff++": "buff++：\n卡包+\n卡包刷新+\\yellow{+}\\yellow{+}\n人格等级+\n拼点\\yellow{+}\\yellow{+}",
    },
    {
        "buff": "buff：\n经费+\n饰品选择+",
        "buff+": "buff+：\n经费+\\yellow{+}\n饰品选择+\n星芒经费\\yellow{+}",
        "buff++": "buff++：\n经费+\\yellow{+}\\yellow{+}\n饰品选择+\n星芒经费\\yellow{+}",
    },
    {
        "buff": "buff：\n商店饰品+\n战斗经费+\n高级饰品+",
        "buff+": "buff+：\n商店饰品+\n战斗经费+\\yellow{+}\n高级饰品+\n商店经费\\yellow{+}",
        "buff++": "buff++：\n商店饰品+\n战斗经费+\\yellow{+}\\yellow{+}\n高级饰品+\n商店经费\\yellow{+}",
    },
    {
        "buff": "buff：\n关键词刷新+\n初始饰品+",
        "buff+": "buff+：\n关键词刷新+\n初始饰品+\\yellow{+}\n特殊商店\\yellow{+}",
        "buff++": "buff++：\n关键词刷新+\\yellow{+}\n初始饰品+\\yellow{+}\n特殊商店\\yellow{+}\\yellow{+}",
    },
    {
        "buff": "buff：\n初始等级+\n过层等级+",
        "buff+": "buff+：\n初始等级+\n过层等级+\\yellow{+}",
        "buff++": "buff++：\n初始等级+\n六层等级\\yellow{+}\n过层等级+\\yellow{+}",
    },
    {
        "buff": "buff：\n速度+\n拼点+\n伤害+\n守护+",
        "buff+": "buff+：\n速度+\\yellow{+}\n拼点+\n伤害+\n守护+",
        "buff++": "buff++：\n速度+\\yellow{+}\\yellow{+}\n拼点+\n伤害+\n守护+",
    },
    {
        "buff": "buff：\n商店饰品+\n三层饰品+\n合成饰品+",
        "buff+": "buff+：\n商店饰品+\\yellow{+}\n三层饰品+\n五层饰品\\yellow{+}\n合成饰品+",
        "buff++": "buff++：\n商店饰品+\\yellow{+}\n三层饰品+\n五层饰品\\yellow{+}\n七层饰品\\yellow{+}\n合成饰品+\\yellow{+}",
    },
    {
        "buff": "buff：\n卡包+\n饰品选择+\n关键词饰品+\n黯淡残影+",
        "buff+": "buff+：\n饰品选择+\n关键词饰品+\\yellow{+}\n黯淡残影+\n微茫残影\\yellow{+}",
        "buff++": "buff++：\n卡包+\n饰品选择+\n关键词饰品+\\yellow{+}\\yellow{+}\n黯淡残影+\n微茫残影\\yellow{+}\n闪耀残影\\yellow{+}",
    },
]

STARLIGHT_COST_LABEL_STYLES = {
    "light": """
        QLabel {
            background: transparent;
            border: none;
            color: rgba(0, 0, 0, 0.82);
            font-size: 11px;
            font-weight: 500;
        }
    """,
    "dark": """
        QLabel {
            background: transparent;
            border: none;
            color: rgba(255, 255, 255, 0.92);
            font-size: 11px;
            font-weight: 500;
        }
    """,
}

STARLIGHT_TOOLTIP_STYLES = {
    "light": """
        QLabel {
            background-color: rgb(255, 255, 255);
            border: 1px solid rgba(0, 0, 0, 38);
            border-radius: 6px;
            color: rgba(0, 0, 0, 0.82);
            padding: 6px 8px;
        }
    """,
    "dark": """
        QLabel {
            background-color: rgb(45, 45, 45);
            border: 1px solid rgba(255, 255, 255, 46);
            border-radius: 6px;
            color: rgba(255, 255, 255, 0.92);
            padding: 6px 8px;
        }
    """,
}

STARLIGHT_LEVEL_BUTTON_STYLES = {
    "light": """
        QPushButton {
            border: none;
            background: transparent;
            padding: 5px 6px;
            min-height: 32px;
            color: rgba(0, 0, 0, 0.82);
            font-size: 13px;
        }
        QPushButton:hover {
            background: transparent;
        }
        QPushButton:checked {
            color: rgba(0, 0, 0, 0.82);
        }
        QPushButton[segment="left"] {
            padding-right: 24px;
        }
    """,
    "dark": """
        QPushButton {
            border: none;
            background: transparent;
            padding: 5px 6px;
            min-height: 32px;
            color: rgba(255, 255, 255, 0.92);
            font-size: 13px;
        }
        QPushButton:hover {
            background: transparent;
        }
        QPushButton:checked {
            color: rgba(255, 255, 255, 0.92);
        }
        QPushButton[segment="left"] {
            padding-right: 24px;
        }
    """,
}

STARLIGHT_SELECTOR_STYLES = {
    "light": "StarlightLevelSelector { background: transparent; }",
    "dark": "StarlightLevelSelector { background: transparent; }",
}

STARLIGHT_PAINT_COLORS = {
    "light": {
        "empty": (120, 120, 120, 20),
        "left": (255, 143, 161, 150),
        "middle": (224, 76, 76, 175),
        "right": (190, 38, 52, 195),
    },
    "dark": {
        "empty": (255, 255, 255, 18),
        "left": (255, 182, 193, 70),
        "middle": (214, 96, 96, 88),
        "right": (170, 32, 44, 130),
    },
}


def get_starlight_cost_label_qss() -> tuple[str, str]:
    return STARLIGHT_COST_LABEL_STYLES["light"], STARLIGHT_COST_LABEL_STYLES["dark"]


def get_starlight_tooltip_qss() -> tuple[str, str]:
    return STARLIGHT_TOOLTIP_STYLES["light"], STARLIGHT_TOOLTIP_STYLES["dark"]


def get_starlight_level_button_qss() -> tuple[str, str]:
    return STARLIGHT_LEVEL_BUTTON_STYLES["light"], STARLIGHT_LEVEL_BUTTON_STYLES["dark"]


def get_starlight_selector_qss() -> tuple[str, str]:
    return STARLIGHT_SELECTOR_STYLES["light"], STARLIGHT_SELECTOR_STYLES["dark"]


def get_starlight_paint_colors(is_dark: bool) -> dict[str, QColor]:
    style = STARLIGHT_PAINT_COLORS["dark"] if is_dark else STARLIGHT_PAINT_COLORS["light"]
    default_line_color = QColor(120, 120, 120, 105)
    return {
        "border": default_line_color,
        "divider": default_line_color,
        "empty": QColor(*style["empty"]),
        "left": QColor(*style["left"]),
        "middle": QColor(*style["middle"]),
        "right": QColor(*style["right"]),
    }


# 公告板侧边栏样式配置
ANNOUNCEMENT_SIDEBAR_STYLES = {
    "dark": """
        QFrame#announcementSidebar {
            background-color: rgba(45, 45, 45, 1);
            border: none;
            border-top-left-radius: 8px;
            border-bottom-left-radius: 8px;
        }
        QLabel#sidebarTitle {
            color: rgba(255, 255, 255, 0.95);
            font-size: 16px;
            font-weight: bold;
            padding: 0px;
        }
    """,
    "light": """
        QFrame#announcementSidebar {
            background-color: rgba(245, 245, 245, 1);
            border: none;
            border-right: 1px solid rgba(0, 0, 0, 0.1);
            border-top-left-radius: 8px;
            border-bottom-left-radius: 8px;
        }
        QLabel#sidebarTitle {
            color: rgba(0, 0, 0, 0.9);
            font-size: 16px;
            font-weight: bold;
            padding: 0px;
        }
    """,
}


def get_announcement_sidebar_qss() -> tuple[str, str]:
    """返回 (light_qss, dark_qss) 用于公告板侧边栏"""
    return ANNOUNCEMENT_SIDEBAR_STYLES["light"], ANNOUNCEMENT_SIDEBAR_STYLES["dark"]


# 公告板列表项样式配置
ANNOUNCEMENT_LIST_STYLES = {
    "dark": """
        ListWidget {
            background-color: transparent;
            border: none;
            outline: 0px;
        }
        ListWidget::item {
            color: rgba(255, 255, 255, 0.85);
            background-color: transparent;
            border-left: 3px solid transparent;
            padding: 12px 15px;
            margin: 2px 5px;
            border-radius: 4px;
        }
        ListWidget::item:hover {
            background-color: rgba(255, 255, 255, 0.08);
        }
        ListWidget::item:selected {
            background-color: rgba(255, 255, 255, 0.12);
            border-left: 3px solid #0078d4;
        }
    """,
    "light": """
        ListWidget {
            background-color: transparent;
            border: none;
            outline: 0px;
        }
        ListWidget::item {
            color: rgba(0, 0, 0, 0.85);
            background-color: transparent;
            border-left: 3px solid transparent;
            padding: 12px 15px;
            margin: 2px 5px;
            border-radius: 4px;
        }
        ListWidget::item:hover {
            background-color: rgba(0, 0, 0, 0.05);
        }
        ListWidget::item:selected {
            background-color: rgba(0, 0, 0, 0.08);
            border-left: 3px solid #0078d4;
        }
    """,
}


def get_announcement_list_qss() -> tuple[str, str]:
    """返回 (light_qss, dark_qss) 用于公告板列表"""
    return ANNOUNCEMENT_LIST_STYLES["light"], ANNOUNCEMENT_LIST_STYLES["dark"]


ANNOUNCEMENT_CONTENT_STYLES = {
    "dark": """
        QTextBrowser {
            color: rgb(201, 209, 217);
            background-color: rgba(28, 28, 28, 1);
            border: none;
            padding: 20px;
            selection-background-color: rgba(88, 166, 255, 0.3);
            selection-color: rgb(255, 255, 255);
        }
    """,
    "light": """
        QTextBrowser {
            color: rgb(36, 41, 47);
            background-color: rgba(255, 255, 255, 1);
            border: none;
            padding: 20px;
            selection-background-color: rgba(0, 120, 212, 0.3);
            selection-color: rgb(0, 0, 0);
        }
    """,
}


def get_announcement_content_qss() -> tuple[str, str]:
    """返回 (light_qss, dark_qss) 用于公告板内容区域"""
    return ANNOUNCEMENT_CONTENT_STYLES["light"], ANNOUNCEMENT_CONTENT_STYLES["dark"]


# 公告板底部按钮区域样式
ANNOUNCEMENT_FOOTER_STYLES = {
    "dark": """
        QFrame#announcementFooter {
            background-color: rgba(45, 45, 45, 1);
            border-top: 1px solid rgba(255, 255, 255, 0.1);
            border-bottom-right-radius: 8px;
        }
    """,
    "light": """
        QFrame#announcementFooter {
            background-color: rgba(250, 250, 250, 1);
            border-top: 1px solid rgba(0, 0, 0, 0.1);
            border-bottom-right-radius: 8px;
        }
    """,
}


def get_announcement_footer_qss() -> tuple[str, str]:
    """返回 (light_qss, dark_qss) 用于公告板底部区域"""
    return ANNOUNCEMENT_FOOTER_STYLES["light"], ANNOUNCEMENT_FOOTER_STYLES["dark"]


# 设置界面样式配置
SETTING_INTERFACE_STYLES = {
    "dark": """
        SettingInterface, #scrollWidget, QWidget {
            background-color: rgb(28, 28, 28);
        }
        QScrollArea, QScrollArea > QWidget, QScrollArea > QWidget > QWidget {
            background-color: rgb(28, 28, 28);
            border: none;
        }
        /* 导航栏背景 (Navigation Bar Background) */
        #navFrame {
            background-color: rgb(28, 28, 28);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 8px;
        }
        /* 项目背景与字体颜色 (Item Background and Font Color - Normal State) */
        #navFrame QPushButton {
            text-align: left;
            padding: 8px 12px;
            border-radius: 6px;
            color: rgba(255, 255, 255, 0.7); /* 项目默认字体颜色 */
            margin: 0px;
            background-color: transparent; /* 项目默认背景透明 */
            border: none;
        }
        /* 项目背景与字体颜色 (Item Background and Font Color - Hover State) */
        #navFrame QPushButton:hover {
            background-color: rgba(255, 255, 255, 0.08); /* 悬停时的项目背景色 */
            color: rgba(255, 255, 255, 0.9); /* 悬停时的项目字体颜色 */
        }
        /* 项目背景与字体颜色 (Item Background and Font Color - Checked/Active State) */
        #navFrame QPushButton:checked {
            background-color: rgba(255, 255, 255, 0.12); /* 选中时的项目背景色 */
            color: rgb(255, 255, 255); /* 选中时的项目字体颜色 */
            font-weight: bold;
        }
    """,
    "light": """
        SettingInterface, #scrollWidget, QWidget {
            background-color: rgb(255, 255, 255);
        }
        QScrollArea, QScrollArea > QWidget, QScrollArea > QWidget > QWidget {
            background-color: rgb(255, 255, 255);
            border: none;
        }
        /* 导航栏背景 (Navigation Bar Background) */
        #navFrame {
            background-color: rgb(255, 255, 255);
            border: 1px solid rgba(0, 0, 0, 0.08);
            border-radius: 8px;
        }
        /* 项目背景与字体颜色 (Item Background and Font Color - Normal State) */
        #navFrame QPushButton {
            text-align: left;
            padding: 8px 12px;
            border-radius: 6px;
            color: rgba(0, 0, 0, 0.6); /* 项目默认字体颜色 */
            margin: 0px;
            background-color: transparent; /* 项目默认背景透明 */
            border: none;
        }
        /* 项目背景与字体颜色 (Item Background and Font Color - Hover State) */
        #navFrame QPushButton:hover {
            background-color: rgba(0, 0, 0, 0.06); /* 悬停时的项目背景色 */
            color: rgba(0, 0, 0, 0.85); /* 悬停时的项目字体颜色 */
        }
        /* 项目背景与字体颜色 (Item Background and Font Color - Checked/Active State) */
        #navFrame QPushButton:checked {
            background-color: rgba(0, 0, 0, 0.09); /* 选中时的项目背景色 */
            color: rgb(0, 0, 0); /* 选中时的项目字体颜色 */
            font-weight: bold;
        }
    """,
}


def get_setting_interface_qss() -> tuple[str, str]:
    """返回 (light_qss, dark_qss) 用于设置界面"""
    return SETTING_INTERFACE_STYLES["light"], SETTING_INTERFACE_STYLES["dark"]


def set_border_style(qframe: QFrame, is_dark: bool | None = None, border_radius: int = 5):
    """为 QFrame 及子类设置边框样式"""
    if is_dark is None:
        is_dark = isDarkTheme()
    style = BORDER_STYLE["dark"] if is_dark else BORDER_STYLE["light"]
    style = style.format(radius=border_radius)
    qss = f"{qframe.__class__.__name__} {{{style}}}"
    qframe.setStyleSheet(qss)
