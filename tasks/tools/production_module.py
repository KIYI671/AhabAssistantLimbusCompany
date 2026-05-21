from datetime import datetime, timedelta
from time import monotonic

import win32con
import win32gui
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QCheckBox,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import qconfig

from module.automation import auto
from module.config import cfg
from module.game_and_screen import screen
from module.logger import log
from module.my_error.my_error import userStopError
from tasks.base.back_init_menu import back_init_menu
from tasks.base.make_enkephalin_module import (
    get_current_enkephalin,
    get_the_timing,
    make_enkephalin_module,
)
from tasks.base.retry import kill_game
from tasks.tools.ui_style import apply_tool_window_theme, get_status_label_style


class ProductionWork(QThread):
    """生产逻辑工作线程，避免阻塞UI"""

    production_executed = Signal()
    error_occurred = Signal(str)
    initialization_complete = Signal()
    on_waiting_occurred = Signal(int, int, int)

    def __init__(self, kill_game=False, parent=None):
        super().__init__(parent)
        self.production_running = True
        self.kill_game = kill_game
        self._init_retry_count = 0
        self._last_back_init_restart_time = 0.0

    def stop(self):
        """停止工作线程"""
        self.production_running = False

    def run(self):
        """工作线程的主循环"""
        while self.production_running:
            # 首先进行游戏初始化
            try:
                from tasks.base.script_task_scheme import init_game

                init_game()
                self._init_retry_count = 0
                self._set_win()
                self.initialization_complete.emit()
            except userStopError:
                return
            except Exception as e:
                if not cfg.simulator and self._is_set_window_access_denied(e):
                    self._init_retry_count += 1
                    if self._init_retry_count <= 8:
                        wait_seconds = min(2 * self._init_retry_count, 10)
                        msg = f"游戏窗口尚未就绪，{wait_seconds}秒后重试初始化 ({self._init_retry_count}/8)"
                        log.warning(
                            f"init_game 遇到 SetWindowPos 拒绝访问，等待{wait_seconds}秒重试"
                            f" ({self._init_retry_count}/8): {e}"
                        )
                        self.error_occurred.emit(msg)
                        self.msleep(wait_seconds * 1000)
                        continue
                self.error_occurred.emit(f"游戏初始化错误: {str(e)}")
                self.msleep(2000)
                return
            try:
                if self._back_init_menu_with_tool_policy() is False:
                    log.warning("自动换饼返回主界面失败，准备重新初始化后重试")
                    self.msleep(1000)
                    continue
                make_enkephalin_module(cancel=False, skip=False)
                while not auto.find_element("enkephalin/lunacy_assets.png", take_screenshot=True):
                    auto.click_element("enkephalin/use_lunacy_assets.png")
                current_enkephalin = get_current_enkephalin()
                if current_enkephalin is None:
                    log.warning("无法识别当前体力，跳过本次循环")
                    self._sleep_with_stop_check(30)
                    continue
                timing = None
                for _ in range(60):
                    timing = get_the_timing(return_time=True)
                    if timing:
                        break
                if timing is None:
                    log.warning("无法获取体力回复时间，跳过本次循环")
                    self._sleep_with_stop_check(60)
                    continue
                auto.mouse_click_blank()
                if current_enkephalin >= 20:
                    make_enkephalin_module(skip=False)
                sleep_time = (20 - current_enkephalin % 20 - 1) * 6 * 60 + timing
                self.on_waiting_occurred.emit(current_enkephalin, timing, sleep_time)
                if self.kill_game:
                    kill_game()
                self._sleep_with_stop_check(float(sleep_time))
            except userStopError:
                return

    def _back_init_menu_with_tool_policy(self) -> bool:
        restart_timeout = 180.0 if cfg.simulator else 120.0
        restart_cooldown = 120.0 if cfg.simulator else 60.0
        start_time = monotonic()

        while self.production_running:
            if back_init_menu(allow_restart=False):
                return True

            elapsed = monotonic() - start_time
            if elapsed < restart_timeout:
                log.warning(f"自动换饼返回主界面未完成，已尝试{int(elapsed)}秒，继续尝试")
                self._sleep_with_stop_check(1.5)
                continue

            now = monotonic()
            since_last_restart = now - self._last_back_init_restart_time
            if since_last_restart < restart_cooldown:
                wait_seconds = max(1, int(restart_cooldown - since_last_restart))
                log.warning(f"自动换饼返回主界面超时，但仍在重启冷却期，等待{wait_seconds}秒后继续尝试")
                self._sleep_with_stop_check(min(wait_seconds, 5))
                continue

            log.error(f"自动换饼返回主界面超时（{int(elapsed)}秒），执行一次重启恢复")
            self._last_back_init_restart_time = now
            try:
                kill_game()
                from tasks.base.script_task_scheme import init_game

                init_game()
                self._set_win()
            except userStopError:
                raise
            except Exception as e:
                log.error(f"自动换饼重启后初始化失败: {e}")
                self.error_occurred.emit(f"自动换饼重启后初始化失败: {e}")
                self._sleep_with_stop_check(2)
            start_time = monotonic()

        return False

    def _sleep_with_stop_check(self, seconds: float):
        end_time = monotonic() + max(0.0, seconds)
        while monotonic() < end_time and self.production_running:
            remain = end_time - monotonic()
            self.msleep(max(50, int(min(0.5, remain) * 1000)))

    @staticmethod
    def _is_set_window_access_denied(error: Exception) -> bool:
        args = getattr(error, "args", ())
        if len(args) >= 2:
            try:
                if int(args[0]) == 5 and str(args[1]) == "SetWindowPos":
                    return True
            except Exception:
                pass
        msg = str(error)
        return "SetWindowPos" in msg and ("拒绝访问" in msg or "Access is denied" in msg)

    def _set_win(self):
        if cfg.simulator:
            return
        try:
            hwnd = screen.handle.hwnd
            if hwnd == 0 or not win32gui.IsWindow(hwnd):
                log.debug("自动换饼跳过窗口置顶恢复：未获取到有效游戏窗口句柄")
                return
            win32gui.SetWindowPos(
                hwnd,  # 目标窗口句柄
                win32con.HWND_NOTOPMOST,  # 关键参数：取消置顶
                0,
                0,
                0,
                0,  # 忽略位置和大小（保持原样）
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
            instruction_text = "在T巢，大家都知道有更多的时间才能够挣到更多的时间\n\n榨取每一分利润、防止任何浪费是每一个资本家的拿手好戏\n\n来试试这款全新的自动节约小助手吧，为你攫取每一分属于你的利益\n\n（本广告五毛一条，记得删括号内的内容）"
        else:
            instruction_text = "At T-Nest, everyone knows that more time is the only way to earn more time\n\nSqueezing every penny of profit and preventing any waste is the specialty of every capitalist\n\nTry this new automatic savings assistant to grab every penny of your own interests\n\n(This ad is five cents. Remember to delete the content in brackets)"

        self.instruction_label = QLabel(instruction_text)
        self.instruction_label.setWordWrap(True)
        layout.addWidget(self.instruction_label)

        # 添加状态显示标签
        self.status_label = QLabel("状态：初始化中...")
        self._apply_theme_style()
        qconfig.themeChanged.connect(self._apply_theme_style)
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

    def _apply_theme_style(self):
        apply_tool_window_theme(self, "ProductionModule")
        self.status_label.setStyleSheet(get_status_label_style())

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
            if cfg.set_reduce_miscontact and not cfg.simulator:
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
        if not hasattr(self, "_last_log_time") or current_time - self._last_log_time > 10:
            self.log_text.append("生产操作执行")
            self._last_log_time = current_time

    def on_error_occurred(self, error_msg):
        """当发生错误时调用"""
        self.status_label.setText(f"状态：错误 - {error_msg[:50]}...")
        self.log_text.append(f"错误: {error_msg}")
        log.error(f"生产错误: {error_msg}")

    def on_waiting_occurred(self, current_enk, next_time, waiting_time):
        """当发生等待时调用"""
        now_time = datetime.now()
        self.log_text.append(f"当前时间: {now_time.strftime('%Y-%m-%d %H:%M:%S')}")
        self.log_text.append(f"当前体力: {current_enk}")
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
        if self.worker is not None and self.worker.isRunning():
            try:
                if cfg.set_reduce_miscontact and not cfg.simulator:
                    screen.reset_win()
                auto.clear_img_cache()
            except Exception as e:
                log.error(f"关闭自动换饼窗口时清理失败: {e}")
        event.accept()
