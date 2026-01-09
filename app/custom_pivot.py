# coding:utf-8
"""
Custom Pivot component with full-width indicator and bottom divider line

采用自定义PivotItem类的方案：
1. 创建专用的PivotItem类，管理自己的选中状态
2. 使用统一的QSS样式表，通过属性选择器控制样式
3. 父组件只需管理状态，不直接操作样式
"""
from PySide6.QtCore import Qt, QRectF, Signal
from PySide6.QtGui import QPainter, QColor, QPen
from PySide6.QtWidgets import QWidget, QPushButton, QHBoxLayout, QSizePolicy
from qfluentwidgets import Pivot, isDarkTheme, themeColor, qconfig


class PivotItem(QPushButton):
    """自定义Pivot Item，管理自己的选中状态"""
    
    # 选中状态变化信号
    selectedChanged = Signal(bool)
    
    def __init__(self, routeKey: str, text: str, parent=None):
        super().__init__(text, parent)
        self._routeKey = routeKey
        self._selected = False
        
        # 设置基础属性
        self.setCursor(Qt.PointingHandCursor)
        self.setProperty("pivotItem", "true")
        self.setProperty("selected", "false")  # 初始为未选中
        
        # 应用基础样式
        self._applyBaseStyle()
        
        # 连接点击信号
        self.clicked.connect(self._onClicked)
    
    @property
    def routeKey(self) -> str:
        return self._routeKey
    
    @property
    def isSelected(self) -> bool:
        return self._selected
    
    def setSelected(self, selected: bool, updateStyle=True):
        """设置选中状态"""
        if self._selected == selected:
            return
        
        self._selected = selected
        self.setProperty("selected", "true" if selected else "false")
        
        if updateStyle:
            self._refreshStyle()
        
        # 发射信号
        self.selectedChanged.emit(selected)
    
    def _applyBaseStyle(self):
        """应用基础样式"""
        # 设置基础布局和大小策略
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        # 应用样式表（只包含基础样式，状态样式由QSS属性选择器控制）
        baseStyle = """
        QPushButton[pivotItem="true"] {
            background-color: transparent;
            border: none;
            padding: 8px 16px;
            font-size: 14px;
            font-weight: 400;
            text-align: center;
        }
        
        QPushButton[pivotItem="true"]:hover {
            background-color: rgba(0, 120, 212, 0.1);
        }
        """
        self.setStyleSheet(baseStyle)
    
    def _refreshStyle(self):
        """刷新样式以应用属性变化"""
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()
    
    def _onClicked(self):
        """点击时发送选中请求"""
        if not self._selected:
            # 通过父组件通知点击事件
            parent = self.parent()
            if parent and hasattr(parent, 'itemClicked'):
                parent.itemClicked(self._routeKey)


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
        
        # 重新设置现有items的属性
        self._syncItemsProperties()
    
    def _applyUnifiedQss(self):
        """应用统一的QSS样式表"""
        # 获取主题颜色
        selected_color = themeColor().name()
        
        if isDarkTheme():
            unselected_color = "rgba(255, 255, 255, 0.7)"
        else:
            unselected_color = "rgba(0, 0, 0, 0.7)"
        
        # 统一的QSS样式表，使用属性选择器
        qss = f"""
        /* 未选中状态 */
        QPushButton[pivotItem="true"][selected="false"] {{
            color: {unselected_color};
        }}
        
        /* 选中状态 - 使用主题色 */
        QPushButton[pivotItem="true"][selected="true"] {{
            color: {selected_color};
        }}
        
        /* 悬停效果 */
        QPushButton[pivotItem="true"]:hover {{
            background-color: {selected_color}15;
        }}
        """
        
        self.setStyleSheet(qss)
    
    def _updateTheme(self):
        """主题变化时更新样式"""
        self._applyUnifiedQss()
        self.update()
    
    def createItem(self, routeKey: str, text: str) -> QPushButton:
        """重写创建item的方法，返回自定义PivotItem"""
        # 创建自定义PivotItem
        item = PivotItem(routeKey, text, self)
        
        # 连接选中变化信号
        item.selectedChanged.connect(lambda selected, key=routeKey: 
                                     self._onItemSelectedChanged(key, selected))
        
        return item
    
    def insertItem(self, index: int, routeKey: str, text: str, onClick=None, icon=None):
        """重写插入item的方法"""
        # 创建自定义PivotItem
        item = self.createItem(routeKey, text)
        
        # 添加到items字典
        self.items[routeKey] = item
        
        # 添加到布局
        layout = self.layout()
        if not layout:
            layout = QHBoxLayout(self)
            self.setLayout(layout)
            
        if index < 0:
            layout.addWidget(item)
        else:
            layout.insertWidget(index, item)
            
        # 处理点击事件
        if onClick:
            item.clicked.connect(onClick)
            
        # 初始化选中状态
        if hasattr(item, 'setSelected'):
            item.setSelected(routeKey == self.currentRouteKey(), updateStyle=False)
        
        return item
        
    def itemClicked(self, routeKey: str):
        """处理item点击"""
        if routeKey != self.currentRouteKey():
            self.setCurrentItem(routeKey)
    
    def _onItemSelectedChanged(self, routeKey: str, selected: bool):
        """处理item选中状态变化"""
        if selected:
            # 更新其他item的选中状态
            for key, item in self.items.items():
                if key != routeKey and hasattr(item, 'setSelected'):
                    item.setSelected(False, updateStyle=True)
            
            # 调用父类的setCurrentItem
            super().setCurrentItem(routeKey)
            
            # 更新指示器位置
            self._currentIndicatorRect = self._getIndicatorGeometry()
            self.update()
    
    def setCurrentItem(self, routeKey: str):
        """重写设置当前item的方法"""
        # 更新所有item的选中状态
        for key, item in self.items.items():
            if hasattr(item, 'setSelected'):
                item.setSelected(key == routeKey, updateStyle=True)
        
        # 调用父类方法
        super().setCurrentItem(routeKey)
        
        # 更新指示器位置
        self._currentIndicatorRect = self._getIndicatorGeometry()
        self.update()
    
    def _syncItemsProperties(self):
        """同步现有items的属性"""
        currentKey = self.currentRouteKey()
        
        for key, item in self.items.items():
            if hasattr(item, 'setSelected'):
                item.setSelected(key == currentKey, updateStyle=False)
                item.setProperty("pivotItem", "true")
    
    def showEvent(self, e):
        super().showEvent(e)
        self._currentIndicatorRect = self._getIndicatorGeometry()
    
    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._currentIndicatorRect = self._getIndicatorGeometry()
    
    # 以下方法保持不变，保持绘图逻辑
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