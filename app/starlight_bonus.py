from html import escape

from PySide6.QtCore import QT_TRANSLATE_NOOP, QEvent, QObject, QPoint, Qt, QTimer
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QToolTip, QVBoxLayout

from app import mediator
from module.config import cfg

STARLIGHT_BONUS_NAMES = [
    QT_TRANSLATE_NOOP("CustomizeSettingsModule", "起始之星"),
    QT_TRANSLATE_NOOP("CustomizeSettingsModule", "层积星云"),
    QT_TRANSLATE_NOOP("CustomizeSettingsModule", "星际旅行"),
    QT_TRANSLATE_NOOP("CustomizeSettingsModule", "倾落的流星雨"),
    QT_TRANSLATE_NOOP("CustomizeSettingsModule", "双星商店"),
    QT_TRANSLATE_NOOP("CustomizeSettingsModule", "卫星商店"),
    QT_TRANSLATE_NOOP("CustomizeSettingsModule", "星云的宠爱"),
    QT_TRANSLATE_NOOP("CustomizeSettingsModule", "星芒的引导"),
    QT_TRANSLATE_NOOP("CustomizeSettingsModule", "偶然的彗星"),
    QT_TRANSLATE_NOOP("CustomizeSettingsModule", "全面的可能性"),
]

STARLIGHT_BONUS_COSTS = [10, 10, 20, 20, 30, 30, 40, 40, 50, 60]

STARLIGHT_BONUS_TIPS = [
    {
        "buff": "buff：\n经费+\n卡包+\n饰品+\n刷新+",
        "buff+": "buff+：\n经费+\\yellow{+}\n卡包+\n饰品+\n刷新+",
        "buff++": "buff++：\n经费+\\yellow{+}\n卡包+\n饰品+\n刷新+\\yellow{+}",
    },
    {
        "buff": "buff：\n过层经费+\n售卖经费+",
        "buff+": "buff+：\n过层经费+\\yellow{+}\n售卖经费+\\yellow{+}",
        "buff++": "buff++：\n过层经费+\\yellow{+}\\yellow{+}\n售卖经费+\\yellow{+}\\yellow{+}",
    },
    {
        "buff": "buff：\n卡包+\n卡包刷新+\n人格等级+",
        "buff+": "buff+：\n卡包+\n卡包刷新+\\yellow{+}\n人格等级+\n拼点\\yellow{+}",
        "buff++": "buff++：\n卡包+\n卡包刷新+\\yellow{+}\\yellow{+}\n人格等级+\n拼点\\yellow{+}\\yellow{+}",
    },
    {
        "buff": "buff：\n经费+\n饰品选择+",
        "buff+": "buff+：\n经费+\\yellow{+}\n饰品选择+\n星芒经费\\yellow{+}",
        "buff++": "buff++：\n经费+\\yellow{+}\\yellow{+}\n饰品选择+\n星芒经费\\yellow{+}",
    },
    {
        "buff": "buff：\n商店饰品+\n战斗经费+\n高级饰品+",
        "buff+": "buff+：\n商店饰品+\n战斗经费+\\yellow{+}\n高级饰品+\n商店经费\\yellow{+}",
        "buff++": "buff++：\n商店饰品+\n战斗经费+\\yellow{+}\\yellow{+}\n高级饰品+\n商店经费\\yellow{+}",
    },
    {
        "buff": "buff：\n关键词刷新+\n初始饰品+",
        "buff+": "buff+：\n关键词刷新+\n初始饰品+\\yellow{+}\n特殊商店\\yellow{+}",
        "buff++": "buff++：\n关键词刷新+\\yellow{+}\n初始饰品+\\yellow{+}\n特殊商店\\yellow{+}\\yellow{+}",
    },
    {
        "buff": "buff：\n初始等级+\n过层等级+",
        "buff+": "buff+：\n初始等级+\n过层等级+\\yellow{+}",
        "buff++": "buff++：\n初始等级+\n六层等级\\yellow{+}\n过层等级+\\yellow{+}",
    },
    {
        "buff": "buff：\n速度+\n拼点+\n伤害+\n守护+",
        "buff+": "buff+：\n速度+\\yellow{+}\n拼点+\n伤害+\n守护+",
        "buff++": "buff++：\n速度+\\yellow{+}\\yellow{+}\n拼点+\n伤害+\n守护+",
    },
    {
        "buff": "buff：\n商店饰品+\n三层饰品+\n合成饰品+",
        "buff+": "buff+：\n商店饰品+\\yellow{+}\n三层饰品+\n五层饰品\\yellow{+}\n合成饰品+",
        "buff++": "buff++：\n商店饰品+\\yellow{+}\n三层饰品+\n五层饰品\\yellow{+}\n七层饰品\\yellow{+}\n合成饰品+\\yellow{+}",
    },
    {
        "buff": "buff：\n卡包+\n饰品选择+\n关键词饰品+\n黯淡残影+",
        "buff+": "buff+：\n饰品选择+\n关键词饰品+\\yellow{+}\n黯淡残影+\n微茫残影\\yellow{+}",
        "buff++": "buff++：\n卡包+\n饰品选择+\n关键词饰品+\\yellow{+}\\yellow{+}\n黯淡残影+\n微茫残影\\yellow{+}\n闪耀残影\\yellow{+}",
    },
]


def _format_starlight_tip(title: str, tip_text: str) -> str:
    tip_text = "\n".join(tip_text.splitlines()[1:])
    html = escape(tip_text).replace("\\yellow{+}", '<span style="color:#d8a300;font-weight:700;">+</span>')
    html = html.replace("\n", "<br>")
    return (
        '<div style="white-space:nowrap; font-size:12px; line-height:1.45;">'
        f'<b>{escape(title)}</b><br>{html}'
        "</div>"
    )


class DelayedRichToolTipFilter(QObject):
    def __init__(self, text: str, parent=None):
        super().__init__(parent)
        self.text = text
        self.widget = None
        self.global_pos = None
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(500)
        self.timer.timeout.connect(self.__show_tooltip)

    def set_text(self, text: str):
        self.text = text

    def eventFilter(self, obj, event):
        event_type = event.type()
        if event_type in (QEvent.Type.Enter, QEvent.Type.HoverEnter):
            QToolTip.hideText()
            self.widget = obj
            self.global_pos = QCursor.pos()
            self.timer.stop()
            self.timer.start()
        elif event_type in (QEvent.Type.MouseMove, QEvent.Type.HoverMove):
            self.global_pos = QCursor.pos()
        elif event_type in (
            QEvent.Type.Leave,
            QEvent.Type.HoverLeave,
            QEvent.Type.MouseButtonPress,
            QEvent.Type.Hide,
        ):
            self.timer.stop()
            QToolTip.hideText()
        return super().eventFilter(obj, event)

    def __show_tooltip(self):
        if self.widget is None:
            return
        cursor_pos = QCursor.pos()
        if not self.widget.rect().contains(self.widget.mapFromGlobal(cursor_pos)):
            return
        pos = (self.global_pos or cursor_pos) + QPoint(12, 18)
        QToolTip.showText(pos, self.text, self.widget)


class StarlightNameButton(QPushButton):
    def __init__(self, text: str, cost: int, parent=None):
        super().__init__(text, parent)
        self.cost_label = QLabel(self)
        self.cost_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
        self.cost_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.cost_label.setStyleSheet(
            """
            QLabel {
                background: transparent;
                border: none;
                color: palette(text);
                font-size: 10px;
                font-weight: 500;
            }
            """
        )
        self.set_cost(cost)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.__place_cost_label()

    def set_cost(self, cost: int):
        self.cost_label.setText(str(cost))
        self.__place_cost_label()

    def __place_cost_label(self):
        width = max(28, self.cost_label.fontMetrics().horizontalAdvance(self.cost_label.text()) + 6)
        self.cost_label.setGeometry(max(0, self.width() - width - 4), 2, width, 14)


class StarlightLevelSelector(QFrame):
    """A three-part selector for default, +, and ++ starlight levels."""

    _STYLE = """
        QPushButton {
            border: 1px solid rgba(120, 120, 120, 105);
            background: rgba(120, 120, 120, 20);
            padding: 5px 6px;
            min-height: 32px;
            color: palette(text);
            font-size: 12px;
        }
        QPushButton:hover {
            background: rgba(0, 120, 212, 28);
        }
        QPushButton:checked {
            color: palette(text);
            font-weight: 600;
        }
        QPushButton[segment="left"] {
            border-top-left-radius: 5px;
            border-bottom-left-radius: 5px;
            border-top-right-radius: 0;
            border-bottom-right-radius: 0;
            padding-right: 24px;
        }
        QPushButton[segment="middle"] {
            border-left: 0;
            border-radius: 0;
        }
        QPushButton[segment="right"] {
            border-left: 0;
            border-top-left-radius: 0;
            border-bottom-left-radius: 0;
            border-top-right-radius: 5px;
            border-bottom-right-radius: 5px;
        }
        QPushButton[segment="left"]:checked {
            border-color: rgba(224, 132, 148, 165);
            background: rgba(255, 182, 193, 70);
        }
        QPushButton[segment="middle"]:checked {
            border-color: rgba(204, 76, 76, 180);
            background: rgba(214, 96, 96, 88);
        }
        QPushButton[segment="right"]:checked {
            border-color: rgba(150, 20, 32, 210);
            background: rgba(150, 20, 32, 120);
        }
    """

    def __init__(self, config_name: str, label_text: str, parent=None):
        super().__init__(parent)
        self.setObjectName(config_name)
        self.config_name = config_name
        self.starlight_index = int(config_name.split("_")[-1])
        self.base_cost = STARLIGHT_BONUS_COSTS[self.starlight_index - 1]
        self.selected = False
        self.level = 0

        self.segment_layout = QHBoxLayout(self)
        self.segment_layout.setContentsMargins(0, 0, 0, 0)
        self.segment_layout.setSpacing(0)

        self.default_button = self.__create_button(label_text, "left")
        self.level_one_button = self.__create_button("+", "middle")
        self.level_two_button = self.__create_button("++", "right")

        self.segment_layout.addWidget(self.default_button, 13)
        self.segment_layout.addWidget(self.level_one_button, 4)
        self.segment_layout.addWidget(self.level_two_button, 4)

        self.default_button.clicked.connect(lambda _checked=False: self.__on_segment_clicked(0))
        self.level_one_button.clicked.connect(lambda _checked=False: self.__on_segment_clicked(1))
        self.level_two_button.clicked.connect(lambda _checked=False: self.__on_segment_clicked(2))
        self.__refresh_tooltips(label_text)

    def __create_button(self, text: str, segment: str) -> QPushButton:
        if segment == "left":
            button = StarlightNameButton(text, self.base_cost, self)
        else:
            button = QPushButton(text, self)
        button.setCheckable(True)
        button.setMouseTracking(True)
        button.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setProperty("segment", segment)
        button.setStyleSheet(self._STYLE)
        return button

    def __refresh_tooltips(self, title: str):
        tips = STARLIGHT_BONUS_TIPS[self.starlight_index - 1]
        self.__set_button_tooltip(self.default_button, _format_starlight_tip(title, tips["buff"]))
        self.__set_button_tooltip(self.level_one_button, _format_starlight_tip(title, tips["buff+"]))
        self.__set_button_tooltip(self.level_two_button, _format_starlight_tip(title, tips["buff++"]))

    def __set_button_tooltip(self, button: QPushButton, text: str):
        tooltip_filter = getattr(button, "_starlight_tooltip_filter", None)
        if tooltip_filter is None:
            tooltip_filter = DelayedRichToolTipFilter(text, button)
            button._starlight_tooltip_filter = tooltip_filter
            button.installEventFilter(tooltip_filter)
        else:
            tooltip_filter.set_text(text)

    def __on_segment_clicked(self, target_level: int):
        if target_level == 0:
            selected = not self.selected if self.selected and self.level == 0 else True
            level = 0
        elif self.selected and self.level == target_level:
            selected = True
            level = 0
        else:
            selected = True
            level = target_level

        self.set_state(selected, level)
        mediator.team_setting.emit({self.config_name: self.selected})
        mediator.team_setting.emit({f"starlight_level_{self.starlight_index}": self.level})

    def set_state(self, selected: bool, level: int):
        self.selected = selected
        self.level = max(0, min(level, 2)) if selected else 0

        self.default_button.setChecked(self.selected)
        self.level_one_button.setChecked(self.selected and self.level >= 1)
        self.level_two_button.setChecked(self.selected and self.level >= 2)
        self.default_button.set_cost(self.base_cost * (self.level + 1))

    def set_label_text(self, text: str):
        self.default_button.setText(text)
        self.__refresh_tooltips(text)


class StarlightCard(QFrame):
    def __init__(self, class_name: str, label_text: str, team_num: int, parent=None):
        super().__init__(parent)
        self.starlight_index: int = int(class_name.split("_")[-1])
        self.selected = False
        self.level = 0
        if team_config := cfg.config.teams.get(str(team_num)):
            self.selected = bool(team_config.opening_bonus[self.starlight_index - 1])
            self.level = team_config.opening_bonus_level[self.starlight_index - 1]

        self.label_text = label_text
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 0, 0, 0)
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        self.starlight_checkbox = StarlightLevelSelector(class_name, label_text, self)
        self.starlight_checkbox.set_state(self.selected, self.level)
        self.main_layout.addWidget(self.starlight_checkbox)
