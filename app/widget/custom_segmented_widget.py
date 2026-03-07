# 自定义 SegmentedWidget 组件
from typing import TYPE_CHECKING

from PySide6.QtCore import QRectF
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from qfluentwidgets import SegmentedWidget, isDarkTheme, setCustomStyleSheet, themeColor

from app.common.ui_config import get_segmented_widget_qss

if TYPE_CHECKING:
    from PySide6.QtGui import QPaintEvent


class CustomSegmentedWidget(SegmentedWidget):
    """自定义 SegmentedWidget，带有圆角外框和选中高亮效果。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._apply_style()

    def _apply_style(self):
        """应用自定义 QSS 样式。"""
        color = themeColor().name()
        light_qss, dark_qss = get_segmented_widget_qss(color)
        setCustomStyleSheet(self, light_qss, dark_qss)

    def paintEvent(self, e: "QPaintEvent"):
        """自定义绘制：外框 + 分割线 + 选中高亮滑块。"""
        # 先调用父类的 paintEvent（保留动画等行为）
        super().paintEvent(e)

        # 验证是否有项目
        if not hasattr(self, "items") or not self.items:
            return

        painter = QPainter(self)
        painter.setRenderHints(QPainter.Antialiasing)

        is_dark = isDarkTheme()
        border_color = QColor(255, 255, 255, 40) if is_dark else QColor(0, 0, 0, 30)
        bg_color = QColor(255, 255, 255, 5) if is_dark else QColor(0, 0, 0, 3)

        # 1. 绘制外框
        painter.setPen(QPen(border_color, 1))
        painter.setBrush(bg_color)
        rect_all = self.rect().adjusted(1, 1, -1, -1)
        painter.drawRoundedRect(rect_all, 6.0, 6.0)

        # 2. 绘制分割线
        items = list(self.items.values())
        for i in range(len(items) - 1):
            item_rect = items[i].geometry()
            x = item_rect.right()
            painter.drawLine(x, rect_all.top(), x, rect_all.bottom())

        # 3. 绘制选中高亮滑块
        if not self.currentItem():
            return

        c = themeColor()
        painter.setPen(QPen(c, 1.5))
        painter.setBrush(QColor(30, 30, 30, 255) if is_dark else QColor(255, 255, 255, 255))

        item = self.currentItem()
        slidex = int(self.slideAni.value())
        rect_active = QRectF(slidex + 1, 1, item.width() - 2, self.height() - 2)

        # 判断边缘位置
        is_left_edge = slidex <= self.rect().left() + 2
        is_right_edge = slidex + item.width() >= self.rect().right() - 2

        path = QPainterPath()
        radius = 6.0

        if is_left_edge and is_right_edge:
            path.addRoundedRect(rect_active, radius, radius)
        else:
            x, y, w, h = rect_active.x(), rect_active.y(), rect_active.width(), rect_active.height()
            # 手动构建路径：左边缘圆角，右边缘直角（或反之）
            path.moveTo(x + (radius if is_left_edge else 0), y)

            if is_right_edge:
                path.lineTo(x + w - radius, y)
                path.arcTo(x + w - 2 * radius, y, 2 * radius, 2 * radius, 90, -90)
                path.lineTo(x + w, y + h - radius)
                path.arcTo(x + w - 2 * radius, y + h - 2 * radius, 2 * radius, 2 * radius, 0, -90)
            else:
                path.lineTo(x + w, y)
                path.lineTo(x + w, y + h)

            if is_left_edge:
                path.lineTo(x + radius, y + h)
                path.arcTo(x, y + h - 2 * radius, 2 * radius, 2 * radius, 270, -90)
                path.lineTo(x, y + radius)
                path.arcTo(x, y, 2 * radius, 2 * radius, 180, -90)
            else:
                path.lineTo(x, y + h)
                path.lineTo(x, y)

        painter.drawPath(path)
