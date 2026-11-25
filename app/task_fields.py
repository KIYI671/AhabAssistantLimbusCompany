"""绑定到某个任务项（task item）字段的设置控件。

旧的 BaseCheckBox / LabelWithSpinBox 等控件用字段名字符串直接读写全局配置；
任务列表里同类任务可以有多项，所以这里的控件改为读写「当前绑定的任务对象」。
切换选中的任务时调用 load(task) 刷新显示，不会触发写回。
"""

from typing import Callable

from PySide6.QtCore import QT_TRANSLATE_NOOP, QCoreApplication, QObject, Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QSizePolicy, QVBoxLayout
from qfluentwidgets import ComboBox, SpinBox, ToolTipFilter, ToolTipPosition

from app.base_tools import BaseLabel, RightClickCheckBox
from module.config.task_queue import TaskBase

GLOBAL_HINT = QT_TRANSLATE_NOOP("TaskPage", "以下设置对所有任务生效")


def _tr(context: str, text: str | None) -> str:
    return QCoreApplication.translate(context, text) if text else ""


class TaskBinder(QObject):
    """一个设置页共用一个 binder：记录当前绑定的任务，控件通过它写字段"""

    changed = Signal(str)  # 被修改的字段名

    def __init__(self, parent=None):
        super().__init__(parent)
        self.task: TaskBase | None = None

    def set(self, path: str, value) -> None:
        if self.task is None:
            return
        target, name = _resolve(self.task, path)
        if getattr(target, name) == value:
            return
        setattr(target, name, value)
        self.changed.emit(path)

    def get(self, path: str, default=None):
        if self.task is None:
            return default
        target, name = _resolve(self.task, path)
        return getattr(target, name, default)


def _resolve(task, path: str):
    """支持 "re_claim.mail" 这样的嵌套字段"""
    *parents, name = path.split(".")
    target = task
    for parent in parents:
        target = getattr(target, parent)
    return target, name


class BoundField(QFrame):
    def __init__(self, binder: TaskBinder, field: str, parent=None):
        super().__init__(parent)
        self.binder = binder
        self.field = field

    def load(self) -> None:
        raise NotImplementedError

    def retranslateUi(self) -> None:
        pass


class BoundCheckBox(BoundField):
    """复选框。

    session=True：取值 0/1/2，左键勾选仅本次运行 AALC 期间有效，右键勾选永久有效。
    checked_value：勾选时写入的值（例如定时任务里的困牢开关直接写 2，表示一直有效）。
    """

    def __init__(
        self,
        binder: TaskBinder,
        field: str,
        title: str,
        tips: str | None = None,
        *,
        context: str = "BaseCheckBox",
        session: bool = False,
        checked_value=True,
        indent: int = 0,
        parent=None,
    ):
        super().__init__(binder, field, parent)
        self.checked_value = checked_value
        self.title = title
        self.tips = tips
        self.context = context
        self.session = session
        layout = QHBoxLayout(self)
        layout.setContentsMargins(indent, 0, 0, 0)
        layout.setAlignment(Qt.AlignLeft)
        self.check_box = RightClickCheckBox(title, self)
        self.check_box.installEventFilter(
            ToolTipFilter(self.check_box, showDelay=0, position=ToolTipPosition.BOTTOM_LEFT)
        )
        layout.addWidget(self.check_box, 0, Qt.AlignLeft)
        self.check_box.toggled.connect(self._on_toggled)
        self.retranslateUi()

    def load(self) -> None:
        self.check_box.blockSignals(True)
        self.check_box.setChecked(bool(self.binder.get(self.field, False)))
        self.check_box.blockSignals(False)

    def _on_toggled(self, checked: bool) -> None:
        if self.session:
            value = (2 if self.check_box.right_clicked else 1) if checked else 0
        elif checked:
            value = self.checked_value
        else:
            value = 0 if isinstance(self.checked_value, int) and not isinstance(self.checked_value, bool) else False
        self.binder.set(self.field, value)

    def setEnabled(self, enabled: bool) -> None:
        self.check_box.setEnabled(enabled)

    def retranslateUi(self) -> None:
        self.check_box.setText(_tr(self.context, self.title))
        if self.tips:
            self.check_box.setToolTip(_tr(self.context, self.tips))


class _LabelledField(BoundField):
    def __init__(self, binder, field, label, context, tips=None, parent=None):
        super().__init__(binder, field, parent)
        self.label_text = label
        self.context = context
        self.tips = tips
        self.vbox = QVBoxLayout(self)
        self.vbox.setContentsMargins(0, 0, 0, 0)
        self.vbox.setSpacing(4)
        self.label = BaseLabel(label)
        self.vbox.addWidget(self.label)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        if tips:
            self.installEventFilter(ToolTipFilter(self))

    def retranslateUi(self) -> None:
        self.label.setText(_tr(self.context, self.label_text))
        if self.tips:
            self.setToolTip(_tr(self.context, self.tips))


class BoundSpinRow(_LabelledField):
    def __init__(
        self,
        binder: TaskBinder,
        field: str,
        label: str,
        *,
        minimum: int = 0,
        maximum: int = 9999,
        context: str = "LabelWithSpinBox",
        tips: str | None = None,
        parent=None,
    ):
        super().__init__(binder, field, label, context, tips, parent)
        self.spin_box = SpinBox(self)
        self.spin_box.setRange(minimum, maximum)
        self.spin_box.setAlignment(Qt.AlignCenter)
        self.vbox.addWidget(self.spin_box)
        self.spin_box.valueChanged.connect(lambda v: self.binder.set(self.field, int(v)))
        self.retranslateUi()

    def load(self) -> None:
        self.spin_box.blockSignals(True)
        self.spin_box.setValue(int(self.binder.get(self.field, 0) or 0))
        self.spin_box.blockSignals(False)


class BoundComboRow(_LabelledField):
    def __init__(
        self,
        binder: TaskBinder,
        field: str,
        label: str,
        options: dict,
        *,
        context: str = "LabelWithComboBox",
        option_context: str = "BaseComboBox",
        tips: str | None = None,
        parent=None,
    ):
        super().__init__(binder, field, label, context, tips, parent)
        self.options = list(options.items())
        self.option_context = option_context
        self.combo_box = ComboBox(self)
        self.combo_box.addItems([_tr(option_context, key) for key, _ in self.options])
        self.vbox.addWidget(self.combo_box)
        self.combo_box.currentIndexChanged.connect(self._on_index)
        self.retranslateUi()

    def _on_index(self, index: int) -> None:
        if 0 <= index < len(self.options):
            self.binder.set(self.field, self.options[index][1])

    def load(self) -> None:
        value = self.binder.get(self.field)
        self.combo_box.blockSignals(True)
        for i, (_, option_value) in enumerate(self.options):
            if option_value == value:
                self.combo_box.setCurrentIndex(i)
                break
        self.combo_box.blockSignals(False)

    def set_combo_enabled(self, enabled: bool) -> None:
        self.combo_box.setEnabled(enabled)

    def retranslateUi(self) -> None:
        super().retranslateUi()
        for i, (key, _) in enumerate(self.options):
            self.combo_box.setItemText(i, _tr(self.option_context, key))


class BoundInlineSpin(BoundField):
    """左边文字、右边数字框（镜牢次数）"""

    def __init__(
        self,
        binder: TaskBinder,
        field: str,
        label: str,
        *,
        minimum: int = 0,
        maximum: int = 9999,
        context: str = "MirrorSpinBox",
        parent=None,
    ):
        super().__init__(binder, field, parent)
        self.label_text = label
        self.context = context
        layout = QHBoxLayout(self)
        self.label = BaseLabel(label)
        self.spin_box = SpinBox(self)
        self.spin_box.setRange(minimum, maximum)
        self.spin_box.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.label, stretch=1)
        layout.addWidget(self.spin_box, stretch=2)
        self.setMaximumHeight(70)
        self.spin_box.valueChanged.connect(lambda v: self.binder.set(self.field, int(v)))
        self.retranslateUi()

    def load(self) -> None:
        self.spin_box.blockSignals(True)
        self.spin_box.setValue(int(self.binder.get(self.field, 0) or 0))
        self.spin_box.blockSignals(False)

    def retranslateUi(self) -> None:
        self.label.setText(_tr(self.context, self.label_text))


class BoundCheckCombo(BoundField):
    """左边复选框、右边下拉框（例如：使用连续作战 + 最大场次）"""

    def __init__(
        self,
        binder: TaskBinder,
        check_field: str,
        title: str,
        combo_field: str,
        options: dict,
        *,
        context: str = "CheckBoxWithComboBox",
        tips: str | None = None,
        tips_context: str = "BaseCheckBox",
        parent=None,
    ):
        super().__init__(binder, check_field, parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.check = BoundCheckBox(binder, check_field, title, tips, context=context)
        self.check_tips = (tips_context, tips)
        self.combo_field = combo_field
        self.options = list(options.items())
        self.combo_box = ComboBox(self)
        self.combo_box.addItems([key for key, _ in self.options])
        self.combo_box.setMinimumWidth(110)
        layout.addWidget(self.check, 1)
        layout.addWidget(self.combo_box)
        self.combo_box.currentIndexChanged.connect(self._on_index)
        self.check.check_box.toggled.connect(self.combo_box.setEnabled)
        self.retranslateUi()

    def _on_index(self, index: int) -> None:
        if 0 <= index < len(self.options):
            self.binder.set(self.combo_field, self.options[index][1])

    def load(self) -> None:
        self.check.load()
        value = self.binder.get(self.combo_field)
        self.combo_box.blockSignals(True)
        for i, (_, option_value) in enumerate(self.options):
            if option_value == value:
                self.combo_box.setCurrentIndex(i)
                break
        self.combo_box.blockSignals(False)
        self.combo_box.setEnabled(self.check.check_box.isChecked())

    def retranslateUi(self) -> None:
        self.check.retranslateUi()
        context, tips = self.check_tips
        if tips:
            self.check.check_box.setToolTip(_tr(context, tips))


def bind_dependency(controller: BoundCheckBox, dependents: list[BoundField], setter: Callable | None = None) -> None:
    """controller 未勾选时禁用 dependents（只影响显示，不改值）"""

    def apply(checked: bool):
        for widget in dependents:
            if setter is not None:
                setter(widget, checked)
            else:
                widget.setEnabled(checked)

    controller.check_box.toggled.connect(apply)
    controller._apply_dependency = apply  # load() 后由页面调用刷新


def refresh_dependency(controller: BoundCheckBox) -> None:
    apply = getattr(controller, "_apply_dependency", None)
    if apply is not None:
        apply(controller.check_box.isChecked())


def mirror_option_fields(binder: TaskBinder, *, scheduled: bool = False) -> tuple[BoundField, list[BoundField]]:
    """镜牢任务的参数控件：返回 (镜牢次数, 其余选项)。

    scheduled=True 用于定时任务：困牢 / 不用每周加成没有「仅本次运行有效」，勾上就一直有效。
    """
    count = BoundInlineSpin(binder, "count", QT_TRANSLATE_NOOP("MirrorSpinBox", "坐牢次数"))
    if scheduled:
        hard = BoundCheckBox(binder, "hard_mirror", QT_TRANSLATE_NOOP("BaseCheckBox", "使用困难镜牢"), checked_value=2)
        weekly = BoundCheckBox(
            binder, "no_weekly_bonuses", QT_TRANSLATE_NOOP("BaseCheckBox", "不使用每周加成"), checked_value=2
        )
    else:
        hard = BoundCheckBox(
            binder,
            "hard_mirror",
            QT_TRANSLATE_NOOP("BaseCheckBox", "使用困难镜牢*"),
            QT_TRANSLATE_NOOP(
                "BaseCheckBox",
                "仅本次运行期间有效，重启AALC后失效\n右键可设置为永久生效\n开启自动困牢时，有剩余困牢次数就会打困牢",
            ),
            session=True,
        )
        weekly = BoundCheckBox(
            binder,
            "no_weekly_bonuses",
            QT_TRANSLATE_NOOP("BaseCheckBox", "不使用每周加成*"),
            QT_TRANSLATE_NOOP("BaseCheckBox", "仅本次运行期间有效，重启AALC后失效\n右键可设置为永久生效"),
            session=True,
        )
    re_claim = BoundCheckBox(binder, "re_claim_rewards", QT_TRANSLATE_NOOP("BaseCheckBox", "再次领取奖励"))
    re_claim_parts = [
        BoundCheckBox(binder, "re_claim.missions", QT_TRANSLATE_NOOP("BaseCheckBox", "日常/周常"), indent=28),
        BoundCheckBox(binder, "re_claim.battle_pass", QT_TRANSLATE_NOOP("BaseCheckBox", "通行证奖励"), indent=28),
        BoundCheckBox(binder, "re_claim.mail", QT_TRANSLATE_NOOP("BaseCheckBox", "邮件"), indent=28),
    ]
    bind_dependency(re_claim, re_claim_parts)
    options = [
        hard,
        weekly,
        BoundCheckBox(binder, "floor_3_exit", QT_TRANSLATE_NOOP("BaseCheckBox", "只打三层")),
        BoundCheckBox(binder, "infinite", QT_TRANSLATE_NOOP("BaseCheckBox", "无限坐牢")),
        BoundCheckBox(
            binder,
            "save_rewards",
            QT_TRANSLATE_NOOP("BaseCheckBox", "保存困牢奖励"),
            QT_TRANSLATE_NOOP("BaseCheckBox", "仅在进行困难镜牢时生效，普通难度不生效"),
        ),
        BoundCheckBox(binder, "hard_single_bonuses", QT_TRANSLATE_NOOP("BaseCheckBox", "困牢单次加成")),
        BoundCheckBox(binder, "select_event_pack", QT_TRANSLATE_NOOP("BaseCheckBox", "第五层选择（最左边）活动卡包")),
        BoundCheckBox(binder, "skip_event_pack", QT_TRANSLATE_NOOP("BaseCheckBox", "第五层跳过（最左边）活动卡包")),
        BoundCheckBox(binder, "not_skip_whitegossypium", QT_TRANSLATE_NOOP("BaseCheckBox", "不跳过白棉花")),
        BoundCheckBox(binder, "fight_to_last_man", QT_TRANSLATE_NOOP("BaseCheckBox", "战斗直到全灭")),
        re_claim,
        *re_claim_parts,
    ]
    return count, options
