from module.automation import auto
from module.logger import log
from module.game_and_screen import screen
from PySide6.QtCore import QThread
import time

class ScreenshotGet(QThread):
    def __init__(self, parent=None):
        super().__init__(parent)

    def run(self):
        try:
            from tasks.base.script_task_scheme import init_game
            init_game()
        except Exception as e:
            log.error(f"初始化游戏失败: {str(e)}")
            return
        try:
            img = auto.take_screenshot(gray=False)
            if img:
                timestr = time.strftime("%Y%m%d_%H%M%S", time.localtime())
                img.save(f"screenshot_{timestr}.png")
                log.info(f"图片保存为 AALC > screenshot_{timestr}.png")
            else:
                log.error("截图失败，请确认游戏是否处于启动状态")
        except Exception as e:
            log.error(f"截图错误: {str(e)}")
            return
        screen.reset_win()

