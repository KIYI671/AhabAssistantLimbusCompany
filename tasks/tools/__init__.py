import re
import threading
from typing import Literal

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
import sys

from module.logger import log
from tasks.base.script_task_scheme import init_game
from tasks.tools.infinite_battle import InfiniteBattles
from tasks.tools.production_module import ProductionModule
from tasks.tools.screenshot_module import ScreenshotGet


class ToolManager:
    def run(self, tool: Literal["battle", "production", "screenshot"]):
        try:
            self.run_tools(tool)
        except Exception as e:
            log.error(e)

    def run_tools(self, tool):
        """自动战斗：在主线程事件循环中展示新窗口"""
        app = QApplication.instance()
        if app is None:
            # 无运行中的 Qt 应用，无法安全创建窗口
            log.error("未检测到正在运行的 Qt 应用，无法展示小工具窗口。请从主程序内启动该工具。")
            return

        def create_and_show():
            try:
                w = None
                if tool == "battle":
                    w = InfiniteBattles()
                elif tool == "production":
                    w = ProductionModule()
                elif tool == "screenshot":
                    w = ScreenshotGet()
                    w.run()
                    return
                if w is None:
                    log.error(f"工具 {tool} 未能成功启动")
                    return
                w.show()
                # 持有引用，避免被 GC 过早销毁
                if not hasattr(self, "_windows"):
                    self._windows = []
                self._windows.append(w)
                # 窗口销毁时移除引用
                w.destroyed.connect(
                    lambda *_: hasattr(self, "_windows") and self._windows.remove(w) if w in self._windows else None)
            except Exception as e:
                log.error(e)

        # 将创建窗口的操作排队到主线程事件循环
        QTimer.singleShot(0, app, create_and_show)


def start(tool: Literal["battle", "production", "screenshot"]):
    """
    启动工具管理器的方法。
    :param tool: 启动工具，可以是"battle"。
    """
    tool_manager = ToolManager()
    tool_gui_thread = threading.Thread(target=tool_manager.run, args=(tool,), daemon=True)
    tool_gui_thread.start()
