"""Independent team settings; no game input or global selection signals."""

from pathlib import Path

from PySide6.QtCore import QEvent, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import CheckBox, ComboBox, ExpandSettingCard, LineEdit, PushButton, SpinBox

from utils.protected_gifts import import_gift_image
from utils.route_weights import ROUTE_NODE_LABELS
from app.common.hover_notes import HoverNoteLabel, set_hover_note

SINNER_NAMES = (
    ("YiSang", "李箱"),
    ("Faust", "浮士德"),
    ("DonQuixote", "堂吉诃德"),
    ("Ryoshu", "良秀"),
    ("Meursault", "默尔索"),
    ("HongLu", "鸿璐"),
    ("Heathcliff", "希斯克利夫"),
    ("Ishmael", "以实玛利"),
    ("Rodion", "罗佳"),
    ("Sinclair", "辛克莱"),
    ("Outis", "奥提斯"),
    ("Gregor", "格里高尔"),
)


class NestedSettingsCard(ExpandSettingCard):
    """Keep an outer group sized to its expanding child sections."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._resize_pending = False
        self.view.installEventFilter(self)
        self.expandAni.finished.connect(self._settle_self)

    def _settle_self(self):
        if self.isExpand:
            self._resize_sections()
        else:
            self.setFixedHeight(self.card.height())

    def eventFilter(self, watched, event):
        handled = super().eventFilter(watched, event)
        if watched is getattr(self, "view", None) and event.type() == QEvent.Type.LayoutRequest:
            if not self._resize_pending:
                self._resize_pending = True
                QTimer.singleShot(0, self._resize_sections)
        return handled

    def _resize_sections(self):
        self._resize_pending = False
        self._adjustViewSize()
        self.updateGeometry()

    def addSection(self, section):
        self.viewLayout.addWidget(section)
        section.expandAni.finished.connect(lambda: self._settle_section(section))

    def _settle_section(self, section):
        if section.isExpand:
            section._adjustViewSize()
        else:
            section.setFixedHeight(section.card.height())
        self._resize_sections()


class ExcludedSinnerCard(QToolButton):
    """Reuse original portrait assets without affecting formation selection."""

    def __init__(self, index, parent=None):
        super().__init__(parent)
        self.sinner_index = index
        key, name = SINNER_NAMES[index]
        self.setObjectName(f"rabbit_event_sinner_{index}")
        self.setAccessibleName(f"禁止{name}参与事件")
        self.setToolTip(name)
        self.setCheckable(True)
        self.setFixedSize(102, 156)
        self._portrait = QPixmap(str(Path("assets/app/sinner") / key / "Sinner.png"))
        self._name = name
        self.toggled.connect(lambda _: self.update())

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(2, 2, -2, -2)
        painter.fillRect(rect, QColor("#212121"))
        if not self._portrait.isNull():
            painter.drawPixmap(rect, self._portrait)
        if not self.isChecked():
            painter.fillRect(rect, QColor(12, 12, 12, 180))
        if not self.isEnabled():
            painter.fillRect(rect, QColor(12, 12, 12, 55))
        painter.setPen(QPen(QColor("#fbc500") if self.isChecked() else QColor("#626262"), 2))
        painter.drawRoundedRect(rect, 5, 5)
        painter.fillRect(3, self.height() - 26, self.width() - 6, 23, QColor(15, 15, 15, 200))
        painter.setPen(QColor("#fbc500") if self.isChecked() else QColor("#b0b0b0"))
        painter.drawText(3, self.height() - 26, self.width() - 6, 23, Qt.AlignmentFlag.AlignCenter, self._name)


class ObservationCoordinateSpinBox(SpinBox):
    """Let page scrolling pass through without changing an observation target."""

    def wheelEvent(self, event):
        event.ignore()


class ObservePackRuleRow(QWidget):
    changed = Signal()
    removed = Signal(object)

    def __init__(self, rule, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.floor = ObservationCoordinateSpinBox(self)
        self.floor.setRange(1, 5)
        self.row = ObservationCoordinateSpinBox(self)
        self.row.setRange(1, 10)
        self.column = ObservationCoordinateSpinBox(self)
        self.column.setRange(1, 5)
        for label, control, value in zip(("楼层", "所在行", "所在列"), (self.floor, self.row, self.column), rule):
            control.setFixedWidth(128)
            control.setValue(value)
            layout.addWidget(QLabel(label, self))
            layout.addWidget(control)
            control.valueChanged.connect(lambda _: self.changed.emit())
        self.remove_button = PushButton("删除", self)
        self.remove_button.clicked.connect(lambda: self.removed.emit(self))
        layout.addStretch(1)
        layout.addWidget(self.remove_button)
        self._accepted_floor = self.floor.value()

    def value(self):
        return [self.floor.value(), self.row.value(), self.column.value()]


class TeamOptionWidget(QWidget):
    """Edit a team copy through direct signals, without global configuration writes."""

    changed = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._loading = False
        self._resize_pending = False
        self.checks = {}
        self.explanation_notes = []
        self._last_note_target = None
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(15, 8, 15, 12)
        self.main_layout.setSpacing(12)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)

    def event(self, event):
        handled = super().event(event)
        if event.type() == QEvent.Type.LayoutRequest and hasattr(self, "_resize_pending"):
            self._schedule_card_resize()
        return handled

    def eventFilter(self, watched, event):
        if event.type() == QEvent.Type.LayoutRequest:
            self._schedule_card_resize()
        return super().eventFilter(watched, event)

    def _check(self, key, text, body=None):
        check = CheckBox(text, self)
        check.setObjectName(key)
        self.checks[key] = check
        self._last_note_target = check
        for note in self.explanation_notes:
            if len(note.targets) == 1:
                note.add_target(check)
        check.toggled.connect(lambda checked, key=key: self._emit(key, checked))
        if body is not None:
            check.toggled.connect(body.setEnabled)
            body.setEnabled(False)
        self.main_layout.addWidget(check)
        return check

    def _emit(self, key, value):
        if not self._loading:
            self.changed.emit({key: value})

    def _schedule_card_resize(self):
        """ExpandSettingCard does not resize itself after child rows change."""
        if self._resize_pending:
            return
        self._resize_pending = True
        QTimer.singleShot(0, self._notify_expand_card)

    def _notify_expand_card(self):
        self._resize_pending = False
        if hasattr(self, "protection_rows"):
            self.protection_rows.activate()
            self.protection_body.layout().activate()
        if hasattr(self, "rules_layout"):
            self.rules_layout.activate()
        if hasattr(self, "body") and self.body.layout() is not None:
            self.body.layout().activate()
        self.main_layout.activate()
        parent = self.parentWidget()
        while parent is not None:
            if isinstance(parent, ExpandSettingCard):
                parent.viewLayout.invalidate()
                required = parent.viewLayout.sizeHint().height()
                if parent.spaceWidget.height() != required or (
                    parent.isExpand and parent.height() != parent.card.height() + required
                ):
                    parent._adjustViewSize()
                    parent.updateGeometry()
                return
            parent = parent.parentWidget()

    def _description(self, text, layout=None, parent=None):
        targets = [self]
        if self._last_note_target is not None:
            targets.append(self._last_note_target)
        label = HoverNoteLabel(text, self, targets)
        self.explanation_notes.append(label)
        return label

    def bind_note_title(self, title):
        for note in self.explanation_notes:
            note.add_target(title)


class EgoReleaseRuleRow(QWidget):

    changed = Signal()

    removed = Signal(object)

    moved = Signal(object, int)



    def __init__(self, rule, parent=None):

        super().__init__(parent)

        rule = rule.model_dump() if hasattr(rule, "model_dump") else dict(rule)

        layout = QVBoxLayout(self)

        layout.setContentsMargins(0, 5, 0, 8)

        first = QHBoxLayout()

        self.enabled = CheckBox("启用", self)

        self.enabled.setChecked(rule.get("enabled", True))

        self.priority = QLabel(self)

        first.addWidget(self.enabled)

        first.addWidget(self.priority)

        first.addSpacing(10)

        first.addWidget(QLabel("TURN", self))

        self.turn = SpinBox(self)

        self.turn.setRange(1, 99)

        self.turn.setFixedWidth(128)

        self.turn.setValue(rule.get("turn", 1))

        first.addWidget(self.turn)

        first.addSpacing(8)

        self.mode = ComboBox(self)

        self.mode.addItems(["觉醒", "侵蚀"])

        self.mode.setCurrentIndex(rule.get("mode", 1))

        self.mode.setFixedWidth(100)

        first.addWidget(self.mode)

        first.addStretch(1)

        self.up_button = PushButton("上移", self)

        self.down_button = PushButton("下移", self)

        self.remove_button = PushButton("删除", self)

        for button in (self.up_button, self.down_button, self.remove_button):

            button.setFixedWidth(66)

            first.addWidget(button)

        layout.addLayout(first)

        second = QHBoxLayout()

        self.name_label = QLabel("EGO 完整名称", self)

        set_hover_note(self.name_label, "name", "填写觉醒名称；与游戏语言一致的觉醒完整名称。")

        second.addWidget(self.name_label)

        self.name = LineEdit(self)

        self.name.setPlaceholderText("EGO 完整名称")

        set_hover_note(self.name, "name", "填写觉醒名称；与游戏语言一致的觉醒完整名称。")

        self.name.setText(rule.get("name", ""))

        second.addWidget(self.name, 1)

        layout.addLayout(second)

        self.enabled.toggled.connect(self._enabled_changed)

        self.turn.valueChanged.connect(lambda _: self.changed.emit())

        self.mode.currentIndexChanged.connect(lambda _: self.changed.emit())

        self.name.textChanged.connect(lambda _: self.changed.emit())

        self.remove_button.clicked.connect(lambda: self.removed.emit(self))

        self.up_button.clicked.connect(lambda: self.moved.emit(self, -1))

        self.down_button.clicked.connect(lambda: self.moved.emit(self, 1))

        self._enabled_changed(self.enabled.isChecked())



    def _enabled_changed(self, enabled):

        for control in (self.turn, self.mode, self.name):

            control.setEnabled(enabled)

        self.changed.emit()



    def value(self):

        return {

            "enabled": self.enabled.isChecked(),

            "turn": self.turn.value(),

            "name": self.name.text(),

            "mode": self.mode.currentIndex(),

        }



class EgoReleaseOptions(TeamOptionWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("EgoReleaseOptions")
        self.rule_rows = []
        self.body = QWidget(self)
        self.body.installEventFilter(self)
        body_layout = QVBoxLayout(self.body)
        body_layout.setContentsMargins(20, 0, 0, 0)
        self._description("在指定回合按列表顺序尝试释放指定ego，名称需严格与游戏内语言的觉醒ego相同")
        self._check("rabbit_ego_enabled", "启用 EGO 释放", self.body)
        self.rules_layout = QVBoxLayout()
        self.rules_layout.setSpacing(8)
        body_layout.addLayout(self.rules_layout)
        self.add_rule_button = PushButton("添加 EGO 规则", self.body)
        self.add_rule_button.clicked.connect(self.add_rule)
        body_layout.addWidget(self.add_rule_button, 0, Qt.AlignmentFlag.AlignLeft)
        self.main_layout.addWidget(self.body)

    def add_rule(self, rule=None):
        if rule is None or isinstance(rule, bool):
            rule = {"enabled": True, "turn": 1, "name": "", "mode": 1}
        row = EgoReleaseRuleRow(rule, self.body)
        row.installEventFilter(self)
        row.changed.connect(self._rules_changed)
        row.removed.connect(self.remove_rule)
        row.moved.connect(self.move_rule)
        self.rule_rows.append(row)
        self.rules_layout.addWidget(row)
        self._refresh_priority()
        self._rules_changed()
        self._schedule_card_resize()

    def remove_rule(self, row):
        self.rule_rows.remove(row)
        self.rules_layout.removeWidget(row)
        row.deleteLater()
        self._refresh_priority()
        self._rules_changed()
        self._schedule_card_resize()

    def move_rule(self, row, step):
        index = self.rule_rows.index(row)
        destination = index + step
        if not 0 <= destination < len(self.rule_rows):
            return
        self.rule_rows[index], self.rule_rows[destination] = self.rule_rows[destination], self.rule_rows[index]
        self.rules_layout.removeWidget(row)
        self.rules_layout.insertWidget(destination, row)
        self._refresh_priority()
        self._rules_changed()

    def _refresh_priority(self):
        for index, row in enumerate(self.rule_rows):
            row.priority.setText(f"优先级 {index + 1}")
            row.up_button.setEnabled(index > 0)
            row.down_button.setEnabled(index + 1 < len(self.rule_rows))

    def _rules_changed(self):
        self._emit("rabbit_ego_rules", [row.value() for row in self.rule_rows])

    def load_settings(self, team):
        self._loading = True
        try:
            self.checks["rabbit_ego_enabled"].setChecked(team.rabbit_ego_enabled)
            for row in list(self.rule_rows):
                self.remove_rule(row)
            for rule in team.rabbit_ego_rules:
                self.add_rule(rule)
        finally:
            self._loading = False
        self.body.setEnabled(team.rabbit_ego_enabled)
        self._schedule_card_resize()

    def settings(self):
        return {
            "rabbit_ego_enabled": self.checks["rabbit_ego_enabled"].isChecked(),
            "rabbit_ego_rules": [row.value() for row in self.rule_rows],
        }


class TeamAutomationOptions(TeamOptionWidget):
    """Team advanced settings, separate from gifts and event participation."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("TeamAutomationOptions")
        self.retry_body = QWidget(self)
        retry_layout = QHBoxLayout(self.retry_body)
        retry_layout.setContentsMargins(20, 0, 0, 0)
        self._check("battle_retry_limit_enabled", "限制本关尝试次数", self.retry_body)
        set_hover_note(self.checks["battle_retry_limit_enabled"], "limit", "耗尽后放弃本局及奖励，扣一次计划次数。")
        limit_label = QLabel("本关最多尝试", self.retry_body)
        set_hover_note(limit_label, "limit", "包含初次战斗。")
        retry_layout.addWidget(limit_label)
        self.retry_limit = SpinBox(self.retry_body)
        self.retry_limit.setRange(1, 20)
        self.retry_limit.setValue(4)
        self.retry_limit.valueChanged.connect(lambda value: self._emit("battle_max_attempts", value))
        retry_layout.addWidget(self.retry_limit)
        retry_layout.addStretch(1)
        self.main_layout.addWidget(self.retry_body)

    def load_settings(self, team):
        self._loading = True
        try:
            self.checks["battle_retry_limit_enabled"].setChecked(team.battle_retry_limit_enabled)
            self.retry_limit.setValue(team.battle_max_attempts)
        finally:
            self._loading = False
        self.retry_body.setEnabled(team.battle_retry_limit_enabled)
        self._schedule_card_resize()

    def settings(self):
        return {"battle_retry_limit_enabled": self.checks["battle_retry_limit_enabled"].isChecked(),
                "battle_max_attempts": self.retry_limit.value()}


class RouteWeightOptions(TeamOptionWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("RouteWeightOptions")
        self.body = QWidget(self)
        layout = QVBoxLayout(self.body)
        layout.setContentsMargins(20, 0, 0, 0)
        self._check("route_weights_enabled", "使用自定义寻路权重", self.body)
        self._description("脚本会优先避开权重高的节点；快捷寻路开启时不生效", layout, self.body)
        grid = QGridLayout()
        self.weights = {}
        for index, (key, label) in enumerate(ROUTE_NODE_LABELS.items()):
            spin = SpinBox(self.body)
            spin.setRange(0, 999)
            spin.setFixedWidth(130)
            self.weights[key] = spin
            spin.valueChanged.connect(lambda _: self._emit("route_node_weights", self._values()))
            grid.addWidget(QLabel(label, self.body), index // 2, (index % 2) * 2)
            grid.addWidget(spin, index // 2, (index % 2) * 2 + 1)
        layout.addLayout(grid)
        self.main_layout.addWidget(self.body)

    def _values(self):
        return {key: control.value() for key, control in self.weights.items()}

    def load_settings(self, team):
        self._loading = True
        try:
            self.checks["route_weights_enabled"].setChecked(team.route_weights_enabled)
            for key, control in self.weights.items():
                control.setValue(team.route_node_weights[key])
        finally:
            self._loading = False
        self.body.setEnabled(team.route_weights_enabled)
        self._schedule_card_resize()

    def settings(self):
        return {"route_weights_enabled": self.checks["route_weights_enabled"].isChecked(),
                "route_node_weights": self._values()}


class GiftImageOptions(TeamOptionWidget):
    def __init__(self, enabled_key, paths_key, title, description, parent=None):
        super().__init__(parent)
        self.enabled_key, self.paths_key = enabled_key, paths_key
        self.dialog_title = "添加饰品图片"
        self.image_folder = "assets/user/gift_lock"
        self.protection_body = QWidget(self)
        self.protection_body.installEventFilter(self)
        protection_layout = QVBoxLayout(self.protection_body)
        protection_layout.setContentsMargins(20, 0, 0, 0)
        self._check(enabled_key, title, self.protection_body)
        self._description(description, protection_layout, self.protection_body)
        self.protected_paths = []
        self.protection_rows = QVBoxLayout()
        protection_layout.addLayout(self.protection_rows)
        self.add_protection_button = PushButton("添加饰品图片", self.protection_body)
        self.add_protection_button.clicked.connect(self._choose_protection_images)
        protection_layout.addWidget(self.add_protection_button, 0, Qt.AlignmentFlag.AlignLeft)
        self.protection_status = QLabel(self.protection_body)
        self.protection_status.setWordWrap(True)
        protection_layout.addWidget(self.protection_status)
        self.main_layout.addWidget(self.protection_body)

    def _choose_protection_images(self):
        files, _ = QFileDialog.getOpenFileNames(self, self.dialog_title, "", "图片 (*.png *.webp *.jpg *.jpeg *.bmp)")
        errors = []
        for filename in files:
            try:
                path = import_gift_image(filename, self.image_folder)
                if path not in self.protected_paths:
                    self.protected_paths.append(path)
            except Exception as error:
                errors.append(f"{Path(filename).name}：{error}")
        self._rebuild_protection_rows()
        self.protection_status.setText("；".join(errors))
        self._emit(self.paths_key, self.protected_paths[:])

    def _remove_protection_image(self, path):
        self.protected_paths.remove(path)
        self._rebuild_protection_rows()
        self._emit(self.paths_key, self.protected_paths[:])

    def _rebuild_protection_rows(self):
        while self.protection_rows.count():
            item = self.protection_rows.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for path in self.protected_paths:
            row = QWidget(self.protection_body)
            row.installEventFilter(self)
            layout = QHBoxLayout(row)
            layout.setContentsMargins(0, 0, 0, 0)
            preview = QLabel(row)
            preview.setFixedSize(64, 64)
            pixmap = QPixmap(path)
            if not pixmap.isNull():
                preview.setPixmap(pixmap.scaled(60, 60, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            else:
                preview.setText("图片缺失")
            label = QLabel(Path(path).stem.split("_", 1)[-1], row)
            label.setWordWrap(True)
            label.setToolTip(path)
            button = PushButton("删除", row)
            button.clicked.connect(lambda checked=False, path=path: self._remove_protection_image(path))
            layout.addWidget(preview)
            layout.addWidget(label, 1)
            layout.addWidget(button)
            self.protection_rows.addWidget(row)
        self._schedule_card_resize()


    def load_settings(self, team):
        self._loading = True
        try:
            self.checks[self.enabled_key].setChecked(getattr(team, self.enabled_key))
            self.protected_paths = list(getattr(team, self.paths_key))
            self._rebuild_protection_rows()
        finally:
            self._loading = False
        self.protection_body.setEnabled(getattr(team, self.enabled_key))
        self._schedule_card_resize()

    def settings(self):
        return {self.enabled_key: self.checks[self.enabled_key].isChecked(), self.paths_key: self.protected_paths[:]}


class GiftLockOptions(GiftImageOptions):
    def __init__(self, parent=None):
        super().__init__("gift_lock_enabled", "gift_lock_images", "启用饰品锁定",
                         "优先在商店购买该饰品；不使用该饰品合成。\n"
                         "沿用出售保护；仍遵守不购买饰品与忽略商店设置。可添加多张图片，关闭后保留列表。\n"
                         "请使用未选中、无金色边框的饰品截图。", parent)
        self.setObjectName("GiftLockOptions")


class EventOptions(TeamOptionWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("EventOptions")
        self.event_body = QWidget(self)
        event_layout = QVBoxLayout(self.event_body)
        event_layout.setContentsMargins(20, 0, 0, 0)
        self._check("rabbit_event_exclusion_enabled", "避免指定罪人参与事件", self.event_body)
        self.event_status = self._description(
            "单击卡面切换；亮起表示禁止参与事件，最多选择 11 人。", event_layout, self.event_body
        )
        grid = QGridLayout()
        grid.setSpacing(8)
        self.event_cards = []
        for index in range(12):
            card = ExcludedSinnerCard(index, self.event_body)
            card.toggled.connect(lambda checked, index=index: self._event_toggled(index, checked))
            self.event_cards.append(card)
            grid.addWidget(card, index // 6, index % 6)
        grid.setAlignment(Qt.AlignmentFlag.AlignLeft)
        event_layout.addLayout(grid)
        self.main_layout.addWidget(self.event_body)

    def _event_toggled(self, index, checked):
        if self._loading:
            return
        selected = [i for i, card in enumerate(self.event_cards) if card.isChecked()]
        if len(selected) > 11:
            card = self.event_cards[index]
            card.blockSignals(True)
            card.setChecked(False)
            card.blockSignals(False)
            self.event_status.setText("最多禁止 11 人，必须保留至少 1 人参与事件。")
            return
        self.event_status.setText(f"已禁止 {len(selected)} 人参与事件；亮起表示禁止，最多 11 人。")
        self._emit("rabbit_event_excluded", selected)


    def load_settings(self, team):
        self._loading = True
        try:
            self.checks["rabbit_event_exclusion_enabled"].setChecked(team.rabbit_event_exclusion_enabled)
            for index, card in enumerate(self.event_cards):
                card.setChecked(index in team.rabbit_event_excluded)
            self.event_status.setText(f"已禁止 {len(team.rabbit_event_excluded)} 人参与事件；亮起表示禁止，最多 11 人。")
        finally:
            self._loading = False
        self.event_body.setEnabled(team.rabbit_event_exclusion_enabled)
        self._schedule_card_resize()

    def settings(self):
        return {"rabbit_event_exclusion_enabled": self.checks["rabbit_event_exclusion_enabled"].isChecked(),
                "rabbit_event_excluded": [i for i, card in enumerate(self.event_cards) if card.isChecked()]}


class ThemeObservationOptions(TeamOptionWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ThemeObservationOptions")
        self.rule_rows = []
        self.body = QWidget(self)
        self.body.installEventFilter(self)
        body_layout = QVBoxLayout(self.body)
        body_layout.setContentsMargins(20, 0, 0, 0)
        self._check("rabbit_observe_enabled", "启用主题卡包观测", self.body)
        self._description(
            "仅在刷新次数为 0 且当前所有卡包权重为负数时触发。按楼层配置观测目标；确认无效时取消，放弃本局及奖励，并扣一次计划次数。",
            body_layout,
            self.body,
        )
        self.rules_layout = QVBoxLayout()
        self.rules_layout.setSpacing(8)
        body_layout.addLayout(self.rules_layout)
        self.rule_status = self._description("每层最多一个目标；行、列从 1 开始。", body_layout, self.body)
        self.add_rule_button = PushButton("添加楼层目标", self.body)
        self.add_rule_button.clicked.connect(self.add_rule)
        body_layout.addWidget(self.add_rule_button, 0, Qt.AlignmentFlag.AlignLeft)
        self.main_layout.addWidget(self.body)

    def add_rule(self, rule=None):
        if isinstance(rule, bool):
            rule = None
        used = {row.floor.value() for row in self.rule_rows}
        if rule is None:
            floor = next((floor for floor in range(1, 6) if floor not in used), None)
            if floor is None:
                return
            rule = [floor, 1, 1]
        row = ObservePackRuleRow(rule, self.body)
        row.changed.connect(lambda: self._rules_changed(row))
        row.removed.connect(self.remove_rule)
        self.rule_rows.append(row)
        self.rules_layout.addWidget(row)
        self.add_rule_button.setEnabled(len(self.rule_rows) < 5)
        self._emit("rabbit_observe_rules", self.observation_rules())
        self._schedule_card_resize()

    def remove_rule(self, row):
        self.rule_rows.remove(row)
        self.rules_layout.removeWidget(row)
        row.deleteLater()
        self.add_rule_button.setEnabled(True)
        self._emit("rabbit_observe_rules", self.observation_rules())
        self._schedule_card_resize()

    def _rules_changed(self, changed_row):
        floor = changed_row.floor.value()
        if any(row is not changed_row and row.floor.value() == floor for row in self.rule_rows):
            changed_row.floor.blockSignals(True)
            changed_row.floor.setValue(changed_row._accepted_floor)
            changed_row.floor.blockSignals(False)
            self.rule_status.setText("这个楼层已有目标，请先删除原目标，或选择其他楼层。")
            return
        changed_row._accepted_floor = floor
        self.rule_status.setText("每层最多一个目标；行、列从 1 开始。")
        self._emit("rabbit_observe_rules", self.observation_rules())

    def observation_rules(self):
        return [row.value() for row in self.rule_rows]

    def load_settings(self, team):
        self._loading = True
        try:
            self.checks["rabbit_observe_enabled"].setChecked(team.rabbit_observe_enabled)
            for row in list(self.rule_rows):
                self.remove_rule(row)
            for rule in team.rabbit_observe_rules:
                self.add_rule(rule)
        finally:
            self._loading = False
        self.body.setEnabled(team.rabbit_observe_enabled)
        self._schedule_card_resize()

    def settings(self):
        return {
            "rabbit_observe_enabled": self.checks["rabbit_observe_enabled"].isChecked(),
            "rabbit_observe_rules": self.observation_rules(),
        }
