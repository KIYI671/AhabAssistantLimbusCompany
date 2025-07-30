import random
from time import sleep

import pyautogui

from module.config import cfg
from utils.singletonmeta import SingletonMeta


class Input(metaclass=SingletonMeta):
    # 禁用pyautogui的失败安全特性，防止意外中断
    pyautogui.FAILSAFE = False

    def __init__(self, logger):
        self.is_pause = False
        self.logger = logger
        # self.is_move_back = False  以后从配置里读取

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

    def mouse_click(self, x, y, times=1, move_back=False):
        """在指定坐标上执行点击操作

        Args:
            x (int): x坐标
            y (int): y坐标
            times (int): 点击次数
            move_back (bool): 是否在点击后将鼠标移动回原位置
        """
        if move_back:
            current_mouse_position = self.get_mouse_position()

        msg = f"点击位置:({x},{y})"
        self.logger.DEBUG(msg)
        for i in range(times):
            pyautogui.click(x, y)
            # 多次点击执行很快所以暂停放到循环外

        if move_back and current_mouse_position:
            self.mouse_move(current_mouse_position)

        self.wait_pause()

        return True

    def mouse_drag_down(self, x, y, move_back=True):
        """鼠标从指定位置向下拖动

        Args:
            x (int): x坐标
            y (int): y坐标
            move_back (bool): 是否在拖动后将鼠标移动回原位置
        """
        if move_back:
            current_mouse_position = self.get_mouse_position()

        scale = cfg.set_win_size / 1080
        pyautogui.moveTo(x, y)
        pyautogui.mouseDown()
        pyautogui.dragTo(x, y + int(300 * scale), duration=0.4)
        pyautogui.mouseUp()

        if move_back and current_mouse_position:
            self.mouse_move(current_mouse_position)

        msg = f"选择卡包:({x},{y})"
        self.logger.DEBUG(msg)

    def mouse_drag(self, x, y, drag_time=0.1, dx=0, dy=0, move_back=False):
        """鼠标从指定位置拖动到另一个位置
        Args:
            x (int): 起始x坐标
            y (int): 起始y坐标
            drag_time (float): 拖动时间
            dx (int): x方向拖动距离
            dy (int): y方向拖动距离
            move_back (bool): 是否在拖动后将鼠标移动回原位置
        """
        if move_back:
            current_mouse_position = self.get_mouse_position()

        pyautogui.moveTo(x, y)
        pyautogui.mouseDown()
        pyautogui.moveTo(x + dx, y + dy, duration=drag_time)
        if drag_time*0.3>0.5:
            sleep(drag_time*0.3)
        else:
            sleep(0.5)
        pyautogui.mouseUp()

        if move_back and current_mouse_position:
            self.mouse_move(current_mouse_position)

    def mouse_scroll(self, direction=-3):
        if direction <= 0:
            msg = "鼠标滚动滚轮，远离界面"
        else:
            msg = "鼠标滚动滚轮，拉近界面"
        self.logger.DEBUG(msg)
        pyautogui.scroll(direction)

    def mouse_click_blank(self, coordinate=(1, 1), times=1, move_back=False):
        """在空白位置点击鼠标
        Args:
            coordinate (tuple): 坐标元组 (x, y)
            times (int): 点击次数
            move_back (bool): 是否在点击后将鼠标移动回原位置
        """
        if move_back:
            current_mouse_position = self.get_mouse_position()

        msg = "点击（1，1）空白位置"
        self.logger.DEBUG(msg)
        x = coordinate[0] + random.randint(0, 10)
        y = coordinate[1] + random.randint(0, 10)
        for i in range(times):
            pyautogui.click(x, y)
        
        if move_back and current_mouse_position:
            self.mouse_move(current_mouse_position)

        self.wait_pause()
        return True

    def mouse_to_blank(self, coordinate=(1, 1), move_back=False):
        """鼠标移动到空白位置，避免遮挡
        Args:
            coordinate (tuple): 坐标元组 (x, y)
            move_back (bool): 是否在移动后将鼠标移动回原位置
        """
        if move_back:
            current_mouse_position = self.get_mouse_position()

        msg = "鼠标移动到空白，避免遮挡"
        self.logger.DEBUG(msg)
        pyautogui.moveTo(coordinate[0], coordinate[1])

        if move_back and current_mouse_position:
            self.mouse_move(current_mouse_position)
        self.wait_pause()

    def mouse_move(self, coordinate=(1, 1)):
        """鼠标移动到指定坐标

        Args:
            coordinate (tuple): 坐标元组 (x, y)
        """
        pyautogui.moveTo(coordinate[0], coordinate[1])
        self.wait_pause()

    def get_mouse_position(self):
        """获取鼠标当前位置

        Returns:
            tuple: 当前鼠标位置的元组 (x, y)
        """
        x, y = pyautogui.position()
        return (x, y)

    def mouse_drag_link(self,position:list, drag_time=0.1):
        """鼠标从指定位置拖动到指定位置
        Args:
            x (int): 起始x坐标
            y (int): 起始y坐标
            position (list): 目标位置列表
            drag_time (float): 拖动时间
        """
        pyautogui.moveTo(position[0][0],position[0][1])
        pyautogui.mouseDown()
        for pos in position:
            pyautogui.moveTo(pos[0], pos[1], duration=drag_time)
        pyautogui.mouseUp()