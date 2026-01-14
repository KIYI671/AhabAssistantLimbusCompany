import os
import sys
from PySide6.QtCore import Qt, QFile, QTimer
from PySide6.QtWidgets import QApplication, QTextEdit
from pynput import keyboard
from qfluentwidgets import TextEdit, TransparentToolButton, setCustomStyleSheet
from qfluentwidgets.window.stacked_widget import StackedWidget

from app.base_combination import *
from app.base_tools import *
from app.language_manager import LanguageManager
from app.common.ui_config import get_log_text_edit_qss
from app.page_card import (
    PageSetWindows,
    PageDailyTask,
    PageLunacyToEnkephalin,
    PageGetPrize,
    PageMirror,
)
from app.team_setting_card import TeamSettingCard
from module.automation import auto
from module.game_and_screen import screen
from module.logger import log
from module.ocr import ocr
from tasks.base.script_task_scheme import my_script_task
from utils.utils import check_hard_mirror_time


class FarmingInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        # objectName 由 addSubInterface 设置，这里不需要设置
        self.hbox_layout = QHBoxLayout(self)
        self.hbox_layout_left = QVBoxLayout()
        self.hbox_layout_center = QVBoxLayout()
        self.hbox_layout_right = QVBoxLayout()
        self.hbox_layout.addLayout(self.hbox_layout_left, stretch=3)
        self.hbox_layout.addLayout(self.hbox_layout_center, stretch=4)
        self.hbox_layout.addLayout(self.hbox_layout_right, stretch=3)

        """
        self.setWidget(self.scroll_widget)
        self.setWidgetResizable(True)
        self.setViewportMargins(0, 0, 0, 5)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)"""

        self.interface_left = FarmingInterfaceLeft()
        self.interface_center = FarmingInterfaceCenter()
        self.interface_right = FarmingInterfaceRight()
        self.hbox_layout_left.addWidget(self.interface_left)
        self.hbox_layout_center.addWidget(self.interface_center)
        self.hbox_layout_right.addWidget(self.interface_right)
        # self.setStyleSheet("border: 1px solid black;")
        # 启动快捷键监听

        self._listener_start()
        mediator.hotkey_listener_stop_signal.connect(self._listener_stop)
        mediator.hotkey_listener_start_signal.connect(self._listener_start)

    def _listener_stop(self):
        self.listener.stop()
    def _listener_start(self):
        try:
            self.listener = keyboard.GlobalHotKeys(
                {
                    cfg.shutdown_hotkey: self.my_stop_shortcut,
                    cfg.pause_hotkey: self.my_pause_and_resume,
                    cfg.resume_hotkey: self.my_pause_and_resume,
                }
            )
            self.listener.start()
        except ValueError:
            log.error("快捷键监听启动失败，请确认设置的快捷键格式有效")

    def my_stop_shortcut(self):
        mediator.link_start.emit()

    def my_pause_and_resume(self):
        auto.set_pause()

class FarmingInterfaceLeft(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.setObjectName("FarmingInterfaceLeft")

        self.my_script = None

        self.__init_widget()
        self.__init_card()
        self.__init_layout()

        self.connect_mediator()

        LanguageManager().register_component(self)

    def __init_widget(self):
        self.hbox_layout = QVBoxLayout(self)
        self.setting_layout = QVBoxLayout()
        self.setting_options = QVBoxLayout()
        self.setting_options.setSpacing(10)

        self.setting_box = BaseSettingLayout()
        self.setting_box.setLayout(self.setting_layout)

    def __init_card(self):
        self.set_windows = CheckBoxWithButton(
            "set_windows",
            QT_TRANSLATE_NOOP("CheckBoxWithButton", "窗口设置"),
            None,
            "set_windows",
        )
        self.set_windows.set_box_enabled(False)

        self.daily_task = CheckBoxWithButton(
            "daily_task",
            QT_TRANSLATE_NOOP("CheckBoxWithButton", "日常任务"),
            None,
            "daily_task",
        )

        self.get_reward = CheckBoxWithButton(
            "get_reward",
            QT_TRANSLATE_NOOP("CheckBoxWithButton", "领取奖励"),
            None,
            "get_reward",
        )
        self.buy_enkephalin = CheckBoxWithButton(
            "buy_enkephalin",
            QT_TRANSLATE_NOOP("CheckBoxWithButton", "狂气换体"),
            None,
            "buy_enkephalin",
        )
        self.mirror = CheckBoxWithButton(
            "mirror",
            QT_TRANSLATE_NOOP("CheckBoxWithButton", "坐牢设置"),
            None,
            "mirror",
        )
        self.resonate_with_Ahab = CheckBoxWithButton(
            "resonate_with_Ahab",
            QT_TRANSLATE_NOOP("CheckBoxWithButton", "亚哈共鸣"),
            None,
            "resonate_with_Ahab",
        )

        self.resonate_with_Ahab.button.setEnabled(False)

        self.select_all = NormalTextButton(
            QT_TRANSLATE_NOOP("NormalTextButton", "全选"), "select_all"
        )
        self.select_all.clicked.connect(self.select_all_function)

        self.clear_all = NormalTextButton(
            QT_TRANSLATE_NOOP("NormalTextButton", "清空"), "clear_all"
        )
        self.clear_all.clicked.connect(self.clear_all_function)

        self.then = BaseLabel(QT_TRANSLATE_NOOP("BaseLabel", "之后"))

        self.then_combobox = BaseComboBox("after_completion")
        self.then_combobox.add_items(set_after_completion_options)
        self.then_combobox.set_options(0)
        self.link_start_button = NormalTextButton("Link Start!", "link_start", 0)
        self.link_start_button.clicked.connect(self.start_and_stop_tasks)
        self.link_start_button.button.setMinimumSize(130, 70)
        scale_factor = (
            QApplication.primaryScreen().logicalDotsPerInch() / 96
        )  # Windows 标准 DPI 是 96
        font_size = min(14, int(14 / scale_factor))
        # 创建字体对象并设置大小
        font = self.link_start_button.button.font()  # 获取当前字体
        font.setPointSize(font_size)  # 设置字体大小（单位：点）
        self.link_start_button.button.setFont(font)  # 应用新字体

    def __init_layout(self):
        self.setting_options.addWidget(self.set_windows)
        self.setting_options.addWidget(self.daily_task)
        self.setting_options.addWidget(self.get_reward)
        self.setting_options.addWidget(self.buy_enkephalin)
        self.setting_options.addWidget(self.mirror)
        self.setting_options.addWidget(self.resonate_with_Ahab)
        self.setting_layout.addLayout(self.setting_options)

        self.hbox_button = QHBoxLayout()
        self.hbox_button.addWidget(self.select_all)
        self.hbox_button.addWidget(self.clear_all)

        self.setting_layout.addLayout(self.hbox_button)

        self.hbox_layout.addWidget(self.setting_box)
        self.hbox_layout.addWidget(self.then)
        self.hbox_layout.addWidget(self.then_combobox)
        self.hbox_layout.addWidget(self.link_start_button)

    @staticmethod
    def select_all_function():
        for check_box in task_check_box[:5]:
            check_box.setChecked(True)

    @staticmethod
    def clear_all_function():
        for check_box in task_check_box[1:5]:
            check_box.setChecked(False)

    def stop_AALC(self):
        log.debug("即将关闭AALC")
        sys.exit(0)

    def check_setting(self):
        # 检测是否有未保存的镜牢队伍设置
        if self.parent().parent().findChild(TeamSettingCard):
            list(self.parent().parent().parent().pivot.items.values())[-1].click()
            mediator.save_warning.emit()
            return False

        if cfg.mirror:
            # 判断是否启用了自动切换困牢
            if cfg.auto_hard_mirror:
                from datetime import datetime

                get_timezone()
                if cfg.last_auto_change == 1715990400:
                    cfg.set_value("last_auto_change", datetime.now().timestamp())
                    cfg.flush()
                if check_hard_mirror_time():
                    log.info("识别到新的困牢周期，自动切换困难镜牢，设置困牢次数为3")
                    cfg.set_value("last_auto_change", datetime.now().timestamp())
                    cfg.set_value("hard_mirror", True)
                    cfg.set_value("hard_mirror_chance", 3)
                if cfg.hard_mirror_chance > 0:
                    cfg.set_value("hard_mirror", True)

            # 检查队伍配置状况
            teams_be_select = sum(1 for team in cfg.teams_be_select if team)
            if teams_be_select != cfg.teams_be_select_num:
                cfg.set_value("teams_be_select_num", teams_be_select)
                from utils.utils import check_teams_order

                teams_order = check_teams_order(cfg.teams_order)
                cfg.set_value("teams_order", teams_order)
                cfg.flush()

            if cfg.teams_be_select_num == 0:
                message = self.tr("没有启用任何队伍，请选择一个队伍进行镜牢任务")
                mediator.warning.emit(message)
                return False

            # 检测是否有未配置角色选择的队伍
            teams_be_select = cfg.get_value("teams_be_select")
            for index in (i for i, t in enumerate(teams_be_select) if t is True):
                team_setting = cfg.get_value(f"team{index + 1}_setting")
                if team_setting["sinners_be_select"] == 0:
                    message = self.tr("存在未配置角色选择的队伍：TEAM_{0}")
                    mediator.warning.emit(message.format(index + 1))
                    return False

            # 检测配置的队伍能否顺利执行
            useful = False
            hard = bool(cfg.hard_mirror)
            teams_be_select = cfg.get_value("teams_be_select")
            for index in (i for i, t in enumerate(teams_be_select) if t is True):
                team_setting = cfg.get_value(f"team{index + 1}_setting")
                if team_setting["fixed_team_use"] is False:
                    useful = True
                    break
                if team_setting["fixed_team_use_select"] == 1 and hard is False:
                    useful = True
                    break
                if team_setting["fixed_team_use_select"] == 0 and hard is True:
                    useful = True
                    break
            if useful is False:
                if hard:
                    message = self.tr("启用了困牢，但是无可用于困牢的队伍")
                else:
                    message = self.tr("启用了普牢，但是无可用于普牢的队伍")
                mediator.warning.emit(message)
                return False

        if (
            cfg.daily_task is False
            and cfg.get_reward is False
            and cfg.buy_enkephalin is False
            and cfg.mirror is False
        ):
            mediator.tasks_warning.emit()
            return False

    def start_and_stop_tasks(self):
        # 设置按下启动与停止按钮时，其他模块的启用与停用
        current_text = self.link_start_button.get_text()
        if current_text == "Link Start!":
            # 启动前检查设置，防呆
            if self.check_setting() is False:
                return
            self.link_start_button.set_text("S t o p !")
            self._disable_setting(self.parent())
            self.create_and_start_script()
        else:
            if cfg.simulator is False:
                screen.reset_win()
            else:
                if cfg.simulator_type == 0:
                    from module.simulator.mumu_control import MumuControl
                    while True:
                        try:
                            MumuControl.clean_connect()
                            break
                        except:
                            continue
                else:
                    from module.simulator.simulator_control import SimulatorControl
                    while True:
                        try:
                            SimulatorControl.clean_connect()
                            break
                        except:
                            continue
            self.link_start_button.set_text("Link Start!")
            self._enable_setting(self.parent())
            mediator.refresh_teams_order.emit()
            self.stop_script()
            auto.clear_img_cache()
            mediator.mirror_bar_kill_signal.emit()

    def _disable_setting(self, parent):
        for child in parent.children():
            # 跳过非 QWidget 类型的子对象（如信号、槽等）
            if not isinstance(child, QWidget):
                continue
            if child.objectName() == "link_start":
                continue
            # 检查是否为目标控件类型
            if isinstance(child, (ToSettingButton, CheckBox, PushButton, ComboBox, SpinBox, TransparentToolButton)):
                child.setEnabled(False)
            else:
                # 递归处理子部件的子部件（如布局中的嵌套控件）
                self._disable_setting(child)

    def _enable_setting(self, parent):
        for child in parent.children():
            # 跳过非 QWidget 类型的子对象（如信号、槽等）
            if not isinstance(child, QWidget):
                continue
            if child.objectName() == "set_windows":
                continue
            # 检查是否为目标控件类型
            if isinstance(child, (ToSettingButton, CheckBox, PushButton, ComboBox, SpinBox, TransparentToolButton)):
                child.setEnabled(True)
            else:
                # 递归处理子部件的子部件（如布局中的嵌套控件）
                self._enable_setting(child)

    def create_and_start_script(self):
        try:
            msg = f"开始进行所有任务"
            log.info(msg)
            mediator.scroll_log_show.emit("clear")
            # 启动脚本线程
            self.my_script = my_script_task()
            # 设置脚本线程为守护(当程序被关闭，一起停止)
            self.my_script.daemon = True
            self.my_script.start()
        except Exception as e:
            log.error(f"启动脚本失败: {e}")

    def stop_script(self):
        if self.my_script and self.my_script.isRunning():
            log.debug("正在终止脚本线程...")
            self.my_script.terminate()  # 终止线程

    def my_stop_shortcut(self):
        current_text = self.link_start_button.get_text()
        if current_text != "Link Start!":
            self.link_start_button.be_click()

    def connect_mediator(self):
        # 连接所有可能信号
        mediator.link_start.connect(self.my_stop_shortcut)
        mediator.kill_signal.connect(self.stop_AALC)
        mediator.finished_signal.connect(self.start_and_stop_tasks)

    def retranslateUi(self):
        self.set_windows.retranslateUi()
        self.daily_task.retranslateUi()
        self.get_reward.retranslateUi()
        self.buy_enkephalin.retranslateUi()
        self.mirror.retranslateUi()
        self.resonate_with_Ahab.retranslateUi()

        self.then.retranslateUi()
        self.then_combobox.retranslateUi()
        self.select_all.retranslateUi()
        self.clear_all.retranslateUi()


class FarmingInterfaceCenter(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.setObjectName("FarmingInterfaceCenter")
        self.__init_widget()
        self.__init_card()
        self.__init_layout()
        self.__init_setting()

        self.connect_mediator()

        LanguageManager().register_component(self)

    def __init_widget(self):
        # self.setting_box = CardWidget()
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
        # self.setting_box.setLayout(self.vbox)

    def __init_setting(self):
        self.setting_page.setCurrentIndex(cfg.get_value("default_page"))
        list(toggle_button_group.items())[cfg.get_value("default_page")][1].setChecked(
            True
        )

    def switch_to_page(self, target: str):
        try:
            """切换页面（带越界保护）"""
            page_index = page_name_and_index[target]
            self.setting_page.setCurrentIndex(page_index) # 当调用 setCurrentIndex 时，StackedWidget 会自动播放过渡动画
            cfg.set_value("default_page", page_index)
        except Exception as e:
            log.error(f"【异常】switch_to_page 出错：{type(e).__name__}:{e}")

    def connect_mediator(self):
        # 连接所有可能信号
        mediator.switch_page.connect(self.switch_to_page)

    def retranslateUi(self):
        self.set_windows.retranslateUi()
        self.daily_task.retranslateUi()
        self.get_reward.retranslateUi()
        self.buy_enkephalin.retranslateUi()
        self.mirror.retranslateUi()


class FarmingInterfaceRight(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.__init_widget()
        self.__init_card()
        self.__init_layout()
        self.last_position = 0

        self._apply_theme_style()
        
        self.timer = QTimer()
        self.timer.timeout.connect(lambda option=0: self.set_log(option))
        self.timer.start(1000)  # 每秒更新一次

        self.connect_mediator()


    def __init_widget(self):
        self.main_layout = QVBoxLayout(self)
        
    def __init_card(self):
        self.scroll_log_edit = TextEdit()
        self.scroll_log_edit.setAutoFormatting(QTextEdit.AutoFormattingFlag.AutoAll)
        self.scroll_log_edit.setReadOnly(True)

    def _apply_theme_style(self):
        light, dark = get_log_text_edit_qss()
        setCustomStyleSheet(self.scroll_log_edit, light, dark)
        self.scroll_log_edit.layer.hide() # 隐藏指示线

    def __init_layout(self):
        self.main_layout.addWidget(self.scroll_log_edit)

    def set_scroll_log(self, target: str):
        if target == "clear":
            self.scroll_log_edit.clear()
            self.set_log(option=1)
            self.last_position = 0

    def load_log_text(self):
        log_path = "./logs/user.log"
        MAX_SIZE_BYTES = 500 * 1024

        if not os.path.exists(log_path):
            return
        else:
            file_size_bytes = os.path.getsize(log_path)
            if file_size_bytes > MAX_SIZE_BYTES:
                os.remove(log_path)
                log.info("日志文件大小超过500KB，为防止加载过久或卡死，已删除")
        file = QFile(log_path)
        if not file.exists():
            return
        if not file.open(QFile.ReadOnly):
            return

        if not hasattr(self, "last_position"):
            self.last_position = 0

        # 跳到上次读取位置
        file.seek(self.last_position)
        raw = file.readAll()  # QByteArray
        self.last_position = file.pos()
        file.close()

        if not raw:
            return

        try:
            new_content = bytes(raw).decode("utf-8", errors="replace")
        except Exception:
            new_content = str(raw)

            # 追加内容
        if new_content:
            at_bottom = (
                self.scroll_log_edit.verticalScrollBar().value()
                == self.scroll_log_edit.verticalScrollBar().maximum()
            )
            # 按行追加，避免 QTextEdit.append 在多段文本中额外插入空行
            for line in new_content.splitlines():
                self.scroll_log_edit.append(line)
            if at_bottom:
                self.scroll_log_edit.moveCursor(self.scroll_log_edit.textCursor().End)

    def clear_all_log(self):
        file = QFile("./logs/user.log")
        if not file.open(QFile.WriteOnly | QFile.Text):
            self.scroll_log_edit.append("无法打开文件")
            return

        # 清空文件内容
        file.write(b"")

        # 关闭文件
        file.close()
        # 重新加载文件内容到 QTextEdit
        self.load_log_text()

    def set_log(self, option=0):
        if option == 0:
            try:
                self.load_log_text()
            except:
                pass

        else:
            try:
                self.clear_all_log()
            except:
                pass

    def connect_mediator(self):
        # 连接所有可能信号
        mediator.scroll_log_show.connect(self.set_scroll_log)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = FarmingInterface()
    w.show()
    app.exec()
