from html import escape

from PySide6.QtCore import QT_TRANSLATE_NOOP, QEvent, QObject, QPoint, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QCursor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout
from qfluentwidgets import StyleSheetBase, Theme, isDarkTheme, setStyleSheet

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


class InlineThemeStyleSheet(StyleSheetBase):
    """Inline light/dark QSS managed by qfluentwidgets' theme style manager."""

    def __init__(self, light_qss: str, dark_qss: str):
        super().__init__()
        self.light_qss = light_qss
        self.dark_qss = dark_qss

    def content(self, theme=Theme.AUTO) -> str:
        if theme == Theme.AUTO:
            return self.dark_qss if isDarkTheme() else self.light_qss
        return self.light_qss if theme == Theme.LIGHT else self.dark_qss


def _set_custom_theme_style(widget, light_qss: str, dark_qss: str):
    setStyleSheet(widget, InlineThemeStyleSheet(light_qss, dark_qss))


def _format_starlight_tip(title: str, tip_text: str) -> str:
    tip_text = "\n".join(tip_text.splitlines()[1:])
    text_color = "rgba(255, 255, 255, 0.92)" if isDarkTheme() else "rgba(0, 0, 0, 0.82)"
    html = escape(tip_text).replace("\\yellow{+}", '<span style="color:#d8a300;font-weight:700;">+</span>')
    html = html.replace("\n", "<br>")
    return (
        f'<div style="white-space:nowrap; font-size:12px; line-height:1.45; color:{text_color};">'
        f'<b>{escape(title)}</b><br>{html}'
        "</div>"
    )


class StarlightToolTipPopup(QLabel):
    def __init__(self):
        super().__init__(None, Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint)
        self.setTextFormat(Qt.TextFormat.RichText)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setMargin(0)

    def show_text(self, pos: QPoint, text: str):
        self.setText(text)
        self.__apply_theme_style()
        self.adjustSize()
        self.move(pos)
        self.show()

    def __apply_theme_style(self):
        if isDarkTheme():
            background = "rgb(45, 45, 45)"
            border = "rgba(255, 255, 255, 46)"
            text = "rgba(255, 255, 255, 0.92)"
        else:
            background = "rgb(255, 255, 255)"
            border = "rgba(0, 0, 0, 38)"
            text = "rgba(0, 0, 0, 0.82)"

        self.setStyleSheet(
            f"""
            QLabel {{
                background-color: {background};
                border: 1px solid {border};
                border-radius: 6px;
                color: {text};
                padding: 6px 8px;
            }}
            """
        )


_starlight_tooltip_popup = None


def _get_starlight_tooltip_popup() -> StarlightToolTipPopup:
    global _starlight_tooltip_popup
    if _starlight_tooltip_popup is None:
        _starlight_tooltip_popup = StarlightToolTipPopup()
    return _starlight_tooltip_popup


class DelayedRichToolTipFilter(QObject):
    def __init__(self, text, parent=None):
        super().__init__(parent)
        self.text = text
        self.widget = None
        self.global_pos = None
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(500)
        self.timer.timeout.connect(self.__show_tooltip)

    def set_text(self, text):
        self.text = text

    def eventFilter(self, obj, event):
        event_type = event.type()
        if event_type in (QEvent.Type.Enter, QEvent.Type.HoverEnter):
            _get_starlight_tooltip_popup().hide()
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
            _get_starlight_tooltip_popup().hide()
        return super().eventFilter(obj, event)

    def __show_tooltip(self):
        if self.widget is None:
            return
        cursor_pos = QCursor.pos()
        if not self.widget.rect().contains(self.widget.mapFromGlobal(cursor_pos)):
            return
        pos = (self.global_pos or cursor_pos) + QPoint(12, 18)
        text = self.text() if callable(self.text) else self.text
        _get_starlight_tooltip_popup().show_text(pos, text)


class StarlightNameButton(QPushButton):
    def __init__(self, text: str, cost: int, parent=None):
        super().__init__(text, parent)
        self.cost_label = QLabel(self)
        self.cost_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
        self.cost_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.apply_cost_style()
        self.set_cost(cost)

    def apply_cost_style(self):
        light_qss = """
            QLabel {
                background: transparent;
                border: none;
                color: rgba(0, 0, 0, 0.82);
                font-size: 11px;
                font-weight: 500;
            }
        """
        dark_qss = """
            QLabel {
                background: transparent;
                border: none;
                color: rgba(255, 255, 255, 0.92);
                font-size: 11px;
                font-weight: 500;
            }
        """
        _set_custom_theme_style(
            self.cost_label,
            light_qss,
            dark_qss,
        )

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

    _BASE_STYLE = """
        QPushButton {
            border: none;
            background: transparent;
            padding: 5px 6px;
            min-height: 32px;
            color: __TEXT_COLOR__;
            font-size: 13px;
        }
        QPushButton:hover {
            background: transparent;
        }
        QPushButton:checked {
            color: __TEXT_COLOR__;
        }
        QPushButton[segment="left"] {
            padding-right: 24px;
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
        self.__apply_theme_style()
        self.__refresh_tooltips(label_text)

    def __create_button(self, text: str, segment: str) -> QPushButton:
        if segment == "left":
            button = StarlightNameButton(text, self.base_cost, self)
        else:
            button = QPushButton(text, self)
        button.setFlat(True)
        button.setCheckable(True)
        button.setMouseTracking(True)
        button.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setProperty("segment", segment)
        return button

    def __apply_theme_style(self):
        light_style = self._BASE_STYLE.replace("__TEXT_COLOR__", "rgba(0, 0, 0, 0.82)")
        dark_style = self._BASE_STYLE.replace("__TEXT_COLOR__", "rgba(255, 255, 255, 0.92)")

        for button in (self.default_button, self.level_one_button, self.level_two_button):
            _set_custom_theme_style(button, light_style, dark_style)
        _set_custom_theme_style(self, "StarlightLevelSelector { background: transparent; }", "StarlightLevelSelector { background: transparent; }")
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        colors = self.__theme_colors()

        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        radius = 5
        path = QPainterPath()
        path.addRoundedRect(rect, radius, radius)

        painter.save()
        painter.setClipPath(path)
        self.__fill_segment(painter, 0, self.default_button.geometry().right() + 1, self.__segment_color(0, colors))
        self.__fill_segment(
            painter,
            self.level_one_button.geometry().x(),
            self.level_one_button.geometry().right() + 1,
            self.__segment_color(1, colors),
        )
        self.__fill_segment(
            painter,
            self.level_two_button.geometry().x(),
            self.width(),
            self.__segment_color(2, colors),
        )
        painter.restore()

        painter.setPen(QPen(colors["border"], 1))
        painter.drawPath(path)
        for x in (self.level_one_button.geometry().x(), self.level_two_button.geometry().x()):
            painter.fillRect(QRectF(x, 1, 1, self.height() - 2), colors["divider"])

    def __fill_segment(self, painter: QPainter, left: int, right: int, color: QColor):
        if right <= left:
            return
        painter.fillRect(QRectF(left, 0, right - left, self.height()), color)

    def __segment_color(self, segment_level: int, colors: dict[str, QColor]) -> QColor:
        if not self.selected or self.level < segment_level:
            return colors["empty"]
        return (colors["left"], colors["middle"], colors["right"])[segment_level]

    def __theme_colors(self) -> dict[str, QColor]:
        default_line_color = QColor(120, 120, 120, 105)
        if isDarkTheme():
            return {
                "border": default_line_color,
                "divider": default_line_color,
                "empty": QColor(255, 255, 255, 18),
                "left": QColor(255, 182, 193, 70),
                "middle": QColor(214, 96, 96, 88),
                "right": QColor(170, 32, 44, 130),
            }
        return {
            "border": default_line_color,
            "divider": default_line_color,
            "empty": QColor(120, 120, 120, 20),
            "left": QColor(255, 143, 161, 150),
            "middle": QColor(224, 76, 76, 175),
            "right": QColor(190, 38, 52, 195),
        }

    def __refresh_tooltips(self, title: str):
        tips = STARLIGHT_BONUS_TIPS[self.starlight_index - 1]
        self.__set_button_tooltip(self.default_button, lambda title=title: _format_starlight_tip(title, tips["buff"]))
        self.__set_button_tooltip(self.level_one_button, lambda title=title: _format_starlight_tip(title, tips["buff+"]))
        self.__set_button_tooltip(self.level_two_button, lambda title=title: _format_starlight_tip(title, tips["buff++"]))

    def __set_button_tooltip(self, button: QPushButton, text):
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
        self.update()

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
