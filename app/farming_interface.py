import sys

from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QApplication
from qfluentwidgets import TextEdit
from qfluentwidgets.window.stacked_widget import StackedWidget

from app.base_combination import *
from app.base_tools import *
from app.gui_action import *
from app.page_card import PageSetWindows, PageDailyTask, PageLunacyToEnkephalin, PageGetPrize, PageMirror


class FarmingInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.parent = parent
        self.hbox_layout = QHBoxLayout(self)
        self.hbox_layout_left = QVBoxLayout(self)
        self.hbox_layout_center = QVBoxLayout(self)
        self.hbox_layout_right = QVBoxLayout(self)
        self.hbox_layout.addLayout(self.hbox_layout_left,stretch=3)
        self.hbox_layout.addLayout(self.hbox_layout_center,stretch=4)
        self.hbox_layout.addLayout(self.hbox_layout_right,stretch=3)

        """
        self.setWidget(self.scroll_widget)
        self.setWidgetResizable(True)
        self.setViewportMargins(0, 0, 0, 5)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)"""

        self.setObjectName('settingInterface')
        self.hbox_layout_left.addWidget(FarmingInterfaceLeft(self))
        self.hbox_layout_center.addWidget(FarmingInterfaceCenter(self))
        self.hbox_layout_right.addWidget(FarmingInterfaceRight(self))

        #self.setStyleSheet("border: 1px solid black;")


        #self.hbox_layout_left.addStretch(1)
        #self.hbox_layout_center.addStretch(1)
        #self.hbox_layout_right.addStretch(1)


class FarmingInterfaceLeft(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.parent = parent
        self.__init_widget()
        self.__init_card()
        self.__init_layout()

    def __init_widget(self):
        self.hbox_layout = QVBoxLayout(self)
        self.setting_layout = QVBoxLayout(self)
        self.setting_options = QVBoxLayout(self)
        self.setting_options.setSpacing(10)

        self.setting_box = BaseSettingLayout()
        #self.setting_box.setFrameShape(QFrame.StyledPanel)  # 带阴影的边框
        #self.setting_box.setLineWidth(1)
        self.setting_box.setLayout(self.setting_layout)

    def __init_card(self):
        self.set_windows = CheckBoxWithButton("set_windows", "窗口设置", None, "set_windows")
        self.daily_task = CheckBoxWithButton("daily_task", "日常任务", None, "daily_task")
        self.get_reward = CheckBoxWithButton("get_reward", "领取奖励", None, "get_reward")
        self.buy_enkephalin = CheckBoxWithButton("buy_enkephalin", "狂气换体", None, "buy_enkephalin")
        self.mirror = CheckBoxWithButton("mirror", "坐牢设置", None, "mirror")
        self.resonate_with_Ahab = CheckBoxWithButton("resonate_with_Ahab", "亚哈共鸣", None, "resonate_with_Ahab")
        self.resonate_with_Ahab.button.setEnabled(False)

        self.select_all = NormalTextButton("全选", lambda: select_all())
        self.clear_all = NormalTextButton("清空", lambda: clear_all())

        self.then = BaseLabel("之后")
        self.then_combobox = BaseComboBox("after_completion")
        self.then_combobox.add_items(set_after_completion_options)
        self.then_combobox.set_options(0)
        self.link_start = NormalTextButton("Link Start!", lambda: link_start(),0)
        self.link_start.button.setMinimumSize(130, 70)
        scale_factor = QtWidgets.QApplication.primaryScreen().logicalDotsPerInch() / 96  # Windows 标准 DPI 是 96
        font_size = min(14, int(14 / scale_factor))
        # 创建字体对象并设置大小
        font = self.link_start.button.font()  # 获取当前字体
        font.setPointSize(font_size)  # 设置字体大小（单位：点）
        self.link_start.button.setFont(font)  # 应用新字体


    def __init_layout(self):
        self.setting_options.addWidget(self.set_windows)
        self.setting_options.addWidget(self.daily_task)
        self.setting_options.addWidget(self.get_reward)
        self.setting_options.addWidget(self.buy_enkephalin)
        self.setting_options.addWidget(self.mirror)
        self.setting_options.addWidget(self.resonate_with_Ahab)
        self.setting_layout.addLayout(self.setting_options)

        self.hbox_button = QHBoxLayout(self)
        self.hbox_button.addWidget(self.select_all)
        self.hbox_button.addWidget(self.clear_all)

        self.setting_layout.addLayout(self.hbox_button)

        self.hbox_layout.addWidget(self.setting_box)
        self.hbox_layout.addWidget(self.then)
        self.hbox_layout.addWidget(self.then_combobox)
        self.hbox_layout.addWidget(self.link_start)


class FarmingInterfaceCenter(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.parent = parent
        self.__init_widget()
        self.__init_card()
        self.__init_layout()
        self.__init_setting()
        # 获取单例
        self.mediator = Mediator()
        self.connect_mediator()

    def __init_widget(self):
        #self.setting_box = CardWidget()
        self.vbox = QVBoxLayout(self)

        self.setting_page = StackedWidget(self)

    def __init_card(self):
        self.set_windows = PageSetWindows(self)
        self.daily_task = PageDailyTask(self)
        self.get_reward = PageGetPrize(self)
        self.buy_enkephalin = PageLunacyToEnkephalin(self)
        self.mirror = PageMirror(self)

    def __init_layout(self):
        self.setting_page.addWidget(self.set_windows)
        self.setting_page.addWidget(self.daily_task)
        self.setting_page.addWidget(self.get_reward)
        self.setting_page.addWidget(self.buy_enkephalin)
        self.setting_page.addWidget(self.mirror)
        self.vbox.addWidget(self.setting_page)
        #self.setting_box.setLayout(self.vbox)

    def __init_setting(self):
        self.setting_page.setCurrentIndex(cfg.get_value("default_page"))
        list(toggle_button_group.items())[cfg.get_value("default_page")][1].setChecked(True)

    def switch_to_page(self, target: str):
        try:
            """切换页面（带越界保护）"""
            page_index = page_name_and_index[target]
            self.setting_page.setCurrentIndex(page_index)
            cfg.set_value("default_page", page_index)
        except Exception as e:
            print(f"【异常】switch_to_page 出错：{e}")

    def connect_mediator(self):
        # 连接所有可能信号
        self.mediator.switch_page.connect(self.switch_to_page)

class FarmingInterfaceRight(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.parent = parent
        self.__init_widget()
        self.__init_card()
        self.__init_layout()

    def __init_widget(self):
        self.main_layout = QVBoxLayout(self)

    def __init_card(self):
        self.scroll_log_edit = TextEdit()
        self.scroll_log_edit.setAutoFormatting(QtWidgets.QTextEdit.AutoAll)

    def __init_layout(self):
        self.main_layout.addWidget(self.scroll_log_edit)


if __name__ == '__main__':
    # enable dpi scale
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)

    app = QApplication(sys.argv)
    w = FarmingInterface()
    w.show()
    app.exec_()