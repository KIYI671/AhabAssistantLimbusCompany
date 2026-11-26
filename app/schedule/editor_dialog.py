"""定时任务的编辑框：改名称、任务列表和结束后操作。改的是副本，点「保存」才写回。"""

from PySide6.QtCore import QT_TRANSLATE_NOOP, Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QStackedWidget, QVBoxLayout, QWidget
from qfluentwidgets import (
    BodyLabel,
    CheckBox,
    ComboBox,
    LineEdit,
    MessageBoxBase,
    StrongBodyLabel,
    SubtitleLabel,
    TransparentDropDownPushButton,
    TransparentPushButton,
)
from qfluentwidgets import FluentIcon as FIF

from app.base_tools import BaseSettingLayout
from app.schedule.texts import EXIT_ACTIONS, POWER_ACTIONS, schedule_title, tr
from app.task_queue.queue_list import TaskQueueList, build_add_menu
from app.task_queue.task_pages import DailyTaskPage, EnkephalinTaskPage, RewardTaskPage, ScheduledMirrorTaskPage
from module.config import cfg
from module.config.task_queue import AfterCompletion, Schedule, copy_task


class AfterCompletionFields(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        self.label = StrongBodyLabel(self)
        layout.addWidget(self.label)
        self.boxes = {}
        for action, text in EXIT_ACTIONS:
            box = CheckBox(self)
            self.boxes[action] = (box, text)
            layout.addWidget(box)
        self.then_label = BodyLabel(self)
        layout.addSpacing(8)
        layout.addWidget(self.then_label)
        self.power = ComboBox(self)
        self.power.addItems(["" for _ in POWER_ACTIONS])
        self.power.setMinimumWidth(110)
        layout.addWidget(self.power)
        layout.addStretch(1)
        self.retranslateUi()

    def load(self, after: AfterCompletion) -> None:
        actions, power_action = after.normalized()
        for action, (box, _) in self.boxes.items():
            box.setChecked(action in actions)
        values = [value for value, _ in POWER_ACTIONS]
        self.power.setCurrentIndex(values.index(power_action) if power_action in values else 0)

    def value(self) -> AfterCompletion:
        actions = [action for action, (box, _) in self.boxes.items() if box.isChecked()]
        power_action = POWER_ACTIONS[max(0, self.power.currentIndex())][0]
        return AfterCompletion(actions=actions, power_action=power_action)

    def retranslateUi(self):
        self.label.setText(tr(QT_TRANSLATE_NOOP("ScheduleEditor", "运行结束后")))
        for box, text in self.boxes.values():
            box.setText(tr(text))
        self.then_label.setText(tr(QT_TRANSLATE_NOOP("ScheduleEditor", "然后")))
        for i, (_, text) in enumerate(POWER_ACTIONS):
            self.power.setItemText(i, tr(text))


class ScheduleEditorDialog(MessageBoxBase):
    """编辑一个定时任务。改的是副本，点「保存」才写回。"""

    def __init__(self, schedule: Schedule, parent=None):
        super().__init__(parent)
        self.schedule = schedule
        self.draft = schedule.model_copy(deep=True)

        self.title = SubtitleLabel(self)
        self.name_edit = LineEdit(self)
        self.name_edit.setText(schedule.name or "")
        self.name_edit.setPlaceholderText(schedule_title(schedule, cfg.config.schedules))
        self.name_edit.setClearButtonEnabled(True)
        self.name_edit.setMaximumWidth(260)

        header = QHBoxLayout()
        header.addWidget(self.title)
        header.addStretch(1)
        self.name_label = BodyLabel(self)
        header.addWidget(self.name_label)
        header.addWidget(self.name_edit)

        # 左：任务列表
        left = BaseSettingLayout(parent=self)
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(6, 6, 6, 6)
        left_header = QHBoxLayout()
        left_header.setContentsMargins(8, 0, 0, 0)
        self.list_title = StrongBodyLabel(left)
        self.add_button = TransparentDropDownPushButton(FIF.ADD, "", left)
        left_header.addWidget(self.list_title)
        left_header.addStretch(1)
        left_header.addWidget(self.add_button)
        left_layout.addLayout(left_header)
        self.queue_list = TaskQueueList(lambda: self.draft.tasks, left)
        left_layout.addWidget(self.queue_list, 1)
        self.copy_button = TransparentPushButton(FIF.COPY, "", left)
        left_layout.addWidget(self.copy_button, 0, Qt.AlignLeft)
        left.setFixedWidth(340)

        # 右：选中任务的设置
        self.pages = {
            "daily": DailyTaskPage(self),
            "reward": RewardTaskPage(self),
            "enkephalin": EnkephalinTaskPage(self, show_global=False),
            "mirror": ScheduledMirrorTaskPage(self),
        }
        self.empty_page = QFrame(self)
        empty_layout = QVBoxLayout(self.empty_page)
        self.empty_label = BodyLabel(self.empty_page)
        self.empty_label.setTextColor("#8a8a8a", "#9a9a9a")
        empty_layout.addWidget(self.empty_label, 0, Qt.AlignCenter)
        self.stack = QStackedWidget(self)
        self.stack.addWidget(self.empty_page)
        for page in self.pages.values():
            self.stack.addWidget(page)
            page.taskChanged.connect(lambda _field: self.queue_list.refresh())

        body = QHBoxLayout()
        body.setSpacing(16)
        body.addWidget(left)
        body.addWidget(self.stack, 1)

        self.after_fields = AfterCompletionFields(self)
        self.after_fields.load(self.draft.after_completion)

        self.viewLayout.setSpacing(14)
        self.viewLayout.addLayout(header)
        self.viewLayout.addLayout(body, 1)
        self.viewLayout.addWidget(self.after_fields)
        self.widget.setMinimumSize(920, 620)

        self.add_button.setMenu(build_add_menu(self, self.queue_list.add_task))
        self.copy_button.clicked.connect(self._copy_from_main)
        self.queue_list.taskSelected.connect(self._show_task)
        self.yesButton.clicked.connect(self._save)
        self.retranslateUi()
        if self.draft.tasks:
            self.queue_list.select_task(self.draft.tasks[0].id)

    def _show_task(self, task_id: str) -> None:
        task = self.queue_list.find_task(task_id)
        if task is None:
            self.stack.setCurrentWidget(self.empty_page)
            return
        page = self.pages[task.type]
        page.bind(task)
        self.stack.setCurrentWidget(page)

    def _copy_from_main(self) -> None:
        """用主界面当前的任务列表（含参数和勾选）替换本定时任务的列表"""
        self.draft.tasks[:] = [copy_task(task) for task in cfg.config.task_queue]
        first = self.draft.tasks[0].id if self.draft.tasks else ""
        self.queue_list.reload(select_id=first)
        if not first:
            self._show_task("")

    def _save(self) -> None:
        name = self.name_edit.text().strip()
        self.schedule.name = name or None
        self.schedule.tasks = self.draft.tasks
        self.schedule.after_completion = self.after_fields.value()
        cfg.save()

    def retranslateUi(self):
        self.title.setText(tr(QT_TRANSLATE_NOOP("ScheduleEditor", "编辑定时任务")))
        self.name_label.setText(tr(QT_TRANSLATE_NOOP("ScheduleEditor", "名称")))
        self.list_title.setText(tr(QT_TRANSLATE_NOOP("ScheduleEditor", "执行的任务")))
        self.add_button.setText(tr(QT_TRANSLATE_NOOP("ScheduleEditor", "添加")))
        self.copy_button.setText(tr(QT_TRANSLATE_NOOP("ScheduleEditor", "从主界面复制任务列表")))
        self.empty_label.setText(tr(QT_TRANSLATE_NOOP("ScheduleEditor", "在左侧选择任务查看设置")))
        self.yesButton.setText(tr(QT_TRANSLATE_NOOP("ScheduleEditor", "保存")))
        self.cancelButton.setText(tr(QT_TRANSLATE_NOOP("ScheduleEditor", "取消")))
        for page in self.pages.values():
            page.retranslateUi()
        self.after_fields.retranslateUi()


def open_editor(schedule: Schedule, window, on_saved=None, on_cancelled=None) -> "ScheduleEditorDialog":
    """非模态打开编辑框。

    不用 exec()：编辑框是主窗口的子控件，嵌套的模态事件循环会和启动后异步弹出的
    公告窗口（窗口级模态）互相影响，实测会让主窗口一直处于禁用状态、点什么都没反应。
    编辑框自带全窗口遮罩，背后的界面本来就点不到，不需要模态。
    """
    dialog = ScheduleEditorDialog(schedule, window)
    dialog.setWindowModality(Qt.WindowModality.NonModal)
    if on_saved is not None:
        dialog.accepted.connect(on_saved)
    if on_cancelled is not None:
        dialog.rejected.connect(on_cancelled)
    dialog.finished.connect(lambda _: dialog.deleteLater())
    dialog.show()
    dialog.raise_()
    return dialog
