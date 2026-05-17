from html import escape

from PySide6.QtCore import QEvent, QObject, QPoint, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QCursor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QVBoxLayout
from qfluentwidgets import StyleSheetBase, isDarkTheme, setCustomStyleSheet, setStyleSheet

from app import mediator
from app.common.ui_config import (
    STARLIGHT_BONUS_COSTS,
    STARLIGHT_BONUS_TIPS,
    get_starlight_cost_label_qss,
    get_starlight_level_button_qss,
    get_starlight_paint_colors,
    get_starlight_selector_qss,
    get_starlight_tooltip_qss,
)
from module.config import cfg


class EmptyStyleSheet(StyleSheetBase):
    """Empty style source used only to register plain Qt widgets for theme updates."""

    def content(self, theme=None) -> str:
        return ""


def _register_custom_style_widget(widget):
    if widget.property("_starlight_custom_style_registered"):
        return
    setStyleSheet(widget, EmptyStyleSheet())
    widget.setProperty("_starlight_custom_style_registered", True)


def _format_starlight_tip(title: str, tip_text: str) -> str:
    tip_text = "\n".join(tip_text.splitlines()[1:])
    html = escape(tip_text).replace("\\yellow{+}", '<span style="color:#d8a300;font-weight:700;">+</span>')
    html = html.replace("\n", "<br>")
    return (
        '<div style="white-space:nowrap; font-size:12px; line-height:1.45;">'
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
        self._apply_theme_style()
        self.adjustSize()
        self.move(pos)
        self.show()

    def _apply_theme_style(self):
        _register_custom_style_widget(self)
        light_qss, dark_qss = get_starlight_tooltip_qss()
        setCustomStyleSheet(self, light_qss, dark_qss)


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
        self._apply_theme_style()
        self.set_cost(cost)

    def _apply_theme_style(self):
        _register_custom_style_widget(self.cost_label)
        light_qss, dark_qss = get_starlight_cost_label_qss()
        setCustomStyleSheet(self.cost_label, light_qss, dark_qss)

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
        self._apply_theme_style()
        self.__refresh_tooltips(label_text)

    def __create_button(self, text: str, segment: str) -> QPushButton:
        if segment == "left":
            button = StarlightNameButton(text, self.base_cost, self)
        else:
            button = QPushButton(text, self)
        button.setFlat(True)
        button.setMinimumWidth(0)
        button.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Expanding)
        button.setCheckable(True)
        button.setMouseTracking(True)
        button.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setProperty("segment", segment)
        return button

    def _apply_theme_style(self):
        light_style, dark_style = get_starlight_level_button_qss()
        for button in (self.default_button, self.level_one_button, self.level_two_button):
            _register_custom_style_widget(button)
            setCustomStyleSheet(button, light_style, dark_style)

        _register_custom_style_widget(self)
        light_style, dark_style = get_starlight_selector_qss()
        setCustomStyleSheet(self, light_style, dark_style)
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
        return get_starlight_paint_colors(isDarkTheme())

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
