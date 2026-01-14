# coding:utf-8
"""
Custom Pivot component with full-width indicator and bottom divider line

采用自定义PivotItem类的方案：
1. 创建专用的PivotItem类，管理自己的选中状态
2. 使用统一的QSS样式表，通过属性选择器控制样式
3. 父组件只需管理状态，不直接操作样式
"""
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPainter, QColor, QPen
from PySide6.QtWidgets import QWidget, QPushButton, QHBoxLayout, QSizePolicy
from qfluentwidgets import Pivot, isDarkTheme, themeColor, qconfig


class PivotItem(QPushButton):
    """自定义Pivot Item，管理自己的选中状态"""
    
    def __init__(self, routeKey: str, text: str, parent=None):
        super().__init__(text, parent)
        self._routeKey = routeKey
        self._selected = False
        
        # 设置基础属性
        self.setCursor(Qt.PointingHandCursor)
        self.setProperty("pivotItem", "true")
        self.setProperty("selected", "false")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    
    @property
    def routeKey(self) -> str:
        return self._routeKey
    
    @property
    def isSelected(self) -> bool:
        return self._selected
    
    def setSelected(self, selected: bool):
        """设置选中状态"""
        if self._selected == selected:
            return
        
        self._selected = selected
        self.setProperty("selected", "true" if selected else "false")
        
        # 刷新样式
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()


class FullWidthPivot(Pivot):
    """
    Custom Pivot with:
    - 使用自定义PivotItem管理状态
    - 全宽指示器
    - 底部分割线
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._indicatorHeight = 3
        self._dividerHeight = 2
        self._currentIndicatorRect = QRectF()
        
        # 应用统一的QSS样式表
        self._applyUnifiedQss()
        
        # 连接主题变化信号
        qconfig.themeChanged.connect(self._updateTheme)
    
    def _applyUnifiedQss(self):
        """应用统一的QSS样式表"""
        selected_color = themeColor().name()
        unselected_color = "rgba(255, 255, 255, 0.7)" if isDarkTheme() else "rgba(0, 0, 0, 0.7)"
        
        qss = f"""
        QPushButton[pivotItem="true"] {{
            background-color: transparent;
            border: none;
            padding: 8px 16px;
            font-size: 14px;
            font-weight: 400;
            text-align: center;
        }}
        
        QPushButton[pivotItem="true"][selected="false"] {{
            color: {unselected_color};
        }}
        
        QPushButton[pivotItem="true"][selected="true"] {{
            color: {selected_color};
        }}
        """
        self.setStyleSheet(qss)
    
    def _updateTheme(self):
        """主题变化时更新样式"""
        self._applyUnifiedQss()
        self.update()
    
    def createItem(self, routeKey: str, text: str) -> QPushButton:
        """重写创建item的方法，返回自定义PivotItem"""
        item = PivotItem(routeKey, text, self)
        item.clicked.connect(lambda: self._onUiItemClicked(routeKey))
        return item
    
    def insertItem(self, index: int, routeKey: str, text: str, onClick=None, icon=None):
        """重写插入item的方法"""
        item = self.createItem(routeKey, text)
        self.items[routeKey] = item
        
        layout = self.layout()
        if not layout:
            layout = QHBoxLayout(self)
            self.setLayout(layout)
            
        if index < 0:
            layout.addWidget(item)
        else:
            layout.insertWidget(index, item)
            
        if onClick:
            item.clicked.connect(onClick)
            
        item.setSelected(routeKey == self.currentRouteKey())
        return item
        
    def _onUiItemClicked(self, routeKey: str):
        """处理UI点击事件"""
        if routeKey != self.currentRouteKey():
            self.setCurrentItem(routeKey)
    def setCurrentItem(self, routeKey: str):
        """重写设置当前item的方法"""
        for key, item in self.items.items():
            item.setSelected(key == routeKey)
        
        super().setCurrentItem(routeKey)
        self._updateIndicator()

    def _updateIndicator(self):
        """更新指示器位置及重绘"""
        self._currentIndicatorRect = self._getIndicatorGeometry()
        self.update()
    
    def showEvent(self, e):
        super().showEvent(e)
        self._updateIndicator()
    
    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._updateIndicator()
    
    def _getIndicatorGeometry(self) -> QRectF:
        """计算指示器位置"""
        item = self.currentItem()
        if not item:
            return QRectF(0, self.height() - self._indicatorHeight, 0, self._indicatorHeight)

        rect = item.geometry()
        return QRectF(
            rect.x(),
            self.height() - self._indicatorHeight,
            rect.width(),
            self._indicatorHeight
        )
    
    def paintEvent(self, e):
        """绘制指示器和分割线"""
        QWidget.paintEvent(self, e)

        painter = QPainter(self)
        painter.setRenderHints(QPainter.Antialiasing)

        # 绘制底部分割线
        self._drawBottomDivider(painter)

        # 绘制选中指示器
        if self.currentItem():
            painter.setPen(Qt.NoPen)
            painter.setBrush(themeColor())
            painter.drawRoundedRect(self._currentIndicatorRect, 1, 1)

        painter.end()
    
    def _drawBottomDivider(self, painter: QPainter):
        """绘制底部全宽分割线"""
        if isDarkTheme():
            dividerColor = QColor(255, 255, 255, 30)
        else:
            dividerColor = QColor(0, 0, 0, 20)

        pen = QPen(dividerColor)
        pen.setWidth(self._dividerHeight)
        painter.setPen(pen)

        y = self.height() - self._indicatorHeight
        painter.drawLine(0, y, self.width(), y)
