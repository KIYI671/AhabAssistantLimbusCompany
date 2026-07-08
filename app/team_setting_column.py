from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget
from qfluentwidgets import ScrollArea, SmoothMode, isDarkTheme, qconfig

from app.base_tools import BaseLabel
from app.common.ui_config import get_team_setting_blank_column_qss, get_team_setting_team_label_qss


class TeamSettingTeamLabel(QLabel):
    clicked = Signal(int)

    def __init__(self, team_number: int, parent=None):
        super().__init__(parent)
        self.team_number = team_number
        self.retranslateUi()
        self.setFixedWidth(100)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.apply_theme_style(False)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.rect().contains(event.position().toPoint()):
            self.clicked.emit(self.team_number)
        super().mouseReleaseEvent(event)

    def set_selected(self, selected: bool):
        self.apply_theme_style(selected)

    def apply_theme_style(self, selected: bool):
        light_qss, dark_qss = get_team_setting_team_label_qss(selected)
        self.setStyleSheet(dark_qss if isDarkTheme() else light_qss)

    def retranslateUi(self):
        self.setText(self.tr("编队") + str(self.team_number))


class TeamSettingBlankColumn(QFrame):
    """队伍设置页左侧编队列表栏。"""

    team_selected = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("TeamSettingBlankColumn")
        self.setFixedWidth(120)
        self.team_labels: dict[int, TeamSettingTeamLabel] = {}
        # 主题切换时用它恢复当前编队按钮的选中样式。
        self.current_team_number = 0

        self.layout_ = QVBoxLayout(self)
        self.layout_.setContentsMargins(0, 0, 0, 0)
        self.layout_.setSpacing(0)

        self.title_label = BaseLabel("编队", self)
        self.title_label.setObjectName("teamSettingTitleLabel")
        self.title_label.hBoxLayout.setContentsMargins(0, 0, 0, 0)
        self.title_label.hBoxLayout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout_.addWidget(self.title_label)
        self.layout_.addSpacing(10)

        self.scroll_area = ScrollArea(self)
        self.scroll_area.setObjectName("teamSettingTeamScroll")
        self.scroll_area.setSmoothMode(SmoothMode.LINEAR, Qt.Orientation.Vertical)
        self.scroll_area.scrollDelagate.verticalSmoothScroll.duration = 100
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.enableTransparentBackground()

        self.scroll_widget = QWidget(self)
        self.scroll_widget.setObjectName("teamSettingScrollWidget")
        self.scroll_layout = QVBoxLayout(self.scroll_widget)
        self.scroll_layout.setContentsMargins(10, 0, 10, 0)
        self.scroll_layout.setSpacing(10)

        for team_number in range(1, 21):
            team_label = TeamSettingTeamLabel(team_number, self.scroll_widget)
            team_label.clicked.connect(self.team_selected.emit)
            self.team_labels[team_number] = team_label
            self.scroll_layout.addWidget(team_label)

        self.scroll_layout.addStretch()
        self.scroll_area.setWidget(self.scroll_widget)
        self.layout_.addWidget(self.scroll_area, 1)
        self._apply_theme_style()
        qconfig.themeChanged.connect(self._apply_theme_style)

    def set_current_team(self, team_number: int):
        self.current_team_number = team_number
        for number, label in self.team_labels.items():
            label.set_selected(number == team_number)

    def _apply_theme_style(self, *_):
        light_qss, dark_qss = get_team_setting_blank_column_qss()
        self.setStyleSheet(dark_qss if isDarkTheme() else light_qss)
        for number, label in self.team_labels.items():
            label.apply_theme_style(number == self.current_team_number)
