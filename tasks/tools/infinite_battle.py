import win32con
import win32gui
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QPushButton, QTextEdit
from PySide6.QtCore import QThread, Signal, Qt
from PySide6.QtGui import QIcon

from module.config import cfg
from tasks.battle.battle import Battle
from module.logger import log


class BattleWorker(QThread):
    """战斗逻辑工作线程，避免阻塞UI"""

    battle_executed = Signal()
    error_occurred = Signal(str)
    initialization_complete = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.initialized = False
        self.battle = Battle()  # 复用镜牢战斗逻辑

    def stop(self):
        """停止工作线程"""
        self.battle.running = False

    def run(self):
        """工作线程的主循环"""
        # 首先进行游戏初始化
        if not self.initialized:
            try:
                from tasks.base.script_task_scheme import init_game

                init_game()
                self._set_win()
                self.initialized = True
                self.initialization_complete.emit()
            except Exception as e:
                self.error_occurred.emit(f"游戏初始化错误: {str(e)}")
                self.msleep(2000)
                return

        self.battle.fight()

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


class InfiniteBattles(QWidget):
    def __init__(self):
        """初始化 InfiniteBattles 类的实例。"""
        super().__init__()

        # 初始化战斗工作线程
        self.worker = BattleWorker()
        self.worker.finished.connect(self.on_battle_finished)
        self.worker.battle_executed.connect(self.on_battle_executed)
        self.worker.error_occurred.connect(self.on_error_occurred)
        self.worker.initialization_complete.connect(self.on_initialization_complete)

        # 关闭时删除自身，不影响其他窗口/应用
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.setup_ui()
        self.start_battle()

    def setup_ui(self):
        """配置窗口的基本属性和界面元素。"""
        self.setWindowTitle("自动战斗")
        self.setGeometry(100, 100, 600, 400)
        self.setWindowIcon(QIcon("./assets/logo/my_icon_256X256.ico"))

        # 创建布局
        layout = QVBoxLayout()

        if cfg.language_in_program == "zh_cn":
            instruction_text = '你来到了"都市"，这里是不战斗就无法生存的修罗场\n\n幸好你得到了亚哈神力的相助\n\n"亚哈降神附身代打"获得了'
        else:
            instruction_text = "You have arrived at the 'The City', a crucible where survival is impossible without combat.\n\nFortunately, you have gained the aid of Ahab's divine power.\n\nEmpowered by Ahab's possession, she will fight for you."

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

        self.start_stop_button = QPushButton("停止战斗")
        self.start_stop_button.clicked.connect(self.toggle_battle)
        button_layout.addWidget(self.start_stop_button)

        layout.addLayout(button_layout)

        # 添加日志显示
        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(150)
        self.log_text.setReadOnly(True)
        self.log_text.append("=== 自动战斗日志 ===")
        layout.addWidget(self.log_text)

        self.setLayout(layout)

    def start_battle(self):
        """启动战斗工作线程"""
        if not self.worker.isRunning():
            self.worker.start()
            self.start_stop_button.setText("停止战斗")
            self.log_text.append("正在初始化游戏...")
            self.status_label.setText("状态：初始化中...")

    def on_initialization_complete(self):
        """当初始化完成时调用"""
        self.log_text.append("游戏初始化完成，开始战斗")
        self.status_label.setText("状态：战斗中...")

    def on_battle_finished(self):
        self.log_text.append("战斗线程已停止")
        self.start_stop_button.setText("开始战斗")
        self.status_label.setText("状态：已停止")

    def stop_battle(self):
        """停止战斗工作线程"""
        if self.worker.isRunning():
            self.log_text.append("中止：等待战斗线程停止...")
            self.worker.stop()
            self.worker.wait(1000)  # 等待1秒
            if self.worker.isRunning():
                self.worker.terminate()
                self.worker.wait(1000)

    def toggle_battle(self):
        """切换战斗状态"""
        if self.worker.isRunning():
            self.stop_battle()
        else:
            self.start_battle()

    def on_battle_executed(self):
        """当执行战斗时调用"""
        self.status_label.setText("状态：正在战斗...")
        # 避免日志过多，只偶尔记录
        import time

        current_time = int(time.time())
        if (
            not hasattr(self, "_last_log_time")
            or current_time - self._last_log_time > 10
        ):
            self.log_text.append("战斗操作执行")
            self._last_log_time = current_time

    def on_error_occurred(self, error_msg):
        """当发生错误时调用"""
        self.status_label.setText(f"状态：错误 - {error_msg[:50]}...")
        self.log_text.append(f"错误: {error_msg}")
        log.error(f"战斗错误: {error_msg}")

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
            from module.automation import auto
            from module.game_and_screen import screen
            from module.ocr import ocr

            screen.reset_win()
            auto.clear_img_cache()
        except Exception:
            # 忽略清理异常，避免影响关闭
            pass
        event.accept()
