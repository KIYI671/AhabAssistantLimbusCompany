import sys
import threading
from typing import Literal

from PySide6.QtCore import QObject, QThread, QTimer
from PySide6.QtWidgets import QApplication, QWidget

from module.logger import log
from tasks.base.script_task_scheme import init_game
from tasks.tools.infinite_battle import InfiniteBattles
from tasks.tools.production_module import ProductionModule
from tasks.tools.screenshot_module import ScreenshotGet


class ToolManager:
    def __init__(self, tool: Literal["battle", "production", "screenshot"]):
        self.tool = tool
        self.initialized = False
        self.w: QObject = None

    def run(self):
        try:
            self.run_tools()
        except Exception as e:
            log.error(e)
            self.initialized = None  # 启动失败返回

    def run_tools(self):
        """自动战斗：在主线程事件循环中展示新窗口"""
        app = QApplication.instance()
        if app is None:
            # 无运行中的 Qt 应用，无法安全创建窗口
            log.error(
                "未检测到正在运行的 Qt 应用，无法展示小工具窗口。请从主程序内启动该工具。"
            )
            self.initialized = None
            return

        def create_and_show():
            try:
                if self.tool == "battle":
                    self.w = InfiniteBattles()
                elif self.tool == "production":
                    self.w = ProductionModule()
                elif self.tool == "screenshot":
                    self.w = ScreenshotGet()
                if self.w is None:
                    log.error(f"工具 {self.tool} 未能成功启动")
                    self.initialized = None  # 失败返回
                    return
                else:
                    log.debug(f"启动工具 {self.tool}")
                    self.initialized = True
                if isinstance(self.w, QWidget):
                    self.w.show()
                # 等待主线程启动, 防止信号连接前任务结束
                # elif isinstance(self.w, QThread):
                #     self.w.start()

            except Exception as e:
                log.error(e)
                self.initialized = None

        # 将创建窗口的操作排队到主线程事件循环
        QTimer.singleShot(0, app, create_and_show)


def start(tool: Literal["battle", "production", "screenshot"]):
    """
    启动工具管理器的方法。
    :param tool: 启动工具，可以是"battle"。
    """
    tool_manager = ToolManager(tool)
    tool_gui_thread = threading.Thread(target=tool_manager.run, daemon=True)
    tool_gui_thread.start()
    return tool_manager
