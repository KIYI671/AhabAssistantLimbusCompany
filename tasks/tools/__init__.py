import threading
from typing import Literal

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
import sys

from module.logger import log
from tasks.base.script_task_scheme import init_game
from tasks.tools.infinite_battle import InfiniteBattles


class ToolManager:
    def run(self, tool: Literal["battle"]):
        try:
            if tool == "battle":
                self.run_battle()
        except Exception as e:
            log.ERROR(e)


    def run_battle(self):
        """自动战斗：在主线程事件循环中展示新窗口"""
        app = QApplication.instance()
        if app is None:
            # 无运行中的 Qt 应用，无法安全创建窗口
            log.ERROR("未检测到正在运行的 Qt 应用，无法展示小工具窗口。请从主程序内启动该工具。")
            return

        def create_and_show():
            try:
                w = InfiniteBattles()
                w.show()
                # 持有引用，避免被 GC 过早销毁
                if not hasattr(self, "_windows"):
                    self._windows = []
                self._windows.append(w)
                # 窗口销毁时移除引用
                w.destroyed.connect(lambda *_: hasattr(self, "_windows") and self._windows.remove(w) if w in self._windows else None)
            except Exception as e:
                log.ERROR(e)

        # 将创建窗口的操作排队到主线程事件循环
        QTimer.singleShot(0, app, create_and_show)



def start(tool: Literal["battle"]):
    """
    启动工具管理器的方法。
    :param tool: 启动工具，可以是"battle"。
    """
    tool_manager = ToolManager()
    tool_gui_thread = threading.Thread(target=tool_manager.run, args=(tool,), daemon=True)
    tool_gui_thread.start()
