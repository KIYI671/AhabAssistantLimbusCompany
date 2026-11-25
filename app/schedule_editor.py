"""设置页的「定时执行」：每个定时任务有自己的时间、任务列表和结束后操作。

定时任务通过 Windows 计划任务执行 `AALC.exe start --exit <定时任务 id>`。
运行时只用定时任务自己的设置，不改主界面的任务列表和默认结束后操作。
"""

from PySide6.QtCore import QT_TRANSLATE_NOOP, QCoreApplication, Qt, QTime, QTimer, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QSizePolicy, QStackedWidget, QVBoxLayout, QWidget
from qfluentwidgets import (
    Action,
    BodyLabel,
    CheckBox,
    ComboBox,
    IndicatorPosition,
    LineEdit,
    MessageBoxBase,
    PrimaryPushButton,
    PushButton,
    RoundMenu,
    SettingCard,
    StrongBodyLabel,
    SubtitleLabel,
    SwitchButton,
    TimePicker,
    TransparentDropDownPushButton,
    TransparentPushButton,
    TransparentToolButton,
)
from qfluentwidgets import FluentIcon as FIF

from app.base_combination import BaseSettingCardGroup
from app.base_tools import BaseSettingLayout
from app.task_pages import DailyTaskPage, EnkephalinTaskPage, RewardTaskPage, ScheduledMirrorTaskPage
from app.task_queue_widget import TaskQueueList, build_add_menu, schedule_title, task_title
from module.after_completion_types import (
    ACTION_EXIT_AALC,
    ACTION_EXIT_EMULATOR,
    ACTION_EXIT_GAME,
    POWER_ACTION_HIBERNATE,
    POWER_ACTION_LOCK,
    POWER_ACTION_NONE,
    POWER_ACTION_SHUTDOWN,
    POWER_ACTION_SLEEP,
)
from module.config import cfg
from module.config.task_queue import AfterCompletion, Schedule, copy_task, default_task_queue
from module.logger import log

CONTEXT = "ScheduleEditor"


def tr(text: str) -> str:
    return QCoreApplication.translate(CONTEXT, text)


EXIT_ACTIONS = [
    (ACTION_EXIT_GAME, QT_TRANSLATE_NOOP("ScheduleEditor", "退出游戏")),
    (ACTION_EXIT_EMULATOR, QT_TRANSLATE_NOOP("ScheduleEditor", "退出模拟器")),
    (ACTION_EXIT_AALC, QT_TRANSLATE_NOOP("ScheduleEditor", "退出AALC")),
]
POWER_ACTIONS = [
    (POWER_ACTION_NONE, QT_TRANSLATE_NOOP("ScheduleEditor", "无")),
    (POWER_ACTION_SLEEP, QT_TRANSLATE_NOOP("ScheduleEditor", "睡眠")),
    (POWER_ACTION_HIBERNATE, QT_TRANSLATE_NOOP("ScheduleEditor", "休眠")),
    (POWER_ACTION_LOCK, QT_TRANSLATE_NOOP("ScheduleEditor", "锁屏")),
    (POWER_ACTION_SHUTDOWN, QT_TRANSLATE_NOOP("ScheduleEditor", "关机")),
]


# ---------------------------------------------------------------------------
# Windows 计划任务
# ---------------------------------------------------------------------------


def schedule_task_name(schedule: Schedule) -> str:
    """迁移来的定时任务沿用旧的计划任务名，已注册的任务不用重新注册"""
    suffix = schedule.id[len("autodaily") :]
    if suffix == "" or suffix.isdigit():
        return f"AALC Daily Task{suffix}"
    return f"AALC Schedule {suffix.lstrip('_')}"


def register_schedule(schedule: Schedule) -> None:
    from utils.schedule_helper import ScheduleHelper

    time = QTime.fromString(schedule.time, "HH:mm")
    try:
        helper = ScheduleHelper()
        helper.unregister_task(schedule_task_name(schedule))
        helper.register_daily_task(
            schedule_task_name(schedule), f"start --exit {schedule.id}", time.hour(), time.minute()
        )
    except Exception as e:
        log.error(f"注册定时任务 {schedule.id} 失败: {e}")


def unregister_schedule(schedule: Schedule) -> None:
    from utils.schedule_helper import ScheduleHelper

    try:
        ScheduleHelper().unregister_task(schedule_task_name(schedule))
    except Exception as e:
        log.error(f"注销定时任务 {schedule.id} 失败: {e}")


def after_completion_text(after: AfterCompletion) -> str:
    actions, power_action = after.normalized()
    parts = [tr(text) for action, text in EXIT_ACTIONS if action in actions]
    if power_action != POWER_ACTION_NONE:
        parts.append(tr(dict(POWER_ACTIONS)[power_action]))
    return "、".join(parts) if parts else tr(QT_TRANSLATE_NOOP("ScheduleEditor", "什么也不做"))


def schedule_summary(schedule: Schedule) -> str:
    names = [task_title(task) for task in schedule.tasks if task.enabled]
    tasks = "、".join(names) if names else tr(QT_TRANSLATE_NOOP("ScheduleEditor", "没有启用的任务"))
    return tr(QT_TRANSLATE_NOOP("ScheduleEditor", "{0}；结束后：{1}")).format(
        tasks, after_completion_text(schedule.after_completion)
    )


# ---------------------------------------------------------------------------
# 编辑框
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# 设置页里的卡片
# ---------------------------------------------------------------------------


class ScheduleCard(SettingCard):
    changed = Signal()
    deleteRequested = Signal(object)

    def __init__(self, schedule: Schedule, parent=None):
        super().__init__(FIF.HISTORY, "", " ", parent)
        self.schedule = schedule
        self.setFixedHeight(76)
        self.contentLabel.setWordWrap(False)

        self.time_picker = TimePicker(self)
        self.time_picker.setTime(QTime.fromString(schedule.time, "HH:mm"))
        self.edit_button = PushButton(FIF.EDIT, "", self)
        self.switch = SwitchButton(self, IndicatorPosition.RIGHT)
        self.switch.setChecked(schedule.enabled)
        self.more_button = TransparentToolButton(FIF.MORE, self)

        self.hBoxLayout.addWidget(self.time_picker, 0, Qt.AlignRight)
        self.hBoxLayout.addSpacing(12)
        self.hBoxLayout.addWidget(self.edit_button, 0, Qt.AlignRight)
        self.hBoxLayout.addSpacing(16)
        self.hBoxLayout.addWidget(self.switch, 0, Qt.AlignRight)
        self.hBoxLayout.addSpacing(4)
        self.hBoxLayout.addWidget(self.more_button, 0, Qt.AlignRight)
        self.hBoxLayout.addSpacing(12)

        self.time_picker.timeChanged.connect(self._on_time_changed)
        self.switch.checkedChanged.connect(self._on_switch)
        self.edit_button.clicked.connect(self._edit)
        self.more_button.clicked.connect(self._show_menu)
        self.retranslateUi()

    def _on_time_changed(self, time: QTime) -> None:
        self.schedule.time = time.toString("HH:mm")
        cfg.save()
        if self.schedule.enabled:
            register_schedule(self.schedule)

    def _on_switch(self, checked: bool) -> None:
        self.schedule.enabled = checked
        cfg.save()
        if checked:
            register_schedule(self.schedule)
        else:
            unregister_schedule(self.schedule)
        self.retranslateUi()

    def _edit(self) -> None:
        def saved():
            self.retranslateUi()
            self.changed.emit()

        open_editor(self.schedule, self.window(), on_saved=saved)

    def _show_menu(self) -> None:
        menu = RoundMenu(parent=self)
        delete = Action(FIF.DELETE, tr(QT_TRANSLATE_NOOP("ScheduleEditor", "删除")))
        delete.triggered.connect(lambda: self.deleteRequested.emit(self))
        menu.addAction(delete)
        menu.exec(self.more_button.mapToGlobal(self.more_button.rect().bottomLeft()))

    def retranslateUi(self):
        self.titleLabel.setText(schedule_title(self.schedule, cfg.config.schedules))
        summary = schedule_summary(self.schedule)
        self.contentLabel.setText(self.contentLabel.fontMetrics().elidedText(summary, Qt.ElideRight, 420))
        self.contentLabel.setToolTip(summary)
        self.edit_button.setText(tr(QT_TRANSLATE_NOOP("ScheduleEditor", "编辑任务")))
        on = QCoreApplication.translate("SwitchSettingCard", "开")
        off = QCoreApplication.translate("SwitchSettingCard", "关")
        self.switch.setText(on if self.switch.isChecked() else off)


class ScheduleSettingGroup(BaseSettingCardGroup):
    """设置页的「定时执行 AALC」分组，卡片数量随定时任务增减"""

    def __init__(self, title: str, parent=None):
        super().__init__(title, parent)
        self.cards: list[ScheduleCard] = []
        # SettingCardGroup 的 ExpandLayout 不支持移除控件，卡片放在自己的容器里增删
        self.container = QWidget(self)
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(0, 0, 0, 0)
        self.container_layout.setSpacing(2)

        self.footer = QWidget(self.container)
        footer_layout = QHBoxLayout(self.footer)
        footer_layout.setContentsMargins(0, 6, 0, 0)
        self.add_button = PrimaryPushButton(FIF.ADD, "", self.footer)
        self.add_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.hint = BodyLabel(self.footer)
        self.hint.setTextColor("#8a8a8a", "#9a9a9a")
        self.hint.setWordWrap(True)
        footer_layout.addWidget(self.add_button, 0, Qt.AlignVCenter)
        footer_layout.addSpacing(12)
        footer_layout.addWidget(self.hint, 1)
        self.container_layout.addWidget(self.footer)
        self.addSettingCard(self.container)
        self.add_button.clicked.connect(self._add_schedule)
        self.rebuild()

    def rebuild(self) -> None:
        for card in self.cards:
            self.container_layout.removeWidget(card)
            card.hide()
            card.deleteLater()
        self.cards = []
        for schedule in cfg.config.schedules:
            card = ScheduleCard(schedule, self.container)
            card.deleteRequested.connect(self._delete)
            card.changed.connect(self._refresh_titles)
            self.cards.append(card)
            self.container_layout.insertWidget(self.container_layout.count() - 1, card)
        self.retranslateUi()
        self._resize()

    def _resize(self) -> None:
        spacing = self.container_layout.spacing()
        height = sum(card.height() + spacing for card in self.cards)
        height += max(self.footer.sizeHint().height(), self.add_button.sizeHint().height() + 6)
        self.container.setFixedHeight(height)
        self.adjustSize()

    def _refresh_titles(self) -> None:
        for card in self.cards:
            card.retranslateUi()

    def _add_schedule(self) -> None:
        schedule = Schedule(tasks=default_task_queue())
        cfg.config.schedules.append(schedule)
        cfg.save()
        self.rebuild()
        # 等布局刷新后再弹出编辑框；取消则不保留这个新建的定时任务
        QTimer.singleShot(0, lambda: self._edit_new(schedule))

    def _edit_new(self, schedule: Schedule) -> None:
        card = next((c for c in self.cards if c.schedule is schedule), None)
        if card is None:
            return

        def cancelled():
            if schedule in cfg.config.schedules:
                cfg.config.schedules.remove(schedule)
                cfg.save()
                self.rebuild()

        open_editor(schedule, self.window(), on_saved=card.retranslateUi, on_cancelled=cancelled)

    def _delete(self, card: ScheduleCard) -> None:
        from qfluentwidgets import MessageBox

        title = schedule_title(card.schedule, cfg.config.schedules)
        box = MessageBox(
            tr(QT_TRANSLATE_NOOP("ScheduleEditor", "删除定时任务")),
            tr(QT_TRANSLATE_NOOP("ScheduleEditor", "确定删除「{0}」吗？")).format(title),
            self.window(),
        )
        box.setWindowModality(Qt.WindowModality.NonModal)
        box.accepted.connect(lambda: self._confirm_delete(card))
        box.finished.connect(lambda _: box.deleteLater())
        box.show()

    def _confirm_delete(self, card: ScheduleCard) -> None:
        if card.schedule not in cfg.config.schedules:
            return
        unregister_schedule(card.schedule)
        cfg.config.schedules.remove(card.schedule)
        cfg.save()
        self.rebuild()

    def retranslateUi(self):
        super().retranslateUi()
        self.add_button.setText(tr(QT_TRANSLATE_NOOP("ScheduleEditor", "添加定时任务")))
        self.add_button.adjustSize()
        self.add_button.setMinimumWidth(self.add_button.sizeHint().width() + 8)
        self.hint.setText(
            tr(
                QT_TRANSLATE_NOOP(
                    "ScheduleEditor",
                    "电脑开机时会在设定时间启动 AALC，按定时任务自己的任务列表执行，不会改动主界面的设置",
                )
            )
        )
        for card in self.cards:
            card.retranslateUi()
