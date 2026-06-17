from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from qfluentwidgets import isDarkTheme, qconfig, themeColor

from app.base_combination import CheckBoxWithButton


class DragHandleButton(QPushButton):
    """拖拽手柄按钮，用于发起拖拽排序"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(20, 20)
        self.setText("⠿")
        self.setFlat(True)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._apply_style()
        self.pressed.connect(self._on_pressed)
        self.released.connect(self._on_released)
        qconfig.themeChangedFinished.connect(self._apply_style)

    def _apply_style(self):
        is_dark = isDarkTheme()
        color = "rgba(255,255,255,120)" if is_dark else "rgba(0,0,0,120)"
        self.setStyleSheet(
            f"""
            DragHandleButton {{
                border: none;
                background: transparent;
                color: {color};
                font-size: 14px;
                padding: 0px;
            }}
            DragHandleButton:hover {{
                color: {themeColor().name()};
            }}
            """
        )

    def _on_pressed(self):
        self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def _on_released(self):
        self.setCursor(Qt.CursorShape.OpenHandCursor)


class DraggableTaskItem(QFrame):
    """包装单个 CheckBoxWithButton，左侧附加拖拽手柄"""

    def __init__(self, task_widget: CheckBoxWithButton, parent=None):
        super().__init__(parent)
        self.task_widget = task_widget
        self.task_name: str = task_widget.box.config_name

        self.hBoxLayout = QHBoxLayout(self)
        self.hBoxLayout.setContentsMargins(0, 0, 0, 0)
        self.hBoxLayout.setSpacing(4)

        self.drag_handle = DragHandleButton(self)
        self.hBoxLayout.addWidget(self.drag_handle)
        self.hBoxLayout.addWidget(self.task_widget)


class DraggableTaskList(QWidget):
    """支持拖拽排序的垂直任务列表

    信号:
        order_changed(list[str]): 顺序变更时发出，传递新的任务名称顺序
    """

    order_changed = Signal(list)

    def __init__(
        self,
        task_items: list[CheckBoxWithButton],
        initial_order: list[str],
        parent=None,
    ):
        super().__init__(parent)

        # 名称 -> CheckBoxWithButton 查找表
        self._task_map: dict[str, CheckBoxWithButton] = {}
        for item in task_items:
            name = item.box.config_name
            self._task_map[name] = item

        # 主垂直布局
        self.vBoxLayout = QVBoxLayout(self)
        self.vBoxLayout.setContentsMargins(0, 0, 0, 0)
        self.vBoxLayout.setSpacing(10)

        # DraggableTaskItem 包装，按名称索引
        self._item_map: dict[str, DraggableTaskItem] = {}

        # 过滤 initial_order 中的未知名称，补全缺失项，防止配置损坏导致崩溃或丢失
        valid_names = set(self._task_map.keys())
        filtered_order = [n for n in initial_order if n in valid_names]
        missing = [n for n in valid_names if n not in set(filtered_order)]
        self._order: list[str] = filtered_order + missing

        # 按计算后的顺序创建 DraggableTaskItem 包装
        for name in self._order:
            widget = self._task_map[name]
            item = DraggableTaskItem(widget, self)
            self._item_map[name] = item
            self.vBoxLayout.addWidget(item)
            item.drag_handle.pressed.connect(self._start_drag_for_item)

        # 拖拽状态
        self._dragging: bool = False
        self._drag_source_index: int = -1
        self._drag_source_name: str = ""

        # 拖拽指示线：显示插入位置的细色线
        self._drag_indicator = QFrame(self)
        self._drag_indicator.setFixedHeight(2)
        self._apply_indicator_style()
        self._drag_indicator.setVisible(False)

        self.setMouseTracking(True)
        qconfig.themeChangedFinished.connect(self._apply_indicator_style)

    def _apply_indicator_style(self):
        self._drag_indicator.setStyleSheet(
            f"background-color: {themeColor().name()};"
        )

    # ── 拖拽发起 ──────────────────────────────────────────────────

    def _start_drag_for_item(self):
        """拖拽手柄按下时，定位源项并开始拖拽"""
        handle = self.sender()
        parent = handle.parent()
        if not isinstance(parent, DraggableTaskItem):
            return

        source_name = parent.task_name
        if source_name not in self._order:
            return

        self._dragging = True
        self._drag_source_name = source_name
        self._drag_source_index = self._order.index(source_name)

        # 使用 QGraphicsOpacityEffect 实现拖拽项半透明
        source_item = self._item_map[source_name]
        self._source_opacity = QGraphicsOpacityEffect(source_item)
        self._source_opacity.setOpacity(0.4)
        source_item.setGraphicsEffect(self._source_opacity)

        self.grabMouse()

    # ── 拖拽中断保护 ──────────────────────────────────────────────

    def _cancel_drag(self):
        """取消拖拽状态，释放鼠标捕获，恢复视觉"""
        if not self._dragging:
            return
        self.releaseMouse()
        self._drag_indicator.setVisible(False)
        source_item = self._item_map.get(self._drag_source_name)
        if source_item:
            source_item.setGraphicsEffect(None)
        self._dragging = False
        self._drag_source_index = -1
        self._drag_source_name = ""

    def focusOutEvent(self, event):
        # 窗口失焦时取消拖拽，防止鼠标永久被捕获
        self._cancel_drag()
        super().focusOutEvent(event)

    def hideEvent(self, event):
        # 隐藏时取消拖拽
        self._cancel_drag()
        super().hideEvent(event)

    # ── 鼠标事件 ──────────────────────────────────────────────────

    def mouseMoveEvent(self, event):
        if not self._dragging:
            super().mouseMoveEvent(event)
            return

        target_index = self._index_from_y(event.position().toPoint().y())

        if target_index is not None and target_index != self._drag_source_index:
            self._show_drag_indicator(target_index)
        else:
            self._drag_indicator.setVisible(False)

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if not self._dragging:
            super().mouseReleaseEvent(event)
            return

        self.releaseMouse()

        target_index = self._index_from_y(event.position().toPoint().y())

        # 清理视觉状态
        self._drag_indicator.setVisible(False)
        source_item = self._item_map.get(self._drag_source_name)
        if source_item:
            source_item.setGraphicsEffect(None)

        # 位置变更时执行重排
        if (
            target_index is not None
            and target_index != self._drag_source_index
            and 0 <= self._drag_source_index < len(self._order)
        ):
            self._perform_reorder(self._drag_source_index, target_index)

        self._dragging = False
        self._drag_source_index = -1
        self._drag_source_name = ""

        super().mouseReleaseEvent(event)

    # ── 索引计算 ──────────────────────────────────────────────────

    def _index_from_y(self, y: int) -> int | None:
        """根据 Y 坐标计算插入索引，返回 None 表示列表为空"""
        if not self._order:
            return None

        n = len(self._order)
        centers = []
        for name in self._order:
            item = self._item_map[name]
            rect = item.geometry()
            centers.append(rect.top() + rect.height() // 2)

        for i in range(n):
            if y < centers[i]:
                return i
        return n

    # ── 拖拽指示线 ────────────────────────────────────────────────

    def _show_drag_indicator(self, target_index: int):
        """在目标插入位置显示指示线"""
        n = len(self._order)
        if target_index <= 0:
            # 指示线放在第一个项顶部边缘，避免 y 为负被裁剪
            first_item = self._item_map[self._order[0]]
            y = first_item.geometry().top()
        elif target_index >= n:
            # 指示线放在最后一个项底部边缘，避免 y 超出 widget 被裁剪
            last_item = self._item_map[self._order[-1]]
            y = last_item.geometry().bottom() - 2
        else:
            above_item = self._item_map[self._order[target_index - 1]]
            below_item = self._item_map[self._order[target_index]]
            y = (above_item.geometry().bottom() + below_item.geometry().top()) // 2

        self._drag_indicator.setGeometry(0, y, self.width(), 2)
        self._drag_indicator.raise_()
        self._drag_indicator.setVisible(True)

    # ── 重排逻辑 ──────────────────────────────────────────────────

    def _perform_reorder(self, from_index: int, to_index: int):
        """将 from_index 处的项移动到 to_index"""
        name = self._order.pop(from_index)
        if to_index > from_index:
            to_index -= 1
        self._order.insert(to_index, name)

        # 暂时移除所有 widget 后按新顺序重新添加
        for _ in range(self.vBoxLayout.count()):
            w = self.vBoxLayout.itemAt(0).widget()
            if w is not None:
                self.vBoxLayout.removeWidget(w)

        for i, n in enumerate(self._order):
            self.vBoxLayout.insertWidget(i, self._item_map[n])

        self.order_changed.emit(list(self._order))

    # ── 公开接口 ──────────────────────────────────────────────────

    def get_current_order(self) -> list[str]:
        """返回当前任务名称的显示顺序"""
        return list(self._order)

    def reorder(self, new_order: list[str]):
        """按 new_order 编程式重排，集合不同则忽略"""
        if set(new_order) != set(self._order):
            return

        self._order = list(new_order)

        for _ in range(self.vBoxLayout.count()):
            w = self.vBoxLayout.itemAt(0).widget()
            if w is not None:
                self.vBoxLayout.removeWidget(w)

        for i, name in enumerate(self._order):
            self.vBoxLayout.insertWidget(i, self._item_map[name])

        self.order_changed.emit(list(self._order))
