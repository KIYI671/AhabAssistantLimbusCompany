from datetime import datetime, timedelta
from time import sleep

import win32con
import win32gui
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QPushButton, QTextEdit, QCheckBox
from PySide6.QtCore import QThread, Signal, Qt
from PySide6.QtGui import QIcon

from module.automation import auto
from module.config import cfg
from module.logger import log
from module.game_and_screen import screen
from tasks.base.back_init_menu import back_init_menu
from tasks.base.make_enkephalin_module import make_enkephalin_module, get_current_enkephalin, get_the_timing
from tasks.base.retry import kill_game
from utils import pic_path


class ProductionWork(QThread):
    """生产逻辑工作线程，避免阻塞UI"""

    production_executed = Signal()
    error_occurred = Signal(str)
    initialization_complete = Signal()
    on_waiting_occurred = Signal(int, int)

    def __init__(self, kill_game=False, parent=None):
        super().__init__(parent)
        self.production_running = True
        self.kill_game = kill_game

    def stop(self):
        """停止工作线程"""
        self.production_running = False

    def run(self):
        """工作线程的主循环"""
        if cfg.language_in_game == "zh_cn" and pic_path[0] != "zh_cn":
            pic_path.insert(0, "zh_cn")
        while self.production_running:
            # 首先进行游戏初始化
            try:
                from tasks.base.script_task_scheme import init_game

                init_game()
                self._set_win()
                self.initialization_complete.emit()
            except Exception as e:
                self.error_occurred.emit(f"游戏初始化错误: {str(e)}")
                self.msleep(2000)
                return
            back_init_menu()
            make_enkephalin_module(cancel=False, skip=False)
            while not auto.find_element("enkephalin/lunacy_assets.png"):
                auto.click_element("enkephalin/use_lunacy_assets.png")
            current_enkephalin = get_current_enkephalin()
            timing = None
            while True:
                timing = get_the_timing(return_time=True)
                if timing:
                    break
            auto.mouse_click_blank()
            if current_enkephalin and current_enkephalin >= 20:
                make_enkephalin_module(skip=False)
            sleep_time = (20 - current_enkephalin % 20 - 1) * 6 * 60 + timing
            self.on_waiting_occurred.emit(timing, sleep_time)
            if self.kill_game:
                kill_game()
            sleep(sleep_time)

    def _set_win(self):
        try:
            from module.game_and_screen import screen

            hwnd = screen.handle
            win32gui.SetWindowPos(
                hwnd._hWnd,  # 目标窗口句柄
                win32con.HWND_NOTOPMOST,  # 关键参数：取消置顶
                0, 0, 0, 0,  # 忽略位置和大小（保持原样）
                win32con.SWP_NOMOVE | win32con.SWP_NOSIZE,  # 标志位：不移动、不调整大小
            )
        except Exception as e:
            self.error_occurred.emit(f"窗口设置错误: {str(e)}")


class ProductionModule(QWidget):
    def __init__(self):
        """初始化 ProductionModule 类的实例。"""
        super().__init__()

        self.worker = None

        # 关闭时删除自身，不影响其他窗口/应用
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.setup_ui()

    def setup_ui(self):
        """配置窗口的基本属性和界面元素。"""
        self.setWindowTitle("自动换饼")
        self.setGeometry(100, 100, 600, 400)
        self.setWindowIcon(QIcon("./assets/logo/my_icon_256X256.ico"))

        # 创建布局
        layout = QVBoxLayout()

        if cfg.language_in_program == "zh_cn":
            instruction_text = '在T巢，大家都知道有更多的时间才能够挣到更多的时间\n\n榨取每一分利润、防止任何浪费是每一个资本家的拿手好戏\n\n来试试这款全新的自动节约小助手吧，为你攫取每一分属于你的利益\n\n（本广告五毛一条，记得删括号内的内容）'
        else:
            instruction_text = "At T-Nest, everyone knows that more time is the only way to earn more time\n\nSqueezing every penny of profit and preventing any waste is the specialty of every capitalist\n\nTry this new automatic savings assistant to grab every penny of your own interests\n\n(This ad is five cents. Remember to delete the content in brackets)"

        self.instruction_label = QLabel(instruction_text)
        self.instruction_label.setWordWrap(True)
        layout.addWidget(self.instruction_label)

        # 添加状态显示标签
        self.status_label = QLabel("状态：初始化中...")
        self.status_label.setStyleSheet(
            "QLabel { background-color: #f0f0f0; padding: 5px; border: 1px solid #ccc; }"
        )
        layout.addWidget(self.status_label)

        # 添加控制按钮
        button_layout = QVBoxLayout()

        self.start_msg = self.tr("开始任务")
        self.start_stop_button = QPushButton(self.start_msg)
        self.start_stop_button.clicked.connect(self.toggle_production)
        self.box_msg = self.tr("等待期间关闭游戏")
        self.kill_game_box = QCheckBox(self.box_msg)
        button_layout.addWidget(self.start_stop_button)
        button_layout.addWidget(self.kill_game_box)

        button_layout.setAlignment(Qt.AlignCenter)

        layout.addLayout(button_layout)

        # 添加日志显示
        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(150)
        self.log_text.setReadOnly(True)
        self.log_text.append("=== 自动工作日志 ===")
        layout.addWidget(self.log_text)

        self.setLayout(layout)

    def start_production(self):
        """启动生产工作线程"""
        if self.worker is None or not self.worker.isRunning():
            self.worker = ProductionWork(self.kill_game_box.isChecked())
            self.worker.finished.connect(self.on_production_finished)
            self.worker.production_executed.connect(self.on_production_executed)
            self.worker.error_occurred.connect(self.on_error_occurred)
            self.worker.initialization_complete.connect(self.on_initialization_complete)
            self.worker.on_waiting_occurred.connect(self.on_waiting_occurred)
            self.worker.start()
            stop_msg = self.tr("中止工作")
            self.start_stop_button.setText(stop_msg)
            self.log_text.append("正在初始化游戏...")
            self.status_label.setText("状态：初始化中...")
            self.kill_game_box.setDisabled(True)

    def on_initialization_complete(self):
        """当初始化完成时调用"""
        self.log_text.append("游戏初始化完成，开始工作")
        self.status_label.setText("状态：工作中...")

    def on_production_finished(self):
        self.log_text.append("工作线程已停止")
        self.start_stop_button.setText(self.start_msg)
        self.status_label.setText("状态：已停止")

    def stop_production(self):
        """停止工作工作线程"""
        if self.worker.isRunning():
            self.log_text.append("中止：等待工作线程停止...")
            self.worker.stop()
            self.worker.wait(1000)  # 等待1秒
            if self.worker.isRunning():
                self.worker.terminate()
                self.worker.wait(1000)
            self.kill_game_box.setDisabled(False)
            screen.reset_win()
            auto.clear_img_cache()

    def toggle_production(self):
        """切换生产状态"""
        if self.worker is None or not self.worker.isRunning():
            self.start_production()
        else:
            self.stop_production()

    def on_production_executed(self):
        """当执行生产时调用"""
        self.status_label.setText("状态：正在生产...")
        # 避免日志过多，只偶尔记录
        import time

        current_time = int(time.time())
        if (
                not hasattr(self, "_last_log_time")
                or current_time - self._last_log_time > 10
        ):
            self.log_text.append("生产操作执行")
            self._last_log_time = current_time

    def on_error_occurred(self, error_msg):
        """当发生错误时调用"""
        self.status_label.setText(f"状态：错误 - {error_msg[:50]}...")
        self.log_text.append(f"错误: {error_msg}")
        log.error(f"生产错误: {error_msg}")

    def on_waiting_occurred(self, next_time, waiting_time):
        """当发生等待时调用"""
        now_time = datetime.now()
        self.log_text.append(f"当前时间: {now_time.strftime('%Y-%m-%d %H:%M:%S')}")
        self.log_text.append(f"状态：等待 - 下一次体力回复时间: {next_time} s")
        self.log_text.append(f"等待: 下一次执行模块生产等待时间: {waiting_time} s")
        future_time = now_time + timedelta(seconds=waiting_time)
        self.log_text.append(f"预计下一次操作时间: {future_time.strftime('%Y-%m-%d %H:%M:%S')}")
        log.info(f"生产等待: 下一次体力回复时间: {next_time} s，下一次执行模块生产等待时间: {waiting_time} s")

    def closeEvent(self, event):
        """窗口关闭时停止所有定时器和工作线程"""
        # 停止工作线程
        if hasattr(self, "worker") and self.worker:
            self.worker.stop()
            self.worker.wait(3000)  # 等待最多3秒
            if self.worker.isRunning():
                self.worker.terminate()

        # 资源清理
        try:
            if self.worker is not None and self.worker.isRunning():
                screen.reset_win()
                auto.clear_img_cache()
                self.listener.stop()
        except Exception:
            # 忽略清理异常，避免影响关闭
            pass
        event.accept()
