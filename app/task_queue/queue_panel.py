"""主界面左侧的任务列表面板：固定的「窗口设置」行、任务列表、添加 / 全选 / 清空按钮。"""

from typing import Callable

from PySide6.QtCore import QT_TRANSLATE_NOOP, QCoreApplication, QSize, Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QListWidgetItem, QVBoxLayout
from qfluentwidgets import DropDownPushButton, ListWidget, PushButton
from qfluentwidgets import FluentIcon as FIF

from app.base_tools import BaseSettingLayout
from app.task_queue.queue_list import TaskItemDelegate, TaskQueueList, build_add_menu

WINDOW_SETTINGS_ID = "set_windows"


class WindowSettingsRow(ListWidget):
    """任务列表上方固定的「窗口设置」行，不能拖动、没有勾选框"""

    selected = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.text = QT_TRANSLATE_NOOP("TaskQueue", "窗口设置")
        delegate = TaskItemDelegate(self)
        self.setItemDelegate(delegate)
        self.delegate = delegate
        item = QListWidgetItem(self.text)
        item.setData(Qt.ItemDataRole.UserRole, WINDOW_SETTINGS_ID)
        item.setSizeHint(QSize(0, TaskItemDelegate.ROW_HEIGHT))
        self.addItem(item)
        self.setFixedHeight(TaskItemDelegate.ROW_HEIGHT + 4)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.itemPressed.connect(lambda _: self.selected.emit())
        self.currentItemChanged.connect(lambda current, _: current is not None and self.selected.emit())

    def retranslateUi(self):
        self.item(0).setText(QCoreApplication.translate("TaskQueue", self.text))


class TaskQueuePanel(BaseSettingLayout):
    """主界面左侧：任务列表（含固定的窗口设置行）、添加按钮、全选 / 清空"""

    itemSelected = Signal(str)  # 任务 id 或 "set_windows"
    changed = Signal()

    def __init__(self, get_tasks: Callable[[], list], parent=None):
        super().__init__(parent=parent)
        self.add_text = QT_TRANSLATE_NOOP("TaskQueue", "添加")
        self.select_all_text = QT_TRANSLATE_NOOP("NormalTextButton", "全选")
        self.clear_all_text = QT_TRANSLATE_NOOP("NormalTextButton", "清空")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)

        self.window_row = WindowSettingsRow(self)
        layout.addWidget(self.window_row)

        self.queue_list = TaskQueueList(get_tasks, self)
        layout.addWidget(self.queue_list, stretch=1)

        footer = QHBoxLayout()
        footer.setContentsMargins(2, 4, 2, 0)
        footer.setSpacing(4)
        self.add_button = DropDownPushButton(FIF.ADD, "", self)
        self.add_button.setMenu(build_add_menu(self, self._add_task))
        self.select_all = PushButton(self)
        self.clear_all = PushButton(self)
        footer.addWidget(self.add_button)
        footer.addWidget(self.select_all, 1)
        footer.addWidget(self.clear_all, 1)
        layout.addLayout(footer)

        self.select_all.clicked.connect(lambda: self.queue_list.set_all_enabled(True))
        self.clear_all.clicked.connect(lambda: self.queue_list.set_all_enabled(False))
        self.queue_list.changed.connect(self.changed)
        self.queue_list.taskSelected.connect(self._on_task_selected)
        self.window_row.selected.connect(self._on_window_selected)
        self.retranslateUi()

    def _add_task(self, task_type: str) -> None:
        self.queue_list.add_task(task_type)

    def _on_task_selected(self, task_id: str) -> None:
        if not task_id:
            if self.queue_list.count() == 0:
                self._on_window_selected()
            return
        self.window_row.clearSelection()
        self.window_row.setCurrentItem(None)
        self.itemSelected.emit(task_id)

    def _on_window_selected(self) -> None:
        self.queue_list.blockSignals(True)
        self.queue_list.clearSelection()
        self.queue_list.setCurrentItem(None)
        self.queue_list.blockSignals(False)
        self.queue_list.viewport().update()
        self.window_row.setCurrentRow(0)
        self.itemSelected.emit(WINDOW_SETTINGS_ID)

    def select(self, item_id: str) -> None:
        if item_id != WINDOW_SETTINGS_ID and self.queue_list.select_task(item_id):
            return
        self._on_window_selected()

    def set_editable(self, editable: bool) -> None:
        self.queue_list.set_editable(editable)

    def retranslateUi(self):
        self.add_button.setText(self.tr(self.add_text))
        self.add_button.setMenu(build_add_menu(self, self._add_task))
        self.select_all.setText(QCoreApplication.translate("NormalTextButton", self.select_all_text))
        self.clear_all.setText(QCoreApplication.translate("NormalTextButton", self.clear_all_text))
        self.window_row.retranslateUi()
        self.queue_list.refresh()

    def tr(self, text):
        return QCoreApplication.translate("TaskQueue", text)
