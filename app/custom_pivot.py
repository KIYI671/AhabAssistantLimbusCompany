# coding:utf-8
"""
Custom Pivot component with full-width indicator and bottom divider line
"""
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPainter, QColor, QPen
from PySide6.QtWidgets import QWidget
from qfluentwidgets import Pivot, isDarkTheme, themeColor
from qfluentwidgets.common.color import autoFallbackThemeColor


class FullWidthPivot(Pivot):
    """
    Custom Pivot with:
    - A horizontal divider line at the bottom spanning the full width
    - Full-width indicator under the selected tab (turns blue)
    - Selected tab text turns blue
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._indicatorHeight = 2
        self._dividerHeight = 1
        self._currentIndicatorRect = QRectF()

    def setIndicatorHeight(self, height: int):
        """Set the height of the indicator bar"""
        self._indicatorHeight = height
        self.update()

    def indicatorHeight(self) -> int:
        return self._indicatorHeight

    def _getIndicatorGeometry(self) -> QRectF:
        """
        Calculate full-width indicator geometry.
        Returns a QRectF spanning the entire width of the current tab item.
        """
        item = self.currentItem()
        if not item:
            return QRectF(0, self.height() - self._indicatorHeight, 0, self._indicatorHeight)

        rect = item.geometry()
        # Return full width of the item
        return QRectF(
            rect.x(),
            self.height() - self._indicatorHeight,
            rect.width(),
            self._indicatorHeight
        )

    def setCurrentItem(self, routeKey: str):
        """Override to also update text color for selected/unselected items"""
        super().setCurrentItem(routeKey)
        self._updateItemStyles()
        self._currentIndicatorRect = self._getIndicatorGeometry()
        self.update()

    def _updateItemStyles(self):
        """Update the text color of items based on selection state"""
        currentKey = self.currentRouteKey()
        for key, item in self.items.items():
            if key == currentKey:
                # Selected: use theme color (blue)
                item.setStyleSheet(f"color: {themeColor().name()};")
            else:
                # Unselected: use default color based on theme
                if isDarkTheme():
                    item.setStyleSheet("color: rgba(255, 255, 255, 0.7);")
                else:
                    item.setStyleSheet("color: rgba(0, 0, 0, 0.7);")

    def showEvent(self, e):
        super().showEvent(e)
        self._updateItemStyles()
        self._currentIndicatorRect = self._getIndicatorGeometry()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._currentIndicatorRect = self._getIndicatorGeometry()

    def paintEvent(self, e):
        """Override to draw full-width indicator and bottom divider"""
        # Call the parent's parent paintEvent to skip the default indicator drawing
        QWidget.paintEvent(self, e)

        painter = QPainter(self)
        painter.setRenderHints(QPainter.Antialiasing)

        # Draw bottom divider line across the full width
        self._drawBottomDivider(painter)

        # Draw the full-width indicator for selected tab
        if self.currentItem():
            painter.setPen(Qt.NoPen)
            painter.setBrush(autoFallbackThemeColor(self.lightIndicatorColor, self.darkIndicatorColor))
            painter.drawRoundedRect(self._currentIndicatorRect, 1, 1)

        painter.end()

    def _drawBottomDivider(self, painter: QPainter):
        """Draw horizontal divider line at the bottom spanning full width"""
        # Get divider color based on theme
        if isDarkTheme():
            dividerColor = QColor(255, 255, 255, 30)  # Light divider for dark theme
        else:
            dividerColor = QColor(0, 0, 0, 20)  # Dark divider for light theme

        pen = QPen(dividerColor)
        pen.setWidth(self._dividerHeight)
        painter.setPen(pen)

        # Draw line at the bottom, spanning the full width of the widget
        y = self.height() - self._indicatorHeight
        painter.drawLine(0, y, self.width(), y)
