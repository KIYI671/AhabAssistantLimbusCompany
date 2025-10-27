import datetime
import os
import re
import subprocess
from enum import Enum

from PySide6.QtCore import Qt, QLocale, QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QHBoxLayout, QStackedWidget, QVBoxLayout, QLabel, QWidget
from qfluentwidgets import Pivot, setThemeColor, ProgressRing
from qfluentwidgets.components.widgets.frameless_window import FramelessWindow
from qframelesswindow import StandardTitleBar

from app import mediator
from app.card.messagebox_custom import MessageBoxWarning, MessageBoxConfirm
from app.farming_interface import FarmingInterface
from app.language_manager import LanguageManager
from app.page_card import MarkdownViewer
from app.setting_interface import SettingInterface
from app.team_setting_card import TeamSettingCard
from app.tools_interface import ToolsInterface
from module.config import cfg
from module.game_and_screen import screen
from module.logger import log
from module.update.check_update import check_update


class Language(Enum):
    """ Language enumeration """

    CHINESE_SIMPLIFIED = QLocale(QLocale.Language.Chinese, QLocale.Country.China)
    CHINESE_TRADITIONAL = QLocale(QLocale.Language.Chinese, QLocale.Country.HongKong)
    ENGLISH = QLocale(QLocale.Language.English)
    AUTO = QLocale()


# 使用无框窗口
class MainWindow(FramelessWindow):
    def __init__(self):
        super().__init__()
        # 设置标准标题栏，如果不设置则无法展示标题
        self.setTitleBar(StandardTitleBar(self))
        self.setWindowIcon(QIcon('./assets/logo/my_icon_256X256.ico'))
        self.setWindowTitle(f"Ahab Assistant Limbus Company -  {cfg.version}")
        self.setObjectName("MainWindow")
        setThemeColor("#9c080b")
        # self.hBoxLayout =QHBoxLayout(self)
        # self.test_interface = TestInterface(self)
        # self.hBoxLayout.setContentsMargins(0,0,0,0)
        # self.hBoxLayout.addWidget(self.test_interface)
        LanguageManager().register_component(self)

        # 禁用最大化
        self.titleBar.maxBtn.setHidden(True)
        self.titleBar.maxBtn.setDisabled(True)
        self.titleBar.setDoubleClickEnabled(False)
        self.setResizeEnabled(False)
        self.setWindowFlags(Qt.WindowCloseButtonHint)

        self.progress_ring = ProgressRing(self)
        self.progress_ring.hide()

        self.resize(1080, 600)
        screen = QApplication.primaryScreen()
        geometry = screen.availableGeometry() if screen else self.geometry()
        w, h = geometry.width(), geometry.height()
        self.move(w // 2 - self.width() // 2, h // 2 - self.height() // 2)

        self.pivot = Pivot()
        self.stackedWidget = QStackedWidget()
        self.vBoxLayout = QVBoxLayout(self)
        self.HBoxLayout = QHBoxLayout()
        # self.stackedWidget.setStyleSheet("border: 1px solid black;")
        self.setStyleSheet("""
                            MainWindow {    
                                background: #fdfdfd;        /* 背景色（可选） */
                            }
                        """)

        self.farming_interface = FarmingInterface(self)
        if cfg.language_in_program == "zh_cn":
            self.help_interface = MarkdownViewer("./assets/doc/zh/How_to_use.md")
        else:
            self.help_interface = MarkdownViewer("./assets/doc/en/How_to_use_EN.md")
        self.tools_interface = ToolsInterface(self)
        self.setting_interface = SettingInterface(self)
        # self.team_setting = TeamSettingCard(self)

        # add items to pivot
        self.addSubInterface(self.farming_interface, 'farming_interface', '一键长草')
        self.addSubInterface(self.help_interface, 'help_interface', '帮助')
        self.addSubInterface(self.tools_interface, 'tools_interface', '小工具')
        self.addSubInterface(self.setting_interface, 'setting_interface', '设置')
        # self.addSubInterface(self.team_setting, 'team_setting', '队伍设置')

        self.HBoxLayout.addWidget(self.pivot)
        self.vBoxLayout.addSpacing(10)
        self.vBoxLayout.addLayout(self.HBoxLayout, 0)
        self.vBoxLayout.addWidget(self.stackedWidget)
        self.vBoxLayout.setContentsMargins(30, 20, 30, 0)
        self.pivot.setMaximumHeight(50)

        self.stackedWidget.setCurrentWidget(self.farming_interface)
        self.pivot.setCurrentItem(self.farming_interface.objectName())
        self.pivot.currentItemChanged.connect(
            lambda k: self.stackedWidget.setCurrentWidget(self.findChild(QWidget, k)))

        # self.stackedWidget.setStyleSheet("background-color: white;")

        # 将标题栏置顶
        self.titleBar.raise_()

        self.connect_mediator()

        self.show()

        self.check_mirror_setting()

        check_update(self, flag=True)

        self.set_ring()

    def addSubInterface(self, widget: QWidget, objectName, text):
        widget.setObjectName(objectName)
        # widget.setAlignment(Qt.AlignCenter)
        self.stackedWidget.addWidget(widget)
        self.pivot.addItem(routeKey=objectName, text=text)

    def add_and_switch_to_page(self, target: str):
        try:
            num = int(re.search(r'team(\d+)_setting', target).group(1))
            if "team_setting" in list(self.pivot.items.keys()):
                list(self.pivot.items.values())[-1].click()
                message = self.tr("存在未保存的队伍设置")
                mediator.warning.emit(message)
                self.pivot.setCurrentItem("team_setting")
            else:
                """切换页面（带越界保护）"""
                self.addSubInterface(TeamSettingCard(num), 'team_setting', self.tr("队伍设置"))
                QTimer.singleShot(0, lambda: self.pivot.setCurrentItem("team_setting"))
        except Exception as e:
            log.error(f"【异常】switch_to_page 出错：{type(e).__name__}:{e}")

    def close_setting_page(self):
        try:
            list(self.pivot.items.values())[0].click()
            page = self.findChild(TeamSettingCard, "team_setting")

            LanguageManager().unregister_component(page)
            LanguageManager().unregister_component(page.customize_settings_module)

            self.stackedWidget.removeWidget(page)
            page.setParent(None)
            page.deleteLater()
            page = None
            self.pivot.removeWidget("team_setting")
        except Exception as e:
            log.error(f"delete_team 出错：{e}")

    def show_save_warning(self):
        MessageBoxWarning(
            self.tr('设置未保存'),
            self.tr('存在未保存的设置，请执行保存或取消操作'),
            self
        ).exec()

    def show_warning(self, warning: str):
        MessageBoxWarning(
            self.tr('警告！'),
            warning,
            self
        ).exec()

    def show_tasks_warning(self):
        MessageBoxWarning(
            self.tr('任务设置出错'),
            self.tr('未设置任何任务，请勾选主页面左边的选项框需要执行的任务'),
            self
        ).exec()

    def connect_mediator(self):
        # 连接所有可能信号
        mediator.switch_team_setting.connect(self.add_and_switch_to_page)
        mediator.close_setting.connect(self.close_setting_page)
        mediator.save_warning.connect(self.show_save_warning)
        mediator.tasks_warning.connect(self.show_tasks_warning)
        mediator.update_progress.connect(self.set_progress_ring)
        mediator.download_complete.connect(self.download_and_install)
        mediator.warning.connect(self.show_warning)

    def set_ring(self):
        self.progress_ring.raise_() # 保持最上层显示
        self.progress_ring.setValue(0)
        self.progress_ring.setTextVisible(True)
        self.progress_ring.setFixedSize(80, 80)
        x = self.width() - 100
        y = self.height() - 100
        self.progress_ring.move(x, y)

    def check_mirror_setting(self):
        for team_num in range(1, 21):
            if not cfg.get_value(f"team{team_num}_setting"):
                return
            config_team_setting = cfg.get_value(f"team{team_num}_setting")
            import copy
            from app import team_setting_template
            team_setting = copy.deepcopy(team_setting_template)
            # 用配置中的值覆盖模板的同名key（仅处理模板中存在的key）
            for key, value in config_team_setting.items():
                if key in team_setting:  # 忽略模板中已删除的key
                    team_setting[key] = value
            cfg.set_value(f"team{team_num}_setting", team_setting)

    def set_progress_ring(self, value: int):
        self.progress_ring.show()
        self.progress_ring.raise_()  # 保持最上层显示
        self.progress_ring.setValue(value)

    def handle_link_click(self, url: str):
        """处理帮助文档中的链接点击"""
        if url.endswith(".md"):
            self.help_interface.load_markdown(url)

    def download_and_install(self, file_name):
        messages_box = MessageBoxConfirm(
            self.tr("更新提醒"),
            self.tr("下载已经完成，是否开始更新"),
            self.window()
        )
        if messages_box.exec():
            source_file = os.path.abspath("./AALC Updater.exe")
            assert_name = file_name
            subprocess.Popen([source_file, assert_name], creationflags=subprocess.DETACHED_PROCESS)

    def retranslateUi(self):
        self.pivot.setItemText("farming_interface", self.tr("一键长草"))
        self.pivot.setItemText("help_interface", self.tr("帮助"))
        self.pivot.setItemText("tools_interface", self.tr("小工具"))
        self.pivot.setItemText("setting_interface", self.tr("设置"))

        if "team_setting" in list(self.pivot.items.keys()):
            self.pivot.setItemText("team_setting", self.tr("队伍设置"))
