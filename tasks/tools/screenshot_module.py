from module.automation import auto
from module.config import cfg
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
            return
        try:
            img = auto.take_screenshot(gray=False)
            if img:
                timestr = time.strftime("%Y%m%d_%H%M%S", time.localtime())
                img.save(f"screenshot_{timestr}.png")
        except Exception as e:
            log.error(f"截图错误: {str(e)}")
            return
        screen.reset_win()
        log.info("截图已保存")

