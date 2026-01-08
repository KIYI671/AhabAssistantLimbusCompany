import datetime
import os
import sys
import re
import subprocess
from enum import Enum

from PySide6.QtCore import Qt, QLocale, QTimer, QRect, QPropertyAnimation, QEasingCurve, QPoint
from PySide6.QtGui import QIcon, QPainter, QColor, QFont, QRegion, QPolygon, QTransform
from PySide6.QtWidgets import QApplication, QHBoxLayout, QStackedWidget, QVBoxLayout, QLabel, QWidget, QGraphicsOpacityEffect
from qfluentwidgets import Pivot, setThemeColor, ProgressRing, qconfig, setTheme, Theme, isDarkTheme
from qfluentwidgets.components.widgets.frameless_window import FramelessWindow
from qframelesswindow import StandardTitleBar

from app import mediator, AnnouncementStatus
from app.announcement_board import AnnouncementBoard, Announcement, AnnouncementThread
from app.card.messagebox_custom import MessageBoxWarning, MessageBoxConfirm
from app.farming_interface import FarmingInterface
from app.language_manager import LanguageManager
from app.page_card import MarkdownViewer
from app.setting_interface import SettingInterface
from app.team_setting_card import TeamSettingCard
from app.tools_interface import ToolsInterface
from module.game_and_screen import screen
from module.logger import log
from module.update.check_update import check_update
from module.config import cfg


class Language(Enum):
    """ Language enumeration """

    CHINESE_SIMPLIFIED = QLocale(QLocale.Language.Chinese, QLocale.Country.China)
    CHINESE_TRADITIONAL = QLocale(QLocale.Language.Chinese, QLocale.Country.HongKong)
    ENGLISH = QLocale(QLocale.Language.English)
    AUTO = QLocale()

#  DEV 标识
class DevWatermark(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(200, 200)
        
        # Enable mouse events for hover detection
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Opacity effect
        self._op = QGraphicsOpacityEffect(self)
        self._op.setOpacity(1.0)
        self.setGraphicsEffect(self._op)
        
        # Opacity animation
        self.anim_opacity = QPropertyAnimation(self._op, b"opacity")
        self.anim_opacity.setDuration(300)
        self.anim_opacity.setEasingCurve(QEasingCurve.OutCubic)

        # Set mask to limit hover area to the ribbon only
        self.updateMask()

    def updateMask(self):
        # Replicate the logic from paintEvent to get the ribbon shape
        ribbon_center_dist = 40
        ribbon_width = 24
        rect = QRect(-100, ribbon_center_dist - ribbon_width // 2, 200, ribbon_width)
        
        transform = QTransform()
        transform.rotate(-45)
        
        # Map the rect to a polygon using the transform
        region_poly = transform.mapToPolygon(rect)
        
        # Set the mask
        self.setMask(QRegion(region_poly))

    def enterEvent(self, event):
        self.anim_opacity.stop()
        self.anim_opacity.setStartValue(self._op.opacity())
        self.anim_opacity.setEndValue(0.05) # Fade to nearly transparent
        self.anim_opacity.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.anim_opacity.stop()
        self.anim_opacity.setStartValue(self._op.opacity())
        self.anim_opacity.setEndValue(1.0) # Fade back to full
        self.anim_opacity.start()
        super().leaveEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Calculate ribbon path
        # We want a ribbon in the top-left corner
        # Let's rotate -45 degrees around (0,0)
        painter.rotate(-45)
        
        # Position the ribbon
        # Since we rotated -45 deg, the X-axis points diagonally up-right
        # The Y-axis points diagonally down-right.
        # We want the ribbon to cross the corner.
        # Distance from origin to ribbon center: let's say 40px
        
        ribbon_center_dist = 40
        ribbon_width = 24
        
        # Draw ribbon background
        rect = QRect(-100, ribbon_center_dist - ribbon_width // 2, 200, ribbon_width)
        
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#d32f2f"))  # Red
        painter.drawRect(rect)
        
        # Draw text
        painter.setFont(QFont("Microsoft YaHei", 9, QFont.Bold))
        painter.setPen(QColor("white"))
        painter.drawText(rect, Qt.AlignCenter, "DEV")



# 使用无框窗口
class MainWindow(FramelessWindow):
    def __init__(self, argv: list[str]):
        super().__init__()

        font_families = [
            "Segoe UI",  # Windows 现代UI字体
            "Microsoft YaHei",  # 微软雅黑
            "微软雅黑",  # 微软雅黑中文名
            "Noto Sans CJK SC",  # 跨平台中文字体
            "sans-serif",  # 最后回退到无衬线字体
            "SansSerif",  # 无衬线字体另一个名称
            "SimSun",  # 宋体
        ]
        qconfig.fontFamilies.value = font_families

        title_bar = StandardTitleBar(self)
        title_bar.titleLabel.setStyleSheet("""
            QLabel{
                background: transparent;
                font-family: "Segoe UI", "Microsoft YaHei", "微软雅黑", "PingFang SC", "Hiragino Sans GB", sans-serif, "SimSun";
                font-size: 13px;
                padding: 0 4px
            }
        """)

        # 设置标准标题栏，如果不设置则无法展示标题
        self.setTitleBar(title_bar)
        self.setWindowIcon(QIcon('./assets/logo/my_icon_256X256.ico'))
        self.setWindowTitle(f"Ahab Assistant Limbus Company -  {cfg.version}")
        self.setObjectName("MainWindow")
        setThemeColor("#0078D4")
        # self.hBoxLayout =QHBoxLayout(self)
        # self.test_interface = TestInterface(self)
        # self.hBoxLayout.setContentsMargins(0,0,0,0)
        # self.hBoxLayout.addWidget(self.test_interface)
        LanguageManager().register_component(self)
        
        # Apply theme
        theme_mode = cfg.get_value("theme_mode", "Auto")
        if theme_mode == "Auto":
            setTheme(Theme.AUTO)
        elif theme_mode == "Light":
            setTheme(Theme.LIGHT)
        elif theme_mode == "Dark":
            setTheme(Theme.DARK)
        
        # Connect theme change signal
        qconfig.themeChanged.connect(self.updateBackground)
        self.updateBackground()

        # 禁用最大化
        self.titleBar.maxBtn.setHidden(True)
        self.titleBar.maxBtn.setDisabled(True)
        self.titleBar.setDoubleClickEnabled(False)
        self.setResizeEnabled(False)

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

        # Dev Watermark
        if os.environ.get('AALC_DEV_MODE') == '1' or not getattr(sys, 'frozen', False):
            self.dev_watermark = DevWatermark(self)
            self.dev_watermark.move(0, 0)
            self.dev_watermark.raise_()

        self.connect_mediator()

        self.show()

        self.check_mirror_setting()

        # 开发模式下不检查更新
        if os.environ.get('AALC_DEV_MODE') != '1':
            check_update(self, flag=True)

        self.set_ring()

        self.show_announcement_board()

        self.command_start(argv)

    def command_start(self, argv: list[str]):
        """通过命令行参数控制程序启动行为"""
        # 初始化控制符
        skip_arg_times = 0
        start_flag = False
        exit_flag = False
        exit_type = 0
        last_cmd = ""
        # 读取输入参数
        for index, arg in enumerate(argv):
            if index == 0:
                # 跳过第一个参数（程序路径）
                continue
            if skip_arg_times > 0:
                # 读取参数后可以跳过的次数
                # 运行一个控制语句读取多个参数
                skip_arg_times -= 1
                continue
            if arg == "start":
                start_flag = True
                last_cmd = "start"
                continue
            if arg == "--exit" and last_cmd == "start":
                exit_flag = True
                skip_arg_times = 1
                exit_type = 5
                try:
                    exit_type = int(argv[index + 1])
                    if exit_type < 0 or exit_type > 6:
                        exit_type = 0
                        log.error(f'命令行参数 --exit 后输入值"{argv[index + 1]}"越界')
                except (IndexError, ValueError):
                    # 由于输入值为可选, 所以在强制int失败或缺少时将跳过参数数值重置为0
                    skip_arg_times = 0
                    log.info('命令行参数 --exit 后缺少退出类型，默认为5, 即退出AALC')
                except Exception as e:
                    exit_type = 0
                    skip_arg_times = 0
                    log.error(f'命令行参数 --exit 未知错误: {e}')
                continue

        # 最终执行操作
        if exit_flag:
            self.farming_interface.interface_left.then_combobox.combo_box.setCurrentIndex(exit_type)

        if start_flag:
            QTimer.singleShot(3000, mediator.finished_signal.emit)
            
    def updateBackground(self):
        if isDarkTheme():
            self.setStyleSheet("MainWindow { background-color: #272727; }")
            self.titleBar.titleLabel.setStyleSheet("""
                QLabel{
                    background: transparent;
                    font-family: "Segoe UI", "Microsoft YaHei", "微软雅黑", "PingFang SC", "Hiragino Sans GB", sans-serif, "SimSun";
                    font-size: 13px;
                    padding: 0 4px;
                    color: white;
                }
            """)
            self.titleBar.minBtn.setNormalColor(Qt.white)
            self.titleBar.minBtn.setHoverColor(Qt.white)
            self.titleBar.minBtn.setPressedColor(Qt.white)
            self.titleBar.maxBtn.setNormalColor(Qt.white)
            self.titleBar.maxBtn.setHoverColor(Qt.white)
            self.titleBar.maxBtn.setPressedColor(Qt.white)
            self.titleBar.closeBtn.setNormalColor(Qt.white)
            self.titleBar.closeBtn.setHoverColor(Qt.white)
            self.titleBar.closeBtn.setPressedColor(Qt.white)
        else:
            self.setStyleSheet("MainWindow { background-color: #fdfdfd; }")
            self.titleBar.titleLabel.setStyleSheet("""
                QLabel{
                    background: transparent;
                    font-family: "Segoe UI", "Microsoft YaHei", "微软雅黑", "PingFang SC", "Hiragino Sans GB", sans-serif, "SimSun";
                    font-size: 13px;
                    padding: 0 4px;
                    color: black;
                }
            """)
            self.titleBar.minBtn.setNormalColor(Qt.black)
            self.titleBar.minBtn.setHoverColor(Qt.black)
            self.titleBar.minBtn.setPressedColor(Qt.black)
            self.titleBar.maxBtn.setNormalColor(Qt.black)
            self.titleBar.maxBtn.setHoverColor(Qt.black)
            self.titleBar.maxBtn.setPressedColor(Qt.black)
            self.titleBar.closeBtn.setNormalColor(Qt.black)
            self.titleBar.closeBtn.setHoverColor(Qt.white)
            self.titleBar.closeBtn.setPressedColor(Qt.black)

    def closeEvent(self, e):
        if (
                self.farming_interface.interface_left.my_script is not None
                and self.farming_interface.interface_left.my_script.isRunning()
        ):
            message_box = MessageBoxConfirm(
                self.tr("有正在进行的任务"),
                self.tr("脚本正在运行中，确定要退出程序吗？"),
                self.window()
            )
            if message_box.exec():
                self.farming_interface.interface_left.my_script.terminate()
            else:
                e.ignore()
                return
        return super().closeEvent(e)

    def addSubInterface(self, widget: QLabel, objectName, text):
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
        self.progress_ring.raise_()  # 保持最上层显示
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

    def show_announcement_board(self):

        def handler_update(status):
            """
            公告处理函数，根据不同的公告状态执行不同的操作。
            :param status: 公告状态。
            """
            if status == AnnouncementStatus.ANNO_AVAILABLE:
                # 当有新公告时，弹出公告栏
                messages_box = AnnouncementBoard(
                    self.announcement_thread.announcement,
                    self.announcement_thread.announcement_time,
                    self.window()
                )
                messages_box.show()
                messages_box.setDefault(0)

        try:
            # 创建一个公告线程实例
            self.announcement_thread = AnnouncementThread()
            # 将公告处理函数连接到更新线程的信号
            self.announcement_thread.AnnouncementSignal.connect(handler_update)
            # 启动公告线程
            self.announcement_thread.start()
        except Exception as e:
            log.error(f"show_announcement_board 出错：{e}")
