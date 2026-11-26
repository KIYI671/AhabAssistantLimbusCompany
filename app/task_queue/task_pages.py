"""各类任务的设置页。每页绑定一个任务项，切换选中的任务时调用 bind(task)。"""

from PySide6.QtCore import QT_TRANSLATE_NOOP, Signal

from app import all_teams, coutinuous_times, set_lunacy_to_enkephalin_options
from app.base_combination import CheckBoxWithComboBox
from app.base_tools import BaseCheckBox
from app.page_card import PageCard
from app.task_queue.task_fields import GLOBAL_HINT, GlobalHint, TaskWidgets, mirror_widgets
from app.task_queue.task_store import TaskStore
from module.config.task_queue import TaskBase


class TaskPage(PageCard):
    """绑定某个任务项的设置页"""

    taskChanged = Signal(str)  # 改动的字段名

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.store = TaskStore(self)
        self.store.changed.connect(self.taskChanged)
        self.fields = TaskWidgets(self.store)
        self.extra_widgets = []

    @property
    def task(self) -> TaskBase | None:
        return self.store.task

    def bind(self, task: TaskBase | None) -> None:
        self.store.task = task
        if task is not None:
            self.fields.load()

    def refresh_dependencies(self) -> None:
        self.fields.refresh_dependencies()

    def add_hint(self, layout, text: str = GLOBAL_HINT) -> GlobalHint:
        hint = GlobalHint(text)
        self.extra_widgets.append(hint)
        layout.addWidget(hint)
        return hint

    def retranslateUi(self):
        self.fields.retranslateUi()
        for widget in self.extra_widgets:
            widget.retranslateUi()
        super().retranslateUi()


class DailyTaskPage(TaskPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("page_daily_task")
        f = self.fields
        self.vbox_general.addWidget(f.spin("exp_count", QT_TRANSLATE_NOOP("LabelWithSpinBox", "经验本次数")))
        self.vbox_general.addWidget(f.spin("thread_count", QT_TRANSLATE_NOOP("LabelWithSpinBox", "纽本次数")))
        self.vbox_general.addWidget(f.combo("team", QT_TRANSLATE_NOOP("LabelWithComboBox", "使用编队"), all_teams))
        combat = f.keep(
            CheckBoxWithComboBox(
                "continuous_combat",
                QT_TRANSLATE_NOOP("CheckBoxWithComboBox", "使用连续作战"),
                None,
                "continuous_combat_max",
                tips=QT_TRANSLATE_NOOP("BaseCheckBox", "勾选后将使用连续作战模式，设置的值为最大连续作战场次"),
                store=self.store,
            )
        )
        combat.box.setFixedWidth(200)
        combat.combo_box.setFixedWidth(100)
        combat.add_items(coutinuous_times)
        self.vbox_general.addWidget(combat)

        exp = f.check("exp_targeted", QT_TRANSLATE_NOOP("BaseCheckBox", "经验本针对性配队"))
        exp_days = [
            ("exp_team_1_2", QT_TRANSLATE_NOOP("LabelWithComboBox", "周一、周二（斩击）")),
            ("exp_team_3_4", QT_TRANSLATE_NOOP("LabelWithComboBox", "周三、周四（突刺）")),
            ("exp_team_5_6", QT_TRANSLATE_NOOP("LabelWithComboBox", "周五、周六（打击）")),
            ("exp_team_7", QT_TRANSLATE_NOOP("LabelWithComboBox", "周日")),
        ]
        exp_rows = [f.combo(field, label, all_teams) for field, label in exp_days]
        f.depends(exp, exp_rows)

        thread = f.check("thread_targeted", QT_TRANSLATE_NOOP("BaseCheckBox", "纽本针对性配队"))
        thread_days = [
            QT_TRANSLATE_NOOP("LabelWithComboBox", "纽本周一（色欲）"),
            QT_TRANSLATE_NOOP("LabelWithComboBox", "纽本周二（怠惰）"),
            QT_TRANSLATE_NOOP("LabelWithComboBox", "纽本周三（暴食）"),
            QT_TRANSLATE_NOOP("LabelWithComboBox", "纽本周四（忧郁）"),
            QT_TRANSLATE_NOOP("LabelWithComboBox", "纽本周五（傲慢）"),
            QT_TRANSLATE_NOOP("LabelWithComboBox", "纽本周六（嫉妒）"),
            QT_TRANSLATE_NOOP("LabelWithComboBox", "纽本周日（暴怒）"),
        ]
        thread_rows = [f.combo(f"thread_team_{i}", label, all_teams) for i, label in enumerate(thread_days, start=1)]
        f.depends(thread, thread_rows)

        for widget in [exp, *exp_rows]:
            self.vbox_advanced.addWidget(widget)
        self.vbox_advanced.addSpacing(30)
        for widget in [thread, *thread_rows]:
            self.vbox_advanced.addWidget(widget)


class RewardTaskPage(TaskPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("page_get_prize")
        f = self.fields
        self.vbox_general.addWidget(f.check("missions", QT_TRANSLATE_NOOP("BaseCheckBox", "日常/周常")))
        self.vbox_general.addWidget(f.check("battle_pass", QT_TRANSLATE_NOOP("BaseCheckBox", "通行证奖励")))
        self.vbox_general.addWidget(f.check("mail", QT_TRANSLATE_NOOP("BaseCheckBox", "邮件")))


class EnkephalinTaskPage(TaskPage):
    def __init__(self, parent=None, show_global: bool = True):
        super().__init__(parent)
        self.setObjectName("page_lunacy_to_enkephalin")
        f = self.fields
        self.vbox_general.addWidget(
            f.combo(
                "lunacy_times", QT_TRANSLATE_NOOP("LabelWithComboBox", "狂气换体"), set_lunacy_to_enkephalin_options
            )
        )
        self.vbox_advanced.addWidget(f.check("dr_grandet", QT_TRANSLATE_NOOP("BaseCheckBox", "葛朗台模式")))
        if show_global:
            self.add_hint(self.vbox_advanced)
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
    """定时任务编辑框里的镜牢设置。队伍是全局设置，在主界面的镜牢页里管理"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("page_mirror")
        count, common, rest = mirror_widgets(self.fields, scheduled=True)
        self.vbox_general.addWidget(count)
        self.add_hint(self.vbox_general, QT_TRANSLATE_NOOP("TaskPage", "使用「一键长草 → 镜牢」中启用的编队"))
        for widget in common:
            self.vbox_general.addWidget(widget)
        for widget in rest:
            self.vbox_advanced.addWidget(widget)
