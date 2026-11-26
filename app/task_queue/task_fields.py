"""绑定到「当前选中的任务」的设置控件。

用的是项目原有的 BaseCheckBox / LabelWithSpinBox 等控件，只是把读写对象从全局 cfg
换成 TaskStore（当前选中的任务）。切换选中的任务时调用 load()，控件重新读取显示。
做法同 MAA 的 GetTaskConfig<T>() / SetTaskConfig<T>()：控件不变，换的是背后的任务。
主界面的镜牢页和各任务设置页、定时任务编辑框都用这里的东西。
"""

from PySide6.QtCore import QT_TRANSLATE_NOOP, QCoreApplication, QObject, Signal
from qfluentwidgets import CaptionLabel

from app.base_combination import LabelWithComboBox, LabelWithSpinBox, MirrorSpinBox
from app.base_tools import BaseCheckBox
from module.config.task_queue import TaskBase, get_field, set_field

GLOBAL_HINT = QT_TRANSLATE_NOOP("TaskPage", "以下设置对所有任务生效")


class TaskStore(QObject):
    """给 Base* 控件用的 ValueStore：读写当前绑定的任务。没有绑定任务时读到 None，控件不会写入"""

    changed = Signal(str)  # 被修改的字段名

    def __init__(self, parent=None):
        super().__init__(parent)
        self.task: TaskBase | None = None

    def get_value(self, key: str, default=None):
        if self.task is None:
            return default
        return get_field(self.task, key, default)

    def set_value(self, key: str, value) -> None:
        if self.task is not None and set_field(self.task, key, value):
            self.changed.emit(key)


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


def depends_on(controller: BaseCheckBox, dependents: list) -> None:
    """controller 没勾选时禁用 dependents（只影响显示，不改值）"""

    def apply(checked: bool):
        for widget in dependents:
            widget.setEnabled(checked)

    controller.check_box.toggled.connect(apply)
    controller.apply_dependency = lambda: apply(controller.check_box.isChecked())


class TaskWidgets:
    """一个设置页里绑定到任务的控件：统一 load / retranslate / 刷新依赖"""

    def __init__(self, store: TaskStore):
        self.store = store
        self.widgets: list = []
        self.controllers: list[BaseCheckBox] = []

    def check(self, field: str, title: str, tips: str | None = None, *, temporary=False, indent=0) -> BaseCheckBox:
        box = BaseCheckBox(field, None, title, center=False, tips=tips, temporary=temporary, store=self.store)
        if indent:
            box.hBoxLayout.setContentsMargins(indent, 0, 0, 0)
        return self.keep(box)

    def combo(self, field: str, label: str, items: dict) -> LabelWithComboBox:
        return self.keep(LabelWithComboBox(label, field, items, store=self.store))

    def spin(self, field: str, label: str) -> LabelWithSpinBox:
        return self.keep(LabelWithSpinBox(label, field, min_value=0, min_step=1, store=self.store))

    def keep(self, widget):
        self.widgets.append(widget)
        return widget

    def depends(self, controller: BaseCheckBox, dependents: list) -> None:
        depends_on(controller, dependents)
        self.controllers.append(controller)

    def load(self) -> None:
        for widget in self.widgets:
            widget.load()
        self.refresh_dependencies()

    def refresh_dependencies(self) -> None:
        for controller in self.controllers:
            controller.apply_dependency()

    def retranslateUi(self) -> None:
        for widget in self.widgets:
            widget.retranslateUi()


def mirror_widgets(fields: TaskWidgets, *, scheduled: bool) -> tuple[MirrorSpinBox, list, list]:
    """镜牢任务的设置控件：返回 (镜牢次数, 常用选项, 其余选项)。主界面和定时任务共用。

    主界面的困牢 / 不用每周加成可以「仅本次运行期间有效」（左键）或一直有效（右键）；
    定时任务每次都是新启动 AALC，没有「本次」的说法，勾上就一直有效。
    """
    count = fields.keep(MirrorSpinBox(QT_TRANSLATE_NOOP("MirrorSpinBox", "坐牢次数"), "count", store=fields.store))
    if scheduled:
        hard = fields.check("hard_mirror", QT_TRANSLATE_NOOP("BaseCheckBox", "使用困难镜牢"))
        weekly = fields.check("no_weekly_bonuses", QT_TRANSLATE_NOOP("BaseCheckBox", "不使用每周加成"))
    else:
        hard = fields.check(
            "hard_mirror",
            QT_TRANSLATE_NOOP("BaseCheckBox", "使用困难镜牢*"),
            QT_TRANSLATE_NOOP(
                "BaseCheckBox",
                "仅本次运行期间有效，重启AALC后失效\n右键可设置为永久生效\n开启自动困牢时，有剩余困牢次数就会打困牢",
            ),
            temporary=True,
        )
        weekly = fields.check(
            "no_weekly_bonuses",
            QT_TRANSLATE_NOOP("BaseCheckBox", "不使用每周加成*"),
            QT_TRANSLATE_NOOP("BaseCheckBox", "仅本次运行期间有效，重启AALC后失效\n右键可设置为永久生效"),
            temporary=True,
        )
    common = [
        hard,
        weekly,
        fields.check("floor_3_exit", QT_TRANSLATE_NOOP("BaseCheckBox", "只打三层")),
        fields.check("infinite", QT_TRANSLATE_NOOP("BaseCheckBox", "无限坐牢")),
    ]
    re_claim = fields.check("re_claim_rewards", QT_TRANSLATE_NOOP("BaseCheckBox", "再次领取奖励"))
    re_claim_parts = [
        fields.check("re_claim.missions", QT_TRANSLATE_NOOP("BaseCheckBox", "日常/周常"), indent=28),
        fields.check("re_claim.battle_pass", QT_TRANSLATE_NOOP("BaseCheckBox", "通行证奖励"), indent=28),
        fields.check("re_claim.mail", QT_TRANSLATE_NOOP("BaseCheckBox", "邮件"), indent=28),
    ]
    fields.depends(re_claim, re_claim_parts)
    rest = [
        fields.check(
            "save_rewards",
            QT_TRANSLATE_NOOP("BaseCheckBox", "保存困牢奖励"),
            QT_TRANSLATE_NOOP("BaseCheckBox", "仅在进行困难镜牢时生效，普通难度不生效"),
        ),
        fields.check("hard_single_bonuses", QT_TRANSLATE_NOOP("BaseCheckBox", "困牢单次加成")),
        fields.check("select_event_pack", QT_TRANSLATE_NOOP("BaseCheckBox", "第五层选择（最左边）活动卡包")),
        fields.check("skip_event_pack", QT_TRANSLATE_NOOP("BaseCheckBox", "第五层跳过（最左边）活动卡包")),
        fields.check("not_skip_whitegossypium", QT_TRANSLATE_NOOP("BaseCheckBox", "不跳过白棉花")),
        fields.check("fight_to_last_man", QT_TRANSLATE_NOOP("BaseCheckBox", "战斗直到全灭")),
        re_claim,
        *re_claim_parts,
    ]
    return count, common, rest
