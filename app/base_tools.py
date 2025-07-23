from typing import Union

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QIcon, QFont
from PyQt5.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QSizePolicy, QWidget, QGridLayout, QAction
from qfluentwidgets import FluentIcon as FIF
from qfluentwidgets import FluentIconBase, CheckBox, ToggleToolButton, ToolButton, PushButton, \
    BodyLabel, ComboBox, DoubleSpinBox, SpinBox, RoundMenu, SplitToolButton
from qfluentwidgets.components.settings.setting_card import SettingIconWidget

from app import *
from module.config import cfg


class BaseLayout(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.hBoxLayout = QHBoxLayout(self)

        # 初始化布局
        self.hBoxLayout.setSpacing(0)
        self.hBoxLayout.setContentsMargins(0, 0, 0, 0)
        self.hBoxLayout.setAlignment(Qt.AlignCenter)


class BaseSettingLayout(QFrame):
    def __init__(self, box_type=0, parent=None):
        super().__init__(parent=parent)
        if box_type == 0:
            pass
        elif box_type == 1:
            self.BoxLayout = QHBoxLayout(self)
            self.BoxLayout.setContentsMargins(0, 0, 0, 0)
        else:
            self.BoxLayout = QVBoxLayout(self)
            self.BoxLayout.setContentsMargins(0, 0, 0, 0)

        self.setStyleSheet("""
                    BaseSettingLayout {
                        border: 2px solid #E0E0E0;  /* 边框颜色 */
                        border-radius: 5px;         /* 圆角 */
                        padding: 10px;              /* 内边距 */
                    }
                    BaseSettingLayout:hover {
                        border-color: #D2D2D2;  /* 悬停时边框突出显示 */
                    }
                """)

    def add(self, tool):
        if isinstance(tool, QWidget):
            self.BoxLayout.addWidget(tool)
        elif isinstance(tool, QVBoxLayout):
            self.BoxLayout.addLayout(tool)
        elif isinstance(tool, QHBoxLayout):
            self.BoxLayout.addLayout(tool)
        elif isinstance(tool, QGridLayout):
            self.BoxLayout.addLayout(tool)


class BaseCheckBox(BaseLayout):
    def __init__(self, config_name, icon: Union[str, QIcon, FluentIconBase, None], title, parent=None, center=True,
                 icon_size=16):
        super().__init__(parent=parent)
        self.config_name = config_name
        self.setObjectName(config_name)

        if icon:
            self.iconLabel = SettingIconWidget(icon, self)
            self.iconLabel.setFixedSize(icon_size, icon_size)
            self.hBoxLayout.addWidget(self.iconLabel, 0, Qt.AlignLeft)
            self.hBoxLayout.addSpacing(5)

        self.check_box = CheckBox(title, self)
        self.hBoxLayout.addWidget(self.check_box, 0, Qt.AlignLeft)
        self.hBoxLayout.addSpacing(16)
        if not center:
            self.hBoxLayout.setAlignment(Qt.AlignLeft)

        if cfg.get_value(self.config_name) is not None:
            self.check_box.setChecked(cfg.get_value(self.config_name))
        elif "the_team_" in self.config_name:
            number = int(self.config_name.split("_")[-1])
            teams_be_select = cfg.get_value("teams_be_select")
            if number <= len(teams_be_select) and teams_be_select[number - 1] is True:
                self.check_box.setChecked(True)
        elif self.config_name in all_sinners_name:
            mediator.sinner_be_selected.emit()

        self.check_box.toggled.connect(self.on_toggle)

    def set_checked(self, checked):
        self.check_box.toggled.disconnect(self.on_toggle)
        self.check_box.setChecked(checked)
        self.check_box.toggled.connect(self.on_toggle)

    def set_box_enabled(self, b: bool):
        self.check_box.setEnabled(b)

    def set_check_false(self):
        self.check_box.setChecked(False)

    def on_toggle(self, checked):
        if cfg.get_value(self.config_name) is not None:
            cfg.set_value(self.config_name, checked)
        elif self.config_name.startswith('the_team_'):
            index = int(self.config_name.split("_")[-1]) - 1
            if checked:
                cfg.set_value("teams_be_select_num", cfg.get_value("teams_be_select_num") + 1)
                teams_be_select = cfg.get_value("teams_be_select")
                teams_be_select[index] = True
                teams_order = cfg.get_value("teams_order")
                teams_order[index] = cfg.get_value("teams_be_select_num")
                cfg.set_value("teams_be_select", teams_be_select)
                cfg.set_value("teams_order", teams_order)
            else:
                cfg.set_value("teams_be_select_num", cfg.get_value("teams_be_select_num") - 1)
                teams_be_select = cfg.get_value("teams_be_select")
                teams_be_select[index] = False
                teams_order = cfg.get_value("teams_order")
                for i in range(len(teams_order)):
                    if teams_order[i] > teams_order[index]:
                        teams_order[i] -= 1
                teams_order[index] = 0
                cfg.set_value("teams_be_select", teams_be_select)
                cfg.set_value("teams_order", teams_order)
            mediator.refresh_teams_order.emit()
        else:
            data_dict = {self.config_name: checked}
            self.send_switch_signal(data_dict)

    def send_switch_signal(self, target: dict):
        mediator.team_setting.emit(target)


class BaseButton(BaseLayout):
    def __init__(self, config_name, parent=None):
        super().__init__(parent=parent)
        self.config_name = config_name
        self.setObjectName(config_name)


class NormalTextButton(BaseButton):
    clicked = pyqtSignal()

    def __init__(self, button_text, config_name, tactics=1, parent=None):
        super().__init__(config_name, parent=parent)
        self.setFixedHeight(100)

        self.button = PushButton(button_text, self)
        if tactics == 1:
            self.button.setSizePolicy(
                QSizePolicy.Expanding,  # 水平方向自动扩展
                QSizePolicy.Fixed  # 垂直方向固定
            )

        self.hBoxLayout.addWidget(self.button)
        self.button.clicked.connect(self.clicked)

    def get_text(self):
        return self.button.text()

    def set_text(self, text):
        self.button.setText(text)

    def be_click(self):
        self.button.click()


class ToSettingButton(BaseButton):
    def __init__(self, config_name, icon: Union[str, QIcon, FluentIconBase, None] = FIF.SETTING, parent=None):
        super().__init__(config_name, parent=parent)

        self.setFixedHeight(30)
        self.setFixedWidth(50)

        self.button = SplitToolButton(icon, self)

        self.menu = RoundMenu(parent=self)
        self.edit_name = QAction(FIF.EDIT.icon(), '命名')
        self.del_action = QAction(FIF.DELETE.icon(), '删除')
        self.menu.addAction(self.edit_name)
        self.menu.addAction(self.del_action)
        self.button.setFlyout(self.menu)

        team_toggle_button_group.append(self.button)

        self.button.clicked.connect(self.on_click)

        self.hBoxLayout.addWidget(self.button)

    def on_click(self):
        for button in team_toggle_button_group:
            if button == self.button:
                self.send_switch_signal(self.config_name)

    def send_switch_signal(self, target: str):
        mediator.switch_team_setting.emit(target)


class ChangePageButton(BaseButton):
    def __init__(self, config_name, icon: Union[str, QIcon, FluentIconBase, None] = FIF.SETTING, parent=None):
        super().__init__(config_name, parent=parent)

        self.setFixedHeight(30)
        self.setFixedWidth(50)

        self.button = ToggleToolButton(icon, self)
        toggle_button_group[config_name] = self.button
        self.button.clicked.connect(self.on_click)

        self.hBoxLayout.addWidget(self.button)

    def on_click(self):
        for d, button in toggle_button_group.items():
            if button == self.button:
                button.setChecked(True)
                self.send_switch_signal(self.config_name)
            else:
                button.setChecked(False)

    def send_switch_signal(self, target: str):
        mediator.switch_page.emit(target)


class SettingTeamsButton(BaseButton):
    def __init__(self, config_name, icon: Union[str, QIcon, FluentIconBase, None] = FIF.SETTING, parent=None):
        super().__init__(config_name, parent=parent)

        self.setFixedHeight(30)
        self.setFixedWidth(50)

        self.button = ToolButton(icon, self)
        self.button.clicked.connect(self.on_click)

        self.hBoxLayout.addWidget(self.button)

    def on_click(self):
        pass


class BaseLabel(BaseLayout):
    def __init__(self, config_name, parent=None):
        super().__init__(parent=parent)
        self.config_name = config_name
        self.label = BodyLabel(config_name)
        self.label.setFont(QFont('Microsoft YaHei UI', 12))
        self.hBoxLayout.addWidget(self.label, Qt.AlignLeft)
        self.hBoxLayout.setContentsMargins(5, 0, 0, 0)
        self.setFixedHeight(25)

    def add_icon(self, icon):
        self.iconLabel = SettingIconWidget(icon, self)
        self.iconLabel.setFixedSize(20, 20)
        self.hBoxLayout.insertWidget(0, self.iconLabel)
        self.hBoxLayout.insertSpacing(1, 16)


class BaseComboBox(BaseLayout):
    def __init__(self, config_name, combo_box_width=None, parent=None):
        super().__init__(parent=parent)
        self.setObjectName(config_name)
        self.config_name = config_name
        self.items = None
        self.combo_box = ComboBox(self)
        self.hBoxLayout.addWidget(self.combo_box, stretch=1)
        self.setFixedHeight(30)
        if combo_box_width and isinstance(combo_box_width, int):
            self.combo_box.setFixedWidth(combo_box_width)

        self.combo_box.currentIndexChanged.connect(self.on_change)

    def add_items(self, items):
        self.combo_box.currentIndexChanged.disconnect(self.on_change)
        self.combo_box.addItems(items)
        self.items = items
        if cfg.get_value(self.config_name):
            for i in range(self.combo_box.count()):
                if list(items.items())[i][1] == cfg.get_value(self.config_name):
                    self.combo_box.setCurrentIndex(i)
        self.combo_box.currentIndexChanged.connect(self.on_change)

    def on_change(self, index):
        if cfg.get_value(self.config_name) is not None:
            cfg.set_value(self.config_name, list(self.items.items())[index][1])
        else:
            data_dict = {self.config_name: list(self.items.items())[index][1]}
            self.send_switch_signal(data_dict)

    def set_options(self, index):
        self.combo_box.setCurrentIndex(index)

    def send_switch_signal(self, target: dict):
        mediator.team_setting.emit(target)


class BaseSpinBox(BaseLayout):
    def __init__(self, config_name, parent=None, double=False, min_value=0, min_step=1):
        super().__init__(parent=parent)
        self.config_name = config_name
        if double:
            self.spin_box = DoubleSpinBox(self)
            min_value = 0.01
            min_step = 0.01
        else:
            self.spin_box = SpinBox(self)
        self.hBoxLayout.addWidget(self.spin_box, stretch=1)
        self.setFixedHeight(50)
        self.spin_box.setMinimum(min_value)
        self.spin_box.setSingleStep(min_step)
        self.spin_box.setAlignment(Qt.AlignCenter)

        if cfg.get_value(self.config_name) is not None:
            self.spin_box.setValue(cfg.get_value(self.config_name))

        self.spin_box.valueChanged.connect(self.value_changed)

    def value_changed(self):
        if cfg.get_value(self.config_name) is not None:
            cfg.set_value(self.config_name, self.spin_box.value())
