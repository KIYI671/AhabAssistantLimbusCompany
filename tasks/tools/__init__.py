import threading
import tkinter as tk
from typing import Literal

from module.logger import log
from tasks.base.script_task_scheme import init_game
from tasks.tools.infinite_battle import InfiniteBattles


class ToolManager:
    def run(self, tool: Literal["battle"]):
        try:
            init_game()
            if tool == "battle":
                self.run_battle()
        except Exception as e:
            log.ERROR(e)
        finally:
            from module.automation import auto
            from module.game_and_screen import screen
            from module.ocr import ocr
            screen.reset_win()
            ocr.exit_ocr()
            auto.clear_img_cache()

    def run_battle(self):
        """自动战斗"""
        root = tk.Tk()
        InfiniteBattles(root)
        root.mainloop()


def start(tool: Literal["battle"]):
    """
    启动工具管理器的方法。
    :param tool: 启动工具，可以是"battle"。
    """
    tool_manager = ToolManager()
    gui_thread = threading.Thread(target=tool_manager.run, args=(tool,))
    gui_thread.start()
