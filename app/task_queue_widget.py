"""任务列表控件：勾选、拖动排序、添加 / 复制 / 改名 / 删除。

主界面和定时任务编辑框共用。列表直接改传入的任务列表对象（cfg 里的
pydantic 对象），每次改动后发出 changed 信号，由使用方负责保存。
"""

from typing import Callable

from PySide6.QtCore import QT_TRANSLATE_NOOP, QCoreApplication, QModelIndex, QRect, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import QAbstractItemView, QListWidgetItem, QStyleOptionViewItem
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

from module.config.task_queue import (
    TASK_TYPES,
    TaskBase,
    copy_task,
    new_task,
)

CONTEXT = "TaskQueue"

TASK_TYPE_NAMES = {
    "daily": QT_TRANSLATE_NOOP("TaskQueue", "日常任务"),
    "reward": QT_TRANSLATE_NOOP("TaskQueue", "领取奖励"),
    "enkephalin": QT_TRANSLATE_NOOP("TaskQueue", "狂气换体"),
    "mirror": QT_TRANSLATE_NOOP("TaskQueue", "镜牢"),
}

ID_ROLE = Qt.ItemDataRole.UserRole
WINDOW_SETTINGS_ID = "set_windows"


def tr(text: str) -> str:
    return QCoreApplication.translate(CONTEXT, text)


def task_type_name(task_type: str) -> str:
    return tr(TASK_TYPE_NAMES.get(task_type, task_type))


def task_title(task: TaskBase) -> str:
    return task.name or task_type_name(task.type)


def schedule_title(schedule, schedules: list | None = None) -> str:
    """定时任务显示名：自定义名称，否则「定时执行 N」"""
    if schedule.name:
        return schedule.name
    index = 1
    if schedules is not None and schedule in schedules:
        index = schedules.index(schedule) + 1
    elif schedule.id.startswith("autodaily") and schedule.id[len("autodaily") :].isdigit():
        index = int(schedule.id[len("autodaily") :])
    return tr(QT_TRANSLATE_NOOP("TaskQueue", "定时执行 {0}")).format(index)


class TaskItemDelegate(ListItemDelegate):
    """紧凑的一行：勾选框、名称、右侧齿轮（选中项的齿轮用主题色）"""

    ROW_HEIGHT = 30
    CHECK_X = 8
    CHECK_SIZE = 18
    GEAR_SIZE = 16

    def __init__(self, parent):
        super().__init__(parent)
        self.margin = 1
        self.running_id = ""

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

        # 齿轮：表示「点这一行在右边看设置」，选中时用主题色
        gear = QRect(
            rect.right() - 8 - self.GEAR_SIZE, rect.center().y() - self.GEAR_SIZE // 2, self.GEAR_SIZE, self.GEAR_SIZE
        )
        if selected:
            FIF.SETTING.icon(color=QColor(themeColor())).paint(painter, gear)
        else:
            FIF.SETTING.render(painter, gear)

        text_color = QColor(255, 255, 255) if is_dark else QColor(0, 0, 0)
        if index.data(Qt.ItemDataRole.CheckStateRole) == Qt.CheckState.Unchecked:
            text_color.setAlpha(140)
        painter.setPen(text_color)
        painter.setFont(getFont(14, QFont.DemiBold if running else QFont.Normal))
        text_w = max(0, gear.left() - 8 - x)
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
    def tasks(self) -> list:
        return self.get_tasks()

    def find_task(self, task_id: str) -> TaskBase | None:
        return next((task for task in self.tasks() if task.id == task_id), None)

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
    def add_task(self, task_type: str) -> TaskBase:
        task = new_task(task_type)
        self._insert(task, len(self.tasks()))
        return task

    def duplicate_task(self, task_id: str) -> TaskBase | None:
        tasks = self.tasks()
        source = self.find_task(task_id)
        if source is None:
            return None
        clone = copy_task(source)
        clone.name = self._copy_name(task_title(source))
        self._insert(clone, tasks.index(source) + 1)
        return clone

    def _copy_name(self, title: str) -> str:
        titles = {task_title(t) for t in self.tasks()}
        n = 2
        while f"{title} ({n})" in titles:
            n += 1
        return f"{title} ({n})"

    def _insert(self, task: TaskBase, position: int) -> None:
        self.tasks().insert(position, task)
        self.reload(select_id=task.id)
        self.changed.emit()

    def remove_task(self, task_id: str) -> None:
        tasks = self.tasks()
        task = self.find_task(task_id)
        if task is None:
            return
        row = tasks.index(task)
        tasks.remove(task)
        next_id = ""
        if tasks:
            next_id = tasks[min(row, len(tasks) - 1)].id
        self.reload(select_id=next_id)
        if not next_id:
            self.taskSelected.emit("")
        self.changed.emit()

    def move_task(self, task_id: str, offset: int) -> None:
        tasks = self.tasks()
        task = self.find_task(task_id)
        if task is None:
            return
        row = tasks.index(task)
        target = row + offset
        if not 0 <= target < len(tasks):
            return
        tasks.insert(target, tasks.pop(row))
        self.reload(select_id=task_id)
        self.changed.emit()

    def set_all_enabled(self, enabled: bool) -> None:
        for task in self.tasks():
            task.enabled = enabled
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
        task = self.find_task(item.data(ID_ROLE))
        if task is None:
            return
        text = item.text().strip()
        name = None if not text or text == task_type_name(task.type) else text
        if name != task.name:
            task.name = name
            self.blockSignals(True)
            item.setText(task_title(task))
            self.blockSignals(False)
            self.changed.emit()

    def _sync_order(self, *args) -> None:
        tasks = self.tasks()
        by_id = {task.id: task for task in tasks}
        ordered = [by_id[self.item(row).data(ID_ROLE)] for row in range(self.count())]
        if [t.id for t in ordered] != [t.id for t in tasks]:
            tasks[:] = ordered
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
                hit = self.delegate.checkbox_rect(rect).adjusted(-6, -6, 6, 6)
                if hit.contains(e.position().toPoint()):
                    if self._editable:
                        self._toggle(item)
                    e.accept()
                    return
        super().mousePressEvent(e)

    def _toggle(self, item: QListWidgetItem) -> None:
        task = self.find_task(item.data(ID_ROLE))
        if task is None:
            return
        task.enabled = not task.enabled
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
            if not menu.actions():
                pass
            else:
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
