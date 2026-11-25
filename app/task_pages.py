"""各类任务的设置页。每页绑定一个任务项，切换选中的任务时调用 bind(task)。"""

from PySide6.QtCore import QT_TRANSLATE_NOOP, QCoreApplication, Signal
from qfluentwidgets import CaptionLabel

from app import all_teams, coutinuous_times, set_lunacy_to_enkephalin_options
from app.base_tools import BaseCheckBox
from app.page_card import PageCard
from app.task_fields import (
    GLOBAL_HINT,
    BoundCheckBox,
    BoundCheckCombo,
    BoundComboRow,
    BoundField,
    BoundSpinRow,
    TaskBinder,
    bind_dependency,
    mirror_option_fields,
    refresh_dependency,
)
from module.config.task_queue import TaskBase


class GlobalHint(CaptionLabel):
    """设置页里区分「本任务」和「全局」设置的小标题"""

    def __init__(self, text: str = GLOBAL_HINT, parent=None):
        super().__init__(parent)
        self.source_text = text
        self.setContentsMargins(4, 12, 0, 2)
        self.setTextColor("#7a7a7a", "#a0a0a0")
        self.retranslateUi()

    def retranslateUi(self):
        self.setText(QCoreApplication.translate("TaskPage", self.source_text))


class TaskPage(PageCard):
    """绑定某个任务项的设置页"""

    taskChanged = Signal(str)  # 改动的字段名

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.binder = TaskBinder(self)
        self.binder.changed.connect(self.taskChanged)
        self.fields: list[BoundField] = []
        self.controllers: list[BoundCheckBox] = []
        self.extra_widgets = []

    @property
    def task(self) -> TaskBase | None:
        return self.binder.task

    def add(self, field: BoundField, advanced: bool = False) -> BoundField:
        self.fields.append(field)
        (self.vbox_advanced if advanced else self.vbox_general).addWidget(field)
        return field

    def depends(self, controller: BoundCheckBox, dependents: list[BoundField]) -> None:
        bind_dependency(controller, dependents)
        self.controllers.append(controller)

    def bind(self, task: TaskBase | None) -> None:
        self.binder.task = task
        if task is None:
            return
        for field in self.fields:
            field.load()
        self.refresh_dependencies()

    def refresh_dependencies(self) -> None:
        for controller in self.controllers:
            refresh_dependency(controller)

    def retranslateUi(self):
        for field in self.fields:
            field.retranslateUi()
        for widget in self.extra_widgets:
            widget.retranslateUi()
        super().retranslateUi()


class DailyTaskPage(TaskPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("page_daily_task")
        b = self.binder
        self.add(BoundSpinRow(b, "exp_count", QT_TRANSLATE_NOOP("LabelWithSpinBox", "经验本次数")))
        self.add(BoundSpinRow(b, "thread_count", QT_TRANSLATE_NOOP("LabelWithSpinBox", "纽本次数")))
        self.add(BoundComboRow(b, "team", QT_TRANSLATE_NOOP("LabelWithComboBox", "使用编队"), all_teams))
        self.add(
            BoundCheckCombo(
                b,
                "continuous_combat",
                QT_TRANSLATE_NOOP("CheckBoxWithComboBox", "使用连续作战"),
                "continuous_combat_max",
                coutinuous_times,
                tips=QT_TRANSLATE_NOOP("BaseCheckBox", "勾选后将使用连续作战模式，设置的值为最大连续作战场次"),
            )
        )

        exp = self.add(
            BoundCheckBox(b, "exp_targeted", QT_TRANSLATE_NOOP("BaseCheckBox", "经验本针对性配队")), advanced=True
        )
        exp_days = [
            ("exp_team_1_2", QT_TRANSLATE_NOOP("LabelWithComboBox", "周一、周二（斩击）")),
            ("exp_team_3_4", QT_TRANSLATE_NOOP("LabelWithComboBox", "周三、周四（突刺）")),
            ("exp_team_5_6", QT_TRANSLATE_NOOP("LabelWithComboBox", "周五、周六（打击）")),
            ("exp_team_7", QT_TRANSLATE_NOOP("LabelWithComboBox", "周日")),
        ]
        self.depends(exp, [self.add(BoundComboRow(b, f, t, all_teams), advanced=True) for f, t in exp_days])
        self.vbox_advanced.addSpacing(24)

        thread = self.add(
            BoundCheckBox(b, "thread_targeted", QT_TRANSLATE_NOOP("BaseCheckBox", "纽本针对性配队")), advanced=True
        )
        thread_days = [
            QT_TRANSLATE_NOOP("LabelWithComboBox", "纽本周一（色欲）"),
            QT_TRANSLATE_NOOP("LabelWithComboBox", "纽本周二（怠惰）"),
            QT_TRANSLATE_NOOP("LabelWithComboBox", "纽本周三（暴食）"),
            QT_TRANSLATE_NOOP("LabelWithComboBox", "纽本周四（忧郁）"),
            QT_TRANSLATE_NOOP("LabelWithComboBox", "纽本周五（傲慢）"),
            QT_TRANSLATE_NOOP("LabelWithComboBox", "纽本周六（嫉妒）"),
            QT_TRANSLATE_NOOP("LabelWithComboBox", "纽本周日（暴怒）"),
        ]
        self.depends(
            thread,
            [
                self.add(BoundComboRow(b, f"thread_team_{i}", text, all_teams), advanced=True)
                for i, text in enumerate(thread_days, start=1)
            ],
        )


class RewardTaskPage(TaskPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("page_get_prize")
        b = self.binder
        self.add(BoundCheckBox(b, "missions", QT_TRANSLATE_NOOP("BaseCheckBox", "日常/周常")))
        self.add(BoundCheckBox(b, "battle_pass", QT_TRANSLATE_NOOP("BaseCheckBox", "通行证奖励")))
        self.add(BoundCheckBox(b, "mail", QT_TRANSLATE_NOOP("BaseCheckBox", "邮件")))


class EnkephalinTaskPage(TaskPage):
    def __init__(self, parent=None, show_global: bool = True):
        super().__init__(parent)
        self.setObjectName("page_lunacy_to_enkephalin")
        b = self.binder
        self.add(
            BoundComboRow(
                b, "lunacy_times", QT_TRANSLATE_NOOP("LabelWithComboBox", "狂气换体"), set_lunacy_to_enkephalin_options
            )
        )
        self.add(BoundCheckBox(b, "dr_grandet", QT_TRANSLATE_NOOP("BaseCheckBox", "葛朗台模式")), advanced=True)
        if show_global:
            hint = GlobalHint()
            self.extra_widgets.append(hint)
            self.vbox_advanced.addWidget(hint)
            # 每个日常 / 镜牢结束后的自动换饼都会读这个开关，所以是全局设置
            self.skip_enkephalin = BaseCheckBox(
                "skip_enkephalin",
                None,
                QT_TRANSLATE_NOOP("BaseCheckBox", "不自动兑换脑啡肽 (?)"),
                tips=QT_TRANSLATE_NOOP("BaseCheckBox", "勾选后除狂气换体以外不执行兑换脑啡肽的操作"),
                center=False,
            )
            self.extra_widgets.append(self.skip_enkephalin)
            self.vbox_advanced.addWidget(self.skip_enkephalin)


class ScheduledMirrorTaskPage(TaskPage):
    """定时任务编辑框里的镜牢设置：没有队伍列表（队伍是全局设置）"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("page_mirror")
        count, options = mirror_option_fields(self.binder, scheduled=True)
        self.add(count)
        hint = GlobalHint(QT_TRANSLATE_NOOP("TaskPage", "使用「一键长草 → 镜牢」中启用的编队"))
        self.extra_widgets.append(hint)
        self.vbox_general.addWidget(hint)
        # 常用的几项放在常规设置，其余放高级设置
        general = {"hard_mirror", "no_weekly_bonuses", "infinite", "floor_3_exit"}
        for field in options:
            self.add(field, advanced=field.field not in general)
            if field.field == "re_claim_rewards":
                self.controllers.append(field)
