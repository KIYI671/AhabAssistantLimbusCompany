# 应用 UI 配置
from typing import TYPE_CHECKING

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget
from qfluentwidgets import qconfig

if TYPE_CHECKING:
    from PySide6.QtGui import QPaintEvent
    from qfluentwidgets import SegmentedWidget

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


def segmented_widget_paint_event(
    widget: "SegmentedWidget", e: "QPaintEvent", original_paint_event=None
) -> None:
    """SegmentedWidget 的自定义 paintEvent，实现自定义外框和选中高亮（中间直角，外侧圆角）。

    Args:
        widget: SegmentedWidget 实例
        e: QPaintEvent 事件
        original_paint_event: 原始的 paintEvent 方法（可选）

    使用方式（无需子类化）:
        import types
        original_paint = widget.paintEvent
        widget.paintEvent = types.MethodType(
            lambda w, ev: segmented_widget_paint_event(w, ev, original_paint),
            widget
        )
    """
    from qfluentwidgets import isDarkTheme, themeColor

    # 先调用原始的 paintEvent（如果提供）
    if original_paint_event is not None:
        original_paint_event(e)
    else:
        QWidget.paintEvent(widget, e)

    # 验证 widget 是否有必需的属性
    if not hasattr(widget, "items") or not widget.items:
        return

    painter = QPainter(widget)
    painter.setRenderHints(QPainter.Antialiasing)

    # 1. 绘制外部全局边框 (未选中时的底层)
    is_dark = isDarkTheme()
    if is_dark:
        border_color = QColor(255, 255, 255, 40)
        bg_color = QColor(255, 255, 255, 5)
    else:
        border_color = QColor(0, 0, 0, 30)
        bg_color = QColor(0, 0, 0, 3)

    painter.setPen(QPen(border_color, 1))
    painter.setBrush(bg_color)

    # 整个组件的外框
    rect_all = widget.rect().adjusted(1, 1, -1, -1)
    painter.drawRoundedRect(rect_all, 6.0, 6.0)

    # 绘制内部各项之间的竖直分割线
    items = list(widget.items.values())
    for i in range(len(items) - 1):
        item_rect = items[i].geometry()
        x = item_rect.right()
        painter.drawLine(x, rect_all.top(), x, rect_all.bottom())

    # 2. 如果没有任何选中项，结束
    if not widget.currentItem():
        return

    # 3. 绘制带有主题色的滑动选中框
    c = themeColor()
    painter.setPen(QPen(c, 1.5))
    if is_dark:
        painter.setBrush(QColor(30, 30, 30, 255))
    else:
        painter.setBrush(QColor(255, 255, 255, 255))

    item = widget.currentItem()
    slidex = int(widget.slideAni.value())

    rect_active = QRectF(slidex + 1, 1, item.width() - 2, widget.height() - 2)

    # 为了让中间呈直角，两端呈圆角，利用 QPainterPath 绘制自定义形状
    path = QPainterPath()

    # 判断当前滑块位于哪一项，以决定哪边需要圆角
    # 注意：在滑动动画过程中，它是在项之间平滑过渡的，简单处理只在最左和最右项到达位置时绘制对应圆角
    # 更平滑的做法：通过 x 坐标位置来判断。这里如果在最左边界，左侧圆角；如果在最右边界，右侧圆角

    is_left_edge = slidex <= widget.rect().left() + 2
    is_right_edge = slidex + item.width() >= widget.rect().right() - 2

    if is_left_edge and is_right_edge:
        # 窗口大小可能只有一个项，四个角都是圆角
        path.addRoundedRect(
            rect_active,
            6.0,
            6.0,
        )
    else:
        # 手动绘制路径
        x, y, w, h = (
            rect_active.x(),
            rect_active.y(),
            rect_active.width(),
            rect_active.height(),
        )
        radius = 6.0

        # 左上角
        path.moveTo(x + (radius if is_left_edge else 0), y)

        # 上边缘与右上角
        if is_right_edge:
            path.lineTo(x + w - radius, y)
            path.arcTo(x + w - 2 * radius, y, 2 * radius, 2 * radius, 90, -90)
        else:
            path.lineTo(x + w, y)

        # 右边缘与右下角
        if is_right_edge:
            path.lineTo(x + w, y + h - radius)
            path.arcTo(
                x + w - 2 * radius, y + h - 2 * radius, 2 * radius, 2 * radius, 0, -90
            )
        else:
            path.lineTo(x + w, y + h)

        # 下边缘与左下角
        if is_left_edge:
            path.lineTo(x + radius, y + h)
            path.arcTo(x, y + h - 2 * radius, 2 * radius, 2 * radius, 270, -90)
        else:
            path.lineTo(x, y + h)

        # 左边缘，闭合路径
        path.lineTo(x, y + (radius if is_left_edge else 0))
        if is_left_edge:
            path.arcTo(x, y, 2 * radius, 2 * radius, 180, -90)

    painter.drawPath(path)


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
