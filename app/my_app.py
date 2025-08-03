import datetime
import os
import re
from enum import Enum

from PyQt5.QtCore import Qt, QLocale
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, QHBoxLayout, QStackedWidget, QVBoxLayout, QLabel, QWidget
from qfluentwidgets import Pivot, setThemeColor, ProgressRing
from qfluentwidgets.components.widgets.frameless_window import FramelessWindow
from qframelesswindow import StandardTitleBar

from app import mediator
from app.card.messagebox_custom import MessageBoxWarning
from app.farming_interface import FarmingInterface
from app.page_card import MarkdownViewer
from app.setting_interface import SettingInterface
from app.team_setting_card import TeamSettingCard
from module.config import cfg
from module.logger import log
from module.update.check_update import check_update


class Language(Enum):
    """ Language enumeration """

    CHINESE_SIMPLIFIED = QLocale(QLocale.Chinese, QLocale.China)
    CHINESE_TRADITIONAL = QLocale(QLocale.Chinese, QLocale.HongKong)
    ENGLISH = QLocale(QLocale.English)
    AUTO = QLocale()

# 使用无框窗口
class MainWindow(FramelessWindow):
    def __init__(self):
        super().__init__()
        # 设置标准标题栏，如果不设置则无法展示标题
        self.setTitleBar(StandardTitleBar(self))
        self.setWindowIcon(QIcon('./assets/logo/my_icon_256X256.ico'))
        self.setWindowTitle(f"Ahab Assistant Limbus Company -  {cfg.version}")
        setThemeColor("#9c080b")
        #self.hBoxLayout =QHBoxLayout(self)
        #self.test_interface = TestInterface(self)
        #self.hBoxLayout.setContentsMargins(0,0,0,0)
        #self.hBoxLayout.addWidget(self.test_interface)

        # 禁用最大化
        self.titleBar.maxBtn.setHidden(True)
        self.titleBar.maxBtn.setDisabled(True)
        self.titleBar.setDoubleClickEnabled(False)
        self.setResizeEnabled(False)
        self.setWindowFlags(Qt.WindowCloseButtonHint)

        self.progress_ring = ProgressRing(self)
        self.progress_ring.hide()

        self.resize(1080,800)
        desktop = QApplication.desktop().availableGeometry()
        w, h = desktop.width(), desktop.height()
        self.move(w // 2 - self.width() // 2, h // 2 - self.height() // 2)

        self.pivot = Pivot(self)
        self.stackedWidget = QStackedWidget(self)
        self.vBoxLayout = QVBoxLayout(self)
        self.HBoxLayout = QHBoxLayout(self)
        #self.stackedWidget.setStyleSheet("border: 1px solid black;")
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
        # 手动处理链接点击以处理md文件
        self.help_interface.linkClicked.connect(self.handle_link_click)

        self.setting_interface = SettingInterface(self)
        #self.team_setting = TeamSettingCard(self)

        # add items to pivot
        self.addSubInterface(self.farming_interface, 'farming_interface', '一键长草')
        self.addSubInterface(self.help_interface, 'help_interface', '帮助')
        self.addSubInterface(self.setting_interface, 'setting_interface', '设置')
        #self.addSubInterface(self.team_setting, 'team_setting', '队伍设置')


        

        self.HBoxLayout.addWidget(self.pivot)
        self.vBoxLayout.addSpacing(10)
        self.vBoxLayout.addLayout(self.HBoxLayout,0)
        self.vBoxLayout.addWidget(self.stackedWidget)
        self.vBoxLayout.setContentsMargins(30, 20, 30, 30)
        self.pivot.setMaximumHeight(50)

        self.stackedWidget.setCurrentWidget(self.farming_interface)
        self.pivot.setCurrentItem(self.farming_interface.objectName())
        self.pivot.currentItemChanged.connect(
            lambda k: self.stackedWidget.setCurrentWidget(self.findChild(QWidget, k)))

        #self.stackedWidget.setStyleSheet("background-color: white;")

        # 将标题栏置顶
        self.titleBar.raise_()

        self.connect_mediator()

        self.show()

        self.clean_old_logs()

        check_update(self, flag=True)

        self.set_ring()

    def addSubInterface(self, widget: QLabel, objectName, text):
        widget.setObjectName(objectName)
        #widget.setAlignment(Qt.AlignCenter)
        self.stackedWidget.addWidget(widget)
        self.pivot.addItem(routeKey=objectName, text=text)

    def add_and_switch_to_page(self, target: str):
        try:
            num = int(re.search(r'team(\d+)_setting', target).group(1))
            if "team_setting" in list(self.pivot.items.keys()):
                list(self.pivot.items.values())[-1].click()
                self.pivot.setCurrentItem("team_setting")
            else:
                """切换页面（带越界保护）"""
                self.addSubInterface(TeamSettingCard(num,self), 'team_setting', '队伍设置')
                list(self.pivot.items.values())[-1].click()
                self.pivot.setCurrentItem("team_setting")
        except Exception as e:
            print(f"【异常】switch_to_page 出错：{e}")

    def close_setting_page(self):
        try:
            list(self.pivot.items.values())[0].click()
            page = self.findChild(TeamSettingCard, "team_setting")
            self.stackedWidget.removeWidget(page)
            page.setParent(None)
            page.deleteLater()
            page = None
            self.pivot.removeWidget("team_setting")
        except Exception as e:
            print(f"【异常】delete_team 出错：{e}")

    def show_save_warning(self):
        MessageBoxWarning(
            '设置未保存',
            '存在未保存的设置，请执行保存或取消操作',
            self
        ).exec()

    def connect_mediator(self):
        # 连接所有可能信号
        mediator.switch_team_setting.connect(self.add_and_switch_to_page)
        mediator.close_setting.connect(self.close_setting_page)
        mediator.save_warning.connect(self.show_save_warning)
        mediator.update_progress.connect(self.set_progress_ring)

    @staticmethod
    def clean_old_logs():
        if not cfg.clean_logs:
            return
        # 获取今日日期（date对象）
        today = datetime.date.today()
        # 计算阈值日期（七天前的日期）
        threshold_date = today - datetime.timedelta(days=7)

        # 遍历日志文件夹中的所有文件/目录
        for filename in os.listdir("./logs"):
            # 拼接完整文件路径
            file_path = os.path.join("./logs", filename)

            try:
                file_date = datetime.datetime.strptime(filename[:10], "%Y-%m-%d").date()
            except:
                continue

            # 判断是否早于阈值日期（需要删除）
            if file_date < threshold_date:
                try:
                    os.remove(file_path)
                    print(f"已删除过期日志文件: {file_path}")
                except Exception as e:
                    log.DEBUG(f"删除文件失败 {file_path}，错误原因: {str(e)}")

    def set_ring(self):
        self.progress_ring.setWindowFlag(Qt.WindowStaysOnTopHint)  # 保持最上层显示
        self.progress_ring.setValue(0)
        self.progress_ring.setTextVisible(True)
        self.progress_ring.setFixedSize(80, 80)
        x = self.width()-100
        y = self.height()-100
        self.progress_ring.move(x, y)

    def set_progress_ring(self,value:int):
        self.progress_ring.setWindowFlag(Qt.WindowStaysOnTopHint)  # 保持最上层显示
        self.progress_ring.show()
        self.progress_ring.setValue(value)

    def handle_link_click(self, url:str):
        """处理帮助文档中的链接点击"""
        
        
        if url.endswith(".md"):
            self.help_interface.load_markdown(url)
        