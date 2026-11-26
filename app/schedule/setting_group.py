"""设置页的「定时执行」：每个定时任务有自己的时间、任务列表和结束后操作。

定时任务通过 Windows 计划任务执行 `AALC.exe start --exit <定时任务 id>`。
运行时只用定时任务自己的设置，不改主界面的任务列表和默认结束后操作。
"""

from PySide6.QtCore import QT_TRANSLATE_NOOP, QCoreApplication, Qt, QTime, QTimer, Signal
from PySide6.QtWidgets import QHBoxLayout, QSizePolicy, QVBoxLayout, QWidget
from qfluentwidgets import (
    Action,
    BodyLabel,
    IndicatorPosition,
    PrimaryPushButton,
    PushButton,
    RoundMenu,
    SettingCard,
    SwitchButton,
    TimePicker,
    TransparentToolButton,
)
from qfluentwidgets import FluentIcon as FIF

from app.base_combination import BaseSettingCardGroup
from app.schedule.editor_dialog import open_editor
from app.schedule.texts import (
    schedule_summary,
    schedule_title,
    tr,
)
from module.config.task_queue import Schedule
from module.schedules import ScheduleBook


class ScheduleCard(SettingCard):
    changed = Signal()
    deleteRequested = Signal(object)

    def __init__(self, book: ScheduleBook, schedule: Schedule, parent=None):
        super().__init__(FIF.HISTORY, "", " ", parent)
        self.book = book
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
        self.book.set_time(self.schedule, time.toString("HH:mm"))

    def _on_switch(self, checked: bool) -> None:
        self.book.set_enabled(self.schedule, checked)
        self.retranslateUi()

    def _edit(self) -> None:
        def saved():
            self.retranslateUi()
            self.changed.emit()

        open_editor(self.book, self.schedule, self.window(), on_saved=saved)

    def _show_menu(self) -> None:
        menu = RoundMenu(parent=self)
        delete = Action(FIF.DELETE, tr(QT_TRANSLATE_NOOP("ScheduleEditor", "删除")))
        delete.triggered.connect(lambda: self.deleteRequested.emit(self))
        menu.addAction(delete)
        menu.exec(self.more_button.mapToGlobal(self.more_button.rect().bottomLeft()))

    def retranslateUi(self):
        self.titleLabel.setText(schedule_title(self.schedule, self.book.schedules))
        summary = schedule_summary(self.schedule)
        self.contentLabel.setText(self.contentLabel.fontMetrics().elidedText(summary, Qt.ElideRight, 420))
        self.contentLabel.setToolTip(summary)
        self.edit_button.setText(tr(QT_TRANSLATE_NOOP("ScheduleEditor", "编辑任务")))
        on = QCoreApplication.translate("SwitchSettingCard", "开")
        off = QCoreApplication.translate("SwitchSettingCard", "关")
        self.switch.setText(on if self.switch.isChecked() else off)


class ScheduleSettingGroup(BaseSettingCardGroup):
    """设置页的「定时执行 AALC」分组，卡片数量随定时任务增减"""

    def __init__(self, title: str, book: ScheduleBook, parent=None):
        super().__init__(title, parent)
        self.book = book
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
        for schedule in self.book.schedules:
            card = ScheduleCard(self.book, schedule, self.container)
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
        schedule = self.book.add()
        self.rebuild()
        # 等布局刷新后再弹出编辑框；取消则不保留这个新建的定时任务
        QTimer.singleShot(0, lambda: self._edit_new(schedule))

    def _edit_new(self, schedule: Schedule) -> None:
        card = next((c for c in self.cards if c.schedule is schedule), None)
        if card is None:
            return

        def cancelled():
            # 新建的定时任务还没启用，系统里没有对应的计划任务，删掉也不会碰系统
            if self.book.remove(schedule):
                self.rebuild()

        open_editor(self.book, schedule, self.window(), on_saved=card.retranslateUi, on_cancelled=cancelled)

    def _delete(self, card: ScheduleCard) -> None:
        from qfluentwidgets import MessageBox

        title = schedule_title(card.schedule, self.book.schedules)
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
        if self.book.remove(card.schedule):
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
