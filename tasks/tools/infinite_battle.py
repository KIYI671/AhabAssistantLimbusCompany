import win32con
import win32gui
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QPushButton, QTextEdit, QCheckBox
from PySide6.QtCore import QThread, Signal, Qt
from PySide6.QtGui import QIcon

from module.automation import auto
from module.config import cfg
from module.logger import log
from tasks.battle.battle import Battle
from pynput import keyboard
from module.game_and_screen import screen
from utils import pic_path


class BattleWorker(QThread):
    """战斗逻辑工作线程，避免阻塞UI"""

    battle_executed = Signal()
    error_occurred = Signal(str)
    initialization_complete = Signal()

    def __init__(self, defense=False, parent=None):
        super().__init__(parent)
        self.defense = defense
        self.initialized = False
        self.battle = Battle()  # 复用镜牢战斗逻辑
        self.background_click = cfg.background_click

    def stop(self):
        """停止工作线程"""
        self.battle.running = False
        if self.background_click is False:
            cfg.set_value("background_click", False)

    def run(self):
        """工作线程的主循环"""
        # 首先进行游戏初始化
        if not self.initialized:
            try:
                from tasks.base.script_task_scheme import init_game

                init_game()
                self._set_win()
                if cfg.language_in_game == "zh_cn" and pic_path[0] != "zh_cn":
                    pic_path.insert(0, "zh_cn")
                elif cfg.language_in_game == "en":
                    while pic_path[0] != "share":
                        pic_path.pop(0)
                    pic_path.insert(0, "en")
                self.initialized = True
                self.initialization_complete.emit()
            except Exception as e:
                self.error_occurred.emit(f"游戏初始化错误: {str(e)}")
                self.msleep(2000)
                return
        self.battle.fight(infinite_battle=True, defense_all_time=self.defense)

    def _set_win(self):
        try:
            from module.game_and_screen import screen
            if not self.background_click:
                cfg.set_value("background_click", True)
            hwnd = screen.handle
            screen.set_win()
        except Exception as e:
            self.error_occurred.emit(f"窗口设置错误: {str(e)}")


class InfiniteBattles(QWidget):
    def __init__(self):
        """初始化 InfiniteBattles 类的实例。"""
        super().__init__()

        self.worker = None

        # 关闭时删除自身，不影响其他窗口/应用
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.setup_ui()

        # 启动快捷键监听
        self.listener = keyboard.GlobalHotKeys(
            {
                "<ctrl>+q": self._on_stop_shortcut,
            }
        )
        self.listener.start()

    def setup_ui(self):
        """配置窗口的基本属性和界面元素。"""
        self.setWindowTitle("自动战斗")
        self.setGeometry(100, 100, 600, 400)
        self.setWindowIcon(QIcon("./assets/logo/my_icon_256X256.ico"))

        # 创建布局
        layout = QVBoxLayout()

        if cfg.language_in_program == "zh_cn":
            instruction_text = '你来到了"都市"，这里是不战斗就无法生存的修罗场\n\n幸好你得到了亚哈神力的相助\n\n"亚哈降神附身代打"获得了\n\n使用<ctrl>+q 停止战斗'
        else:
            instruction_text = "You have arrived at the 'The City', a crucible where survival is impossible without combat.\n\nFortunately, you have gained the aid of Ahab's divine power.\n\nEmpowered by Ahab's possession, she will fight for you.\n\nUse <ctrl>+q to stop the battle."

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

        self.start_stop_button = QPushButton("开始战斗")
        self.start_stop_button.clicked.connect(self.toggle_battle)
        self.defense_box = QCheckBox("无限守备")
        button_layout.addWidget(self.start_stop_button)
        button_layout.addWidget(self.defense_box)

        button_layout.setAlignment(Qt.AlignCenter)

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
        if self.worker is None or not self.worker.isRunning():
            self.worker = BattleWorker(self.defense_box.isChecked())
            self.worker.finished.connect(self.on_battle_finished)
            self.worker.battle_executed.connect(self.on_battle_executed)
            self.worker.error_occurred.connect(self.on_error_occurred)
            self.worker.initialization_complete.connect(self.on_initialization_complete)
            self.worker.start()
            self.start_stop_button.setText("停止战斗")
            self.log_text.append("正在初始化游戏...")
            self.status_label.setText("状态：初始化中...")
            self.defense_box.setDisabled(True)

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
            if self.worker.background_click is False:
                cfg.set_value("background_click", False)
            self.worker.stop()
            self.worker.wait(1000)  # 等待1秒
            if self.worker.isRunning():
                self.worker.terminate()
                self.worker.wait(1000)
            self.defense_box.setDisabled(False)
            screen.reset_win()
            auto.clear_img_cache()

    def toggle_battle(self):
        """切换战斗状态"""
        if self.worker is None or not self.worker.isRunning():
            self.start_battle()
        else:
            self.stop_battle()

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
            if self.worker is not None and self.worker.isRunning():
                screen.reset_win()
                auto.clear_img_cache()
                self.listener.stop()
        except Exception:
            # 忽略清理异常，避免影响关闭
            pass
        event.accept()

    def _on_stop_shortcut(self):
        """快捷键停止战斗"""
        if self.worker and self.worker.isRunning():
            self.stop_battle()
