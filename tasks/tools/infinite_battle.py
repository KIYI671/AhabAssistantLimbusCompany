from time import sleep
import traceback

import win32con
import win32gui
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QPushButton, QTextEdit, QHBoxLayout
from PySide6.QtCore import QTimer, QThread, Signal, Qt
from PySide6.QtGui import QIcon

from module.automation import auto
from module.config import cfg
from utils.image_utils import ImageUtils
from module.logger import log
from tasks.battle.battle import Battle
from pynput import keyboard
from module.game_and_screen import screen


class BattleWorker(QThread):
    """战斗逻辑工作线程，避免阻塞UI"""
    battle_executed = Signal()
    error_occurred = Signal(str)
    initialization_complete = Signal()
    
    def __init__(self, parent=None, is_guard=False):
        super().__init__(parent)
        self.identify_keyword_turn = True
        self.fail_count = 0
        self.running = True
        self.initialized = False
        self.is_guard = is_guard
    def stop(self):
        self.running = False
        
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
        
        # 主循环
        while self.running:
            try:
                self.execute_battle_logic()
                self.msleep(500)  # 500ms 间隔，不阻塞UI
            except Exception as e:
                self.error_occurred.emit(f"战斗逻辑错误: {str(e)}")
                self.msleep(1000)
                
    def execute_battle_logic(self):
        """执行战斗逻辑"""
        if not self.initialized:
            return  # 等待初始化完成
            
        window = win32gui.FindWindow("UnityWndClass", "LimbusCompany")
        if window:
            try:
                if not cfg.background_click:
                    original_index = self.get_z_order_index(window)
                    win32gui.SetWindowPos(
                        window,
                        win32con.HWND_TOP,
                        0, 0, 0, 0,
                        win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE
                    )
                auto.take_screenshot()
                
                if self.fail_count >= 5 or self.identify_keyword_turn is False:
                    self._ocr_battle()
                elif self.is_guard:
                    self._guard_battle()
                else:
                    self._template_battle()
                if not cfg.background_click:
                    self.restore_target_z_order(window, original_index)
                self.battle_executed.emit()
            except Exception as e:
                self.error_occurred.emit(f"窗口操作错误: {str(e)}")
        else:
            # 游戏窗口未找到，但不重新初始化，只是等待
            self.error_occurred.emit("未找到游戏窗口，等待中...")

    def _ocr_battle(self):
        turn_bbox = ImageUtils.get_bbox(ImageUtils.load_image("battle/turn_assets.png"))
        turn_ocr_result = auto.find_text_element("turn", turn_bbox)
        if turn_ocr_result is not False:
            self.fail_count = 0
            # 守备战斗
            if self.is_guard:
                auto.mouse_click_blank(move_back=True)
                Battle._defense_first_round(move_back=True)
                auto.key_press("enter")
                self.identify_keyword_turn = cfg.background_click
                return
            # 普通战斗
            auto.mouse_click_blank(move_back=True)
            auto.key_press("p")
            sleep(0.5)
            auto.key_press("enter")
            self.identify_keyword_turn = cfg.background_click
        else:
            self.fail_count += 1
            wait_time = min(1 * (self.fail_count + 1), 8)  # 最大等待8秒
            sleep(wait_time)

    def _template_battle(self):
        if auto.click_element("battle/turn_assets.png") or auto.find_element("battle/win_rate_assets.png"):
            auto.mouse_click_blank(move_back=True)
            auto.key_press('p')
            sleep(0.5)
            auto.key_press('enter')
            self.fail_count = 0
            return
        else:
            self.fail_count += 1
            sleep(1*(self.fail_count+1))

    def _guard_battle(self):
        if auto.click_element("battle/turn_assets.png") or auto.find_element("battle/win_rate_assets.png"):
            auto.mouse_click_blank(move_back=True)
            Battle._defense_first_round()
            auto.key_press('enter')
            self.fail_count = 0
            return
        else:
            self.fail_count += 1
            sleep(1*(self.fail_count+1))

    def _set_win(self):
        try:
            
            hwnd = screen.handle
            win32gui.SetWindowPos(
                hwnd._hWnd,  # 目标窗口句柄
                win32con.HWND_NOTOPMOST,  # 关键参数：取消置顶
                0, 0, 0, 0,  # 忽略位置和大小（保持原样）
                win32con.SWP_NOMOVE | win32con.SWP_NOSIZE  # 标志位：不移动、不调整大小
            )
        except Exception as e:
            self.error_occurred.emit(f"窗口设置错误: {str(e)}")

    @staticmethod
    def get_z_order_index(hwnd: int) -> int:
        """获取目标窗口在当前顶层窗口中的 Z 顺序索引（0 为最高）"""
        z_order = []

        def enum_callback(hwnd_enum, _):
            # 仅收集可见的顶层窗口（无父窗口）
            if win32gui.IsWindowVisible(hwnd_enum) and win32gui.GetParent(hwnd_enum) == 0:
                z_order.append(hwnd_enum)
            return True

        win32gui.EnumWindows(enum_callback, None)

        try:
            return z_order.index(hwnd)
        except ValueError:
            raise ValueError("目标窗口不是顶层窗口或不可见")

    @staticmethod
    def restore_target_z_order(hwnd: int, target_index: int):
        """将目标窗口恢复到指定的 Z 顺序索引位置"""
        # 获取当前所有可见顶层窗口的 Z 顺序（提升后的状态）
        current_z_order = []

        def enum_callback(hwnd_enum, _):
            if win32gui.IsWindowVisible(hwnd_enum) and win32gui.GetParent(hwnd_enum) == 0:
                current_z_order.append(hwnd_enum)
            return True

        win32gui.EnumWindows(enum_callback, None)

        try:
            current_index = current_z_order.index(hwnd)
        except ValueError:
            log.warning("目标窗口已不在顶层，无需恢复")
            return

        # 若目标窗口已在正确位置，无需操作
        if current_index == target_index:
            return

        # 计算需要插入的位置（目标索引）
        # 插入到目标索引的前一个窗口之后（或 HWND_TOP）
        if target_index == 0:
            insert_after = win32con.HWND_TOP
        else:
            # 目标索引的前一个窗口（需确保有效）
            insert_after = current_z_order[target_index - 1] if (target_index - 1) < len(
                current_z_order) else win32con.HWND_TOP

        # 移动目标窗口到指定位置（不影响其他窗口的相对顺序）
        win32gui.SetWindowPos(
            hwnd,
            insert_after,
            0, 0, 0, 0,
            win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE
        )


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
        
        if cfg.language_in_program == 'zh_cn':
            instruction_text = "你来到了\"都市\"，这里是不战斗就无法生存的修罗场\n\n幸好你得到了亚哈神力的相助\n\n\"亚哈降神附身代打\"获得了"
        else:
            instruction_text = "You have arrived at the 'The City', a crucible where survival is impossible without combat.\n\nFortunately, you have gained the aid of Ahab's divine power.\n\nEmpowered by Ahab's possession, she will fight for you."
        
        self.instruction_label = QLabel(instruction_text)
        self.instruction_label.setWordWrap(True)
        layout.addWidget(self.instruction_label)
        
        # 添加状态显示标签
        self.status_label = QLabel("状态：等待开始...")
        self.status_label.setStyleSheet("QLabel { background-color: #f0f0f0; padding: 5px; border: 1px solid #ccc; }")
        layout.addWidget(self.status_label)
        
        # 添加控制按钮
        button_layout = QHBoxLayout()
        
        self.start_stop_button = QPushButton("开始战斗")
        self.start_stop_button.clicked.connect(self.toggle_battle)
        self.guard_button = QPushButton("守备战斗")
        self.guard_button.clicked.connect(self.toggle_guard_battle)
        button_layout.addWidget(self.start_stop_button)
        button_layout.addWidget(self.guard_button)
        
        layout.addLayout(button_layout)
        
        # 添加日志显示
        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(150)
        self.log_text.setReadOnly(True)
        self.log_text.append("=== 自动战斗日志 ===")
        layout.addWidget(self.log_text)
        
        self.setLayout(layout)

    def start_battle(self, is_guard=False):
        """启动战斗工作线程"""
        if self.worker is None or not self.worker.isRunning():
            self.worker = BattleWorker(is_guard=is_guard)
            self.worker.battle_executed.connect(self.on_battle_executed)
            self.worker.error_occurred.connect(self.on_error_occurred)
            self.worker.initialization_complete.connect(self.on_initialization_complete)
            self.worker.start()
            self.start_stop_button.setText("停止战斗")
            self.guard_button.setText("停止战斗")
            self.log_text.append("正在初始化游戏...")
            self.status_label.setText("状态：初始化中...")
    
    def on_initialization_complete(self):
        """当初始化完成时调用"""
        self.log_text.append("游戏初始化完成，开始战斗")
        self.status_label.setText("状态：战斗中...")
    
    def stop_battle(self):
        """停止战斗工作线程"""
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait(2000)  # 等待2秒
            if self.worker.isRunning():
                self.worker.terminate()
                self.worker.wait(1000)
            self.start_stop_button.setText("开始战斗")
            self.guard_button.setText("守备战斗")
            self.log_text.append("战斗线程已停止")
            self.status_label.setText("状态：已停止")
            screen.reset_win()
    
    def toggle_battle(self):
        """切换战斗状态"""
        if self.worker and self.worker.isRunning():
            self.stop_battle()
        else:
            self.start_battle()

    def toggle_guard_battle(self):
        """切换守备战斗状态"""
        if self.worker and self.worker.isRunning():
            self.stop_battle()
        else:
            self.start_battle(is_guard=True)

    def on_battle_executed(self):
        """当执行战斗时调用"""
        self.status_label.setText("状态：正在战斗...")
        # 避免日志过多，只偶尔记录
        import time
        current_time = int(time.time())
        if not hasattr(self, '_last_log_time') or current_time - self._last_log_time > 10:
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
        if hasattr(self, 'worker') and self.worker:
            self.worker.stop()
            self.worker.wait(3000)  # 等待最多3秒
            if self.worker.isRunning():
                self.worker.terminate()

        # 资源清理
        try:
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
