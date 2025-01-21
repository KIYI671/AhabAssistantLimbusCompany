import random
from time import sleep

import pyautogui

from module.config import cfg
from utils.singletonmeta import SingletonMeta


class Input(metaclass=SingletonMeta):
    # 禁用pyautogui的失败安全特性，防止意外中断
    pyautogui.FAILSAFE = False

    def __init__(self,logger):
        self.is_pause = False
        self.logger = logger

    def set_pause(self):
        self.is_pause = not self.is_pause  # 设置暂停状态
        if self.is_pause:
            msg = "操作将在下一次点击时暂停"
        else:
            msg = "继续操作"
        self.logger.INFO(msg)

    def wait_pause(self):
        while self.is_pause:
            sleep(1)

    def mouse_click(self, x,y, times=1):
        msg = f"点击位置:({x},{y})"
        self.logger.DEBUG(msg)
        for i in range(times):
            pyautogui.click(x, y)
            self.wait_pause()
        return True

    def mouse_drag_down(self, x,y):
        scale = cfg.set_win_size/1080
        pyautogui.moveTo(x,y)
        pyautogui.mouseDown()
        pyautogui.dragTo(x,y + int(300 * scale), duration=0.4)
        pyautogui.mouseUp()
        msg = f"选择卡包:({x},{y})"
        self.logger.DEBUG(msg)

    def mouse_drag(self, x,y, drag_time=0.1, dx=0, dy=0):
        pyautogui.moveTo(x, y)
        pyautogui.mouseDown()
        pyautogui.dragTo(x + dx, y + dy, duration=drag_time)
        pyautogui.mouseUp()

    def mouse_scroll(self, direction=-3):
        if direction<=0:
            msg = "鼠标滚动滚轮，远离界面"
        else:
            msg = "鼠标滚动滚轮，拉近界面"
        self.logger.DEBUG(msg)
        pyautogui.scroll(direction)

    def mouse_click_blank(self, coordinate=(1, 1), times=1):
        msg = "点击（1，1）空白位置"
        self.logger.DEBUG(msg)
        x = coordinate[0] + random.randint(0, 10)
        y = coordinate[1] + random.randint(0, 10)
        for i in range(times):
            pyautogui.click(x, y)
            self.wait_pause()
        return True

    def mouse_to_blank(self, coordinate=(1, 1)):
        msg = "鼠标移动到空白，避免遮挡"
        self.logger.DEBUG(msg)
        pyautogui.moveTo(coordinate[0], coordinate[1])
        self.wait_pause()