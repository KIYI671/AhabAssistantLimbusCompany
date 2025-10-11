from module.automation import auto
from module.config import cfg
from module.logger import log
from module.game_and_screen import screen
from PySide6.QtCore import QThread
from app.card.messagebox_custom import BaseInfoBar
from PySide6.QtCore import QT_TRANSLATE_NOOP, Qt
from qfluentwidgets import FluentIcon as FIF, InfoBarPosition
from qfluentwidgets import ScrollArea
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
        bar = BaseInfoBar.success(
            title=QT_TRANSLATE_NOOP("BaseInfoBar", '截图完成'),
            content=f'图片保存为 screenshot_{timestr}.png',
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.BOTTOM_RIGHT,
            duration=5000,
            parent=None # Fixme: parent应该绑在什么上面
        )

