"""任务列表控件：显示任务列表，把勾选、拖动、添加 / 复制 / 改名 / 删除转给 TaskQueue。

主界面和定时任务编辑框共用。数据怎么变由 module.task_queue.operations.TaskQueue
决定；这里只负责画出来、响应鼠标键盘，改动后发出 changed 信号，由使用方保存。
"""

from typing import Callable

from PySide6.QtCore import QT_TRANSLATE_NOOP, QEvent, QModelIndex, QRect, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import QAbstractItemView, QListWidgetItem, QStyleOptionViewItem, QToolTip
from qfluentwidgets import (
    Action,
    ListItemDelegate,
    ListWidget,
    RoundMenu,
    isDarkTheme,
    themeColor,
)
from qfluentwidgets import FluentIcon as FIF
from qfluentwidgets.common.font import getFont

from app.task_queue.texts import task_title, task_type_name, tr
from module.config.task_queue import TASK_TYPES, TaskBase
from module.task_queue.operations import TaskQueue

ID_ROLE = Qt.ItemDataRole.UserRole


class TaskItemDelegate(ListItemDelegate):
    """紧凑的一行：勾选框、名称、右侧齿轮（选中项的齿轮用主题色）"""

    ROW_HEIGHT = 30
    CHECK_X = 8
    CHECK_SIZE = 18
    GEAR_SIZE = 16

    ACTION_SIZE = 16
    ACTION_GAP = 10
    ACTIONS = ("copy", "rename", "delete")

    def __init__(self, parent):
        super().__init__(parent)
        self.margin = 1
        self.running_id = ""
        self.actions_enabled = True  # 运行期间不显示行内操作
        self.hover_action: tuple[int, str] | None = None  # 鼠标所在的行内按钮 (行号, 按钮名)

    def gear_rect(self, row_rect: QRect) -> QRect:
        size = self.GEAR_SIZE + 6
        return QRect(row_rect.right() - 6 - size, row_rect.center().y() - size // 2, size, size)

    def action_rects(self, row_rect: QRect) -> dict[str, QRect]:
        """齿轮左边的行内按钮：复制、重命名、删除"""
        rects = {}
        right = self.gear_rect(row_rect).left() - self.ACTION_GAP
        for name in reversed(self.ACTIONS):
            rects[name] = QRect(
                right - self.ACTION_SIZE,
                row_rect.center().y() - self.ACTION_SIZE // 2,
                self.ACTION_SIZE,
                self.ACTION_SIZE,
            )
            right -= self.ACTION_SIZE + self.ACTION_GAP
        return rects

    def shows_actions(self, index: QModelIndex) -> bool:
        row = index.row()
        return (
            self.actions_enabled
            and index.data(Qt.ItemDataRole.CheckStateRole) is not None
            and (row == self.hoverRow or row in self.selectedRows)
        )

    def sizeHint(self, option, index):
        return QSize(option.rect.width(), self.ROW_HEIGHT)

    def checkbox_rect(self, row_rect: QRect) -> QRect:
        y = row_rect.center().y() - self.CHECK_SIZE // 2
        return QRect(row_rect.x() + self.CHECK_X, y, self.CHECK_SIZE, self.CHECK_SIZE)

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex):
        rect = QRect(option.rect).adjusted(2, self.margin, -2, -self.margin)
        opt = QStyleOptionViewItem(option)
        opt.rect = rect
        row = index.row()
        selected = row in self.selectedRows
        running = bool(self.running_id) and index.data(ID_ROLE) == self.running_id
        is_dark = isDarkTheme()

        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        if running:
            accent = QColor(themeColor())
            accent.setAlpha(40 if is_dark else 28)
            painter.setBrush(accent)
        else:
            c = 255 if is_dark else 0
            alpha = 17 if selected else (12 if self.hoverRow == row else 0)
            painter.setBrush(QColor(c, c, c, alpha))
        painter.drawRoundedRect(rect, 4, 4)

        x = rect.x() + 10
        if index.data(Qt.ItemDataRole.CheckStateRole) is not None:
            opt.rect = QRect(rect.x() - 15 + self.CHECK_X, rect.y(), rect.width(), rect.height())
            self._drawCheckBox(painter, opt, index)
            x = rect.x() + self.CHECK_X + self.CHECK_SIZE + 10

        # 齿轮：表示「点这一行在右边看设置」；选中时是主题色实心底
        gear = self.gear_rect(rect)
        icon_rect = gear.adjusted(3, 3, -3, -3)
        if selected:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(themeColor()))
            painter.drawRoundedRect(gear, 5, 5)
            FIF.SETTING.icon(color=QColor(255, 255, 255)).paint(painter, icon_rect)
        else:
            gear_gray = QColor(160, 160, 160) if is_dark else QColor(120, 120, 120)
            FIF.SETTING.icon(color=gear_gray).paint(painter, icon_rect)

        # 悬停或选中时显示行内操作（同 MAA）：复制用主题色
        text_right = gear.left() - 8
        if self.shows_actions(index):
            rects = self.action_rects(rect)
            icons = {"copy": FIF.COPY, "rename": FIF.EDIT, "delete": FIF.DELETE}
            gray = QColor(160, 160, 160) if is_dark else QColor(120, 120, 120)
            for name, icon in icons.items():
                action_rect = rects[name]
                hovered = self.hover_action == (row, name)
                if hovered:
                    # 悬停：浅色圆角底 + 图标变色（删除用红色）
                    c = 255 if is_dark else 0
                    painter.setPen(Qt.NoPen)
                    painter.setBrush(QColor(c, c, c, 24 if is_dark else 18))
                    painter.drawRoundedRect(action_rect.adjusted(-4, -4, 4, 4), 4, 4)
                # 默认灰色，悬停时用主题色
                color = QColor(themeColor()) if hovered else gray
                icon.icon(color=color).paint(painter, action_rect)
            text_right = rects["copy"].left() - 8

        text_color = QColor(255, 255, 255) if is_dark else QColor(0, 0, 0)
        if index.data(Qt.ItemDataRole.CheckStateRole) == Qt.CheckState.Unchecked:
            text_color.setAlpha(140)
        painter.setPen(text_color)
        painter.setFont(getFont(14, QFont.DemiBold if running else QFont.Normal))
        text_w = max(0, text_right - x)
        title = painter.fontMetrics().elidedText(index.data(Qt.ItemDataRole.DisplayRole) or "", Qt.ElideRight, text_w)
        painter.drawText(QRect(x, rect.y(), text_w, rect.height()), Qt.AlignVCenter, title)
        painter.restore()


class TaskQueueList(ListWidget):
    """任务列表。get_tasks 返回要编辑的那个 list（就地修改，保证 cfg 里的引用不变）"""

    changed = Signal()  # 增删、改名、勾选、排序
    taskSelected = Signal(str)  # 选中项的任务 id，没有选中时为空字符串

    def __init__(self, get_tasks: Callable[[], list], parent=None):
        super().__init__(parent)
        self.get_tasks = get_tasks
        self.hint_text = QT_TRANSLATE_NOOP("TaskQueue", "拖动调整顺序，右键复制或重命名")
        self.empty_text = QT_TRANSLATE_NOOP("TaskQueue", "列表是空的，点击「添加」新建任务")
        self._editable = True
        self._reloading = False

        self.delegate = TaskItemDelegate(self)
        self.setItemDelegate(self.delegate)

        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setDragEnabled(True)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.DefaultContextMenu)
        self.setUniformItemSizes(True)

        self.model().rowsMoved.connect(self._sync_order)
        self.itemChanged.connect(self._on_item_changed)
        self.currentItemChanged.connect(self._on_current_changed)
        self.itemDoubleClicked.connect(self._rename_item)
        self.reload()

    # ----------------------------------------------------------------- data
    @property
    def queue(self) -> TaskQueue:
        return TaskQueue(self.get_tasks(), task_type_name)

    def tasks(self) -> list:
        return self.get_tasks()

    def find_task(self, task_id: str) -> TaskBase | None:
        return self.queue.find(task_id)

    def selected_id(self) -> str:
        item = self.currentItem()
        return item.data(ID_ROLE) if item is not None else ""

    def reload(self, select_id: str | None = None) -> None:
        """按任务列表重建所有行"""
        if select_id is None:
            select_id = self.selected_id()
        self._reloading = True
        self.blockSignals(True)
        self.clear()
        for task in self.tasks():
            self.addItem(self._make_item(task))
        self.blockSignals(False)
        self._reloading = False
        if select_id:
            self.select_task(select_id)

    def refresh(self) -> None:
        """参数变了，只重画摘要和名称"""
        self.blockSignals(True)
        for row in range(self.count()):
            item = self.item(row)
            task = self.find_task(item.data(ID_ROLE))
            if task is not None:
                item.setText(task_title(task))
                item.setCheckState(Qt.CheckState.Checked if task.enabled else Qt.CheckState.Unchecked)
        self.blockSignals(False)
        self.viewport().update()

    def _make_item(self, task: TaskBase) -> QListWidgetItem:
        item = QListWidgetItem(task_title(task))
        item.setData(ID_ROLE, task.id)
        item.setCheckState(Qt.CheckState.Checked if task.enabled else Qt.CheckState.Unchecked)
        flags = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEditable
        if self._editable:
            flags |= Qt.ItemFlag.ItemIsDragEnabled
        item.setFlags(flags)
        item.setSizeHint(QSize(0, TaskItemDelegate.ROW_HEIGHT))
        return item

    def select_task(self, task_id: str) -> bool:
        for row in range(self.count()):
            if self.item(row).data(ID_ROLE) == task_id:
                self.setCurrentRow(row)
                return True
        return False

    def set_running(self, task_id: str) -> None:
        self.delegate.running_id = task_id
        self.viewport().update()

    def set_editable(self, editable: bool) -> None:
        """运行期间禁止编辑，但仍然可以选中查看设置"""
        self._editable = editable
        self.delegate.actions_enabled = editable
        self.setDragEnabled(editable)
        for row in range(self.count()):
            item = self.item(row)
            flags = item.flags()
            if editable:
                flags |= Qt.ItemFlag.ItemIsDragEnabled
            else:
                flags &= ~Qt.ItemFlag.ItemIsDragEnabled
            item.setFlags(flags)
        self.viewport().update()

    # ------------------------------------------------------------- editing
    def _edited(self, select_id: str | None = None) -> None:
        self.reload(select_id=select_id)
        self.changed.emit()

    def add_task(self, task_type: str) -> TaskBase:
        task = self.queue.add(task_type)
        self._edited(task.id)
        return task

    def duplicate_task(self, task_id: str) -> TaskBase | None:
        clone = self.queue.duplicate(task_id)
        if clone is not None:
            self._edited(clone.id)
        return clone

    def remove_task(self, task_id: str) -> None:
        next_id = self.queue.remove(task_id)
        if next_id is None:
            return
        self._edited(next_id)
        if not next_id:
            self.taskSelected.emit("")

    def move_task(self, task_id: str, offset: int) -> None:
        if self.queue.move(task_id, offset):
            self._edited(task_id)

    def set_all_enabled(self, enabled: bool) -> None:
        self.queue.set_all_enabled(enabled)
        self.refresh()
        self.changed.emit()

    def _rename_item(self, item: QListWidgetItem) -> None:
        if not self._editable:
            return
        task = self.find_task(item.data(ID_ROLE))
        if task is None:
            return
        # 编辑框里显示当前名称；清空后恢复为默认名称
        self.blockSignals(True)
        item.setText(task_title(task))
        self.blockSignals(False)
        self.editItem(item)

    def _on_item_changed(self, item: QListWidgetItem) -> None:
        if self._reloading:
            return
        task_id = item.data(ID_ROLE)
        changed = self.queue.rename(task_id, item.text())
        task = self.find_task(task_id)
        if task is not None:
            self.blockSignals(True)
            item.setText(task_title(task))
            self.blockSignals(False)
        if changed:
            self.changed.emit()

    def _sync_order(self, *args) -> None:
        if self.queue.reorder([self.item(row).data(ID_ROLE) for row in range(self.count())]):
            self.changed.emit()

    def _on_current_changed(self, current, previous) -> None:
        self.taskSelected.emit(current.data(ID_ROLE) if current is not None else "")

    def paintEvent(self, e):
        super().paintEvent(e)
        # 列表下方有空位时，在空白处画一行操作提示，不额外占用布局空间
        viewport = self.viewport()
        bottom = 0
        if self.count():
            bottom = self.visualItemRect(self.item(self.count() - 1)).bottom()
        free = viewport.height() - bottom
        if free < 30:
            return
        text = tr(self.empty_text if self.count() == 0 else self.hint_text)
        painter = QPainter(viewport)
        painter.setFont(getFont(12))
        painter.setPen(QColor(255, 255, 255, 110) if isDarkTheme() else QColor(0, 0, 0, 100))
        area = QRect(0, viewport.height() - 26, viewport.width(), 22)
        if self.count() == 0:
            area = viewport.rect()
        painter.drawText(area, Qt.AlignCenter, painter.fontMetrics().elidedText(text, Qt.ElideRight, area.width() - 16))
        painter.end()

    # --------------------------------------------------------------- mouse
    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            item = self.itemAt(e.position().toPoint())
            if item is not None:
                rect = self.visualItemRect(item)
                action = self._action_at(item, e.position().toPoint())
                if action is not None:
                    self._run_action(item, action)
                    e.accept()
                    return
                hit = self.delegate.checkbox_rect(rect).adjusted(-6, -6, 6, 6)
                if hit.contains(e.position().toPoint()):
                    if self._editable:
                        self._toggle(item)
                    e.accept()
                    return
        super().mousePressEvent(e)

    def _action_at(self, item: QListWidgetItem, pos) -> str | None:
        index = self.indexFromItem(item)
        if not self.delegate.shows_actions(index):
            return None
        rect = QRect(self.visualItemRect(item)).adjusted(2, 1, -2, -1)
        for name, action_rect in self.delegate.action_rects(rect).items():
            if action_rect.adjusted(-4, -4, 4, 4).contains(pos):
                return name
        return None

    def _run_action(self, item: QListWidgetItem, action: str) -> None:
        task_id = item.data(ID_ROLE)
        if action == "copy":
            self.duplicate_task(task_id)
        elif action == "rename":
            self.setCurrentItem(item)
            self._rename_item(item)
        elif action == "delete":
            self.remove_task(task_id)

    def viewportEvent(self, e):
        # 行内按钮的悬停提示
        if e.type() == QEvent.Type.ToolTip:
            item = self.itemAt(e.pos())
            action = self._action_at(item, e.pos()) if item is not None else None
            if action is not None:
                tips = {
                    "copy": tr(QT_TRANSLATE_NOOP("TaskQueue", "复制")),
                    "rename": tr(QT_TRANSLATE_NOOP("TaskQueue", "重命名")),
                    "delete": tr(QT_TRANSLATE_NOOP("TaskQueue", "删除")),
                }
                QToolTip.showText(e.globalPos(), tips[action], self)
                return True
            QToolTip.hideText()
            return True
        return super().viewportEvent(e)

    def mouseMoveEvent(self, e):
        super().mouseMoveEvent(e)
        self._update_hover_action(e.position().toPoint())

    def _update_hover_action(self, pos) -> None:
        item = self.itemAt(pos)
        action = self._action_at(item, pos) if item is not None else None
        hover = (self.row(item), action) if action is not None else None
        if hover != self.delegate.hover_action:
            self.delegate.hover_action = hover
            self.viewport().setCursor(Qt.CursorShape.PointingHandCursor if hover else Qt.CursorShape.ArrowCursor)
        self.viewport().update()

    def leaveEvent(self, e):
        super().leaveEvent(e)
        self.delegate.hover_action = None
        self.viewport().unsetCursor()
        self.viewport().update()

    def _toggle(self, item: QListWidgetItem) -> None:
        task_id = item.data(ID_ROLE)
        if not self.queue.toggle(task_id):
            return
        task = self.find_task(task_id)
        self.blockSignals(True)
        item.setCheckState(Qt.CheckState.Checked if task.enabled else Qt.CheckState.Unchecked)
        self.blockSignals(False)
        self.viewport().update()
        self.changed.emit()

    def keyPressEvent(self, e):
        item = self.currentItem()
        if item is not None and self._editable:
            if e.key() == Qt.Key.Key_Space:
                self._toggle(item)
                return
            if e.key() == Qt.Key.Key_Delete:
                self.remove_task(item.data(ID_ROLE))
                return
            if e.key() == Qt.Key.Key_F2:
                self._rename_item(item)
                return
        super().keyPressEvent(e)

    def contextMenuEvent(self, e):
        item = self.itemAt(e.pos())
        menu = RoundMenu(parent=self)
        if item is not None and self._editable:
            self.setCurrentItem(item)
            task_id = item.data(ID_ROLE)
            row = self.row(item)
            rename = Action(FIF.EDIT, tr(QT_TRANSLATE_NOOP("TaskQueue", "重命名")))
            rename.triggered.connect(lambda: self._rename_item(item))
            copy = Action(FIF.COPY, tr(QT_TRANSLATE_NOOP("TaskQueue", "复制")))
            copy.triggered.connect(lambda: self.duplicate_task(task_id))
            up = Action(FIF.UP, tr(QT_TRANSLATE_NOOP("TaskQueue", "上移")))
            up.triggered.connect(lambda: self.move_task(task_id, -1))
            up.setEnabled(row > 0)
            down = Action(FIF.DOWN, tr(QT_TRANSLATE_NOOP("TaskQueue", "下移")))
            down.triggered.connect(lambda: self.move_task(task_id, 1))
            down.setEnabled(row < self.count() - 1)
            delete = Action(FIF.DELETE, tr(QT_TRANSLATE_NOOP("TaskQueue", "删除")))
            delete.triggered.connect(lambda: self.remove_task(task_id))
            menu.addActions([rename, copy])
            menu.addSeparator()
            menu.addActions([up, down])
            menu.addSeparator()
            menu.addAction(delete)
        if self._editable:
            if menu.actions():
                menu.addSeparator()
            add_menu = build_add_menu(self, self.add_task)
            add_menu.setTitle(tr(QT_TRANSLATE_NOOP("TaskQueue", "添加任务")))
            add_menu.setIcon(FIF.ADD)
            menu.addMenu(add_menu)
            menu.exec(e.globalPos())


def build_add_menu(parent, on_add: Callable[[str], object]) -> RoundMenu:
    menu = RoundMenu(parent=parent)
    for task_type in TASK_TYPES:
        action = Action(task_type_name(task_type))
        action.triggered.connect(lambda _=False, t=task_type: on_add(t))
        menu.addAction(action)
    return menu
