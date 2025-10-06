import asyncio
import random
from functools import partial
from time import sleep, time
from pywintypes import error as PyWinTypesError

import pyautogui
import win32api
import win32con
import win32gui

from module.config import cfg
from utils.singletonmeta import SingletonMeta
from ..game_and_screen import screen
from ..logger import log

key_list = {
    'a': 0x41, 'b': 0x42, 'c': 0x43, 'd': 0x44, 'e': 0x45,
    'f': 0x46, 'g': 0x47, 'h': 0x48, 'i': 0x49, 'j': 0x4A,
    'k': 0x4B, 'l': 0x4C, 'm': 0x4D, 'n': 0x4E, 'o': 0x4F,
    'p': 0x50, 'q': 0x51, 'r': 0x52, 's': 0x53, 't': 0x54,
    'u': 0x55, 'v': 0x56, 'w': 0x57, 'x': 0x58, 'y': 0x59,
    'z': 0x5A,
    '0': 0x30, '1': 0x31, '2': 0x32, '3': 0x33, '4': 0x34,
    '5': 0x35, '6': 0x36, '7': 0x37, '8': 0x38, '9': 0x39,
    'enter': win32con.VK_RETURN,
    'esc': win32con.VK_ESCAPE,
    'space': win32con.VK_SPACE,
    'tab': win32con.VK_TAB,
    'shift': win32con.VK_SHIFT,
    'ctrl': win32con.VK_CONTROL,
    'alt': win32con.VK_MENU,
}


class Input(metaclass=SingletonMeta):
    """基于 `pyautogui` 的输入类, 仅支持前台操作"""
    # 禁用pyautogui的失败安全特性，防止意外中断
    pyautogui.FAILSAFE = False

    def __init__(self):
        self.is_pause = False
        self.restore_time = None
        # self.is_move_back = False  以后从配置里读取

    def set_pause(self) -> None:
        """
        设置暂停状态
        """
        self.is_pause = not self.is_pause  # 设置暂停状态
        if self.is_pause:
            msg = "操作将在下一次点击时暂停"
        else:
            msg = "继续操作"
        log.info(msg)

    def wait_pause(self) -> None:
        """
        当处于暂停状态时堵塞的进行等待
        """
        pause_identity = False
        while self.is_pause:
            if not pause_identity is False:
                log.info("AALC 已暂停")
                pause_identity = True
            sleep(1)
            self.restore_time = time()

    def mouse_click(self, x, y, times=1, move_back=False) -> bool:
        """在指定坐标上执行点击操作

        Args:
            x (int): x坐标
            y (int): y坐标
            times (int): 点击次数
            move_back (bool): 是否在点击后将鼠标移动回原位置
        Returns:
            bool (True) : 总是返回True表示操作执行完毕
        """
        if move_back:
            current_mouse_position = self.get_mouse_position()

        msg = f"点击位置:({x},{y})"
        log.debug(msg, stacklevel=2)
        for i in range(times):
            pyautogui.click(x, y)
            # 多次点击执行很快所以暂停放到循环外

        if move_back and current_mouse_position:
            self.mouse_move(current_mouse_position)

        self.wait_pause()

        return True

    def mouse_drag_down(self, x, y, move_back=True) -> None:
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
        log.debug(msg, stacklevel=2)

    def mouse_drag(self, x, y, drag_time=0.1, dx=0, dy=0, move_back=True) -> None:
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
        if drag_time * 0.3 > 0.5:
            sleep(drag_time * 0.3)
        else:
            sleep(0.5)
        pyautogui.mouseUp()

        if move_back and current_mouse_position:
            self.mouse_move(current_mouse_position)

    def mouse_scroll(self, direction: int = -3) -> bool:
        """
        进行鼠标滚动操作
        Args:
            direction (int): 滚动方向，正值表示拉近，负值表示缩小
        Returns:
            bool (True) : 表示是否支持该操作
        """
        if direction <= 0:
            msg = "鼠标滚动滚轮，远离界面"
        else:
            msg = "鼠标滚动滚轮，拉近界面"
        log.debug(msg, stacklevel=2)
        pyautogui.scroll(direction)
        return True

    def mouse_click_blank(self, coordinate=(1, 1), times=1, move_back=False) -> bool:
        """在空白位置点击鼠标
        Args:
            coordinate (tuple): 坐标元组 (x, y)
            times (int): 点击次数
            move_back (bool): 是否在点击后将鼠标移动回原位置
        Returns:
            bool (True) : 总是返回True表示操作执行完毕
        """
        if move_back:
            current_mouse_position = self.get_mouse_position()

        msg = "点击（1，1）空白位置"
        log.debug(msg, stacklevel=2)
        x = coordinate[0] + random.randint(0, 10)
        y = coordinate[1] + random.randint(0, 10)
        for i in range(times):
            pyautogui.click(x, y)

        if move_back and current_mouse_position:
            self.mouse_move(current_mouse_position)

        self.wait_pause()
        return True

    def mouse_to_blank(self, coordinate=(1, 1), move_back=False) -> None:
        """鼠标移动到空白位置，避免遮挡
        Args:
            coordinate (tuple): 坐标元组 (x, y)
            move_back (bool): 是否在移动后将鼠标移动回原位置
        """
        if move_back:
            current_mouse_position = self.get_mouse_position()

        msg = "鼠标移动到空白，避免遮挡"
        log.debug(msg, stacklevel=2)
        pyautogui.moveTo(coordinate[0], coordinate[1])

        if move_back and current_mouse_position:
            self.mouse_move(current_mouse_position)
        self.wait_pause()

    def mouse_move(self, coordinate=(1, 1)) -> None:
        """鼠标移动到指定坐标

        Args:
            coordinate (tuple): 坐标元组 (x, y)
        """
        pyautogui.moveTo(coordinate[0], coordinate[1])
        self.wait_pause()

    def get_mouse_position(self) -> tuple[int, int]:
        """获取鼠标当前位置

        Returns:
            tuple: 当前鼠标位置的元组 (x, y)
        """
        return pyautogui.position()

    def mouse_drag_link(self, position: list, drag_time=0.1) -> None:
        """鼠标从指定位置拖动到指定位置
        Args:
            x (int): 起始x坐标
            y (int): 起始y坐标
            position (list): 目标位置列表
            drag_time (float): 拖动时间
        """
        pyautogui.moveTo(position[0][0], position[0][1])
        pyautogui.mouseDown()
        for pos in position:
            pyautogui.moveTo(pos[0], pos[1], duration=drag_time)
        pyautogui.mouseUp()

    def key_press(self, key):
        return pyautogui.press(key)


class BackgroundInput(Input, metaclass=SingletonMeta):
    """基于 `pywin32` 的输入类, 支持后台操作
    \n 除了不支持滚轮事件, 其余同 `Input` 类
    """

    def mouse_to_blank(self, coordinate=(1, 1), move_back=True) -> None:
        """鼠标移动到空白位置，避免遮挡（然而为了避免影响用户操作，这个暂时没用）
        Args:
            coordinate (tuple): 坐标元组 (x, y)
            move_back (bool): 是否在移动后将鼠标移动回原位置
        """
        # FIXME：既不能影响用户操作，也要避免遮挡，似乎没有好办法
        # FIXME：目前是不在游戏窗口内不移动鼠标, 但是我觉得应该把这个功能集成在截图里 - 233 25.10.4
        if move_back:
            current_mouse_position = self.get_mouse_position()
            rect = win32gui.GetWindowRect(screen.handle._hWnd)
            if (
                current_mouse_position[0] > rect[0] + rect[2]
                or current_mouse_position[1] > rect[1] + rect[3]
            ):
                # 在窗口右下角外
                log.debug("当前鼠标位置不在游戏窗口内，取消移动到空白", stacklevel=2)
                return
            elif (
                current_mouse_position[0] < rect[0]
                or current_mouse_position[1] < rect[1]
            ):
                # 在窗口左上角外
                log.debug("当前鼠标位置不在游戏窗口内，取消移动到空白", stacklevel=2)
                return
        self._mouse_move_to(coordinate[0], coordinate[1])

        log.debug("鼠标移动到空白，避免遮挡", stacklevel=2)

        self.wait_pause()

    def mouse_click(self, x, y, times=1, move_back=True) -> bool:
        """在指定坐标上执行点击操作

        Args:
            x (int): x坐标
            y (int): y坐标
            times (int): 点击次数
            move_back (bool): 是否在点击后将鼠标移动回原位置
        Returns:
            bool (True) : 总是返回True表示操作执行完毕
        """
        if move_back:
            current_mouse_position = self.get_mouse_position()

        msg = f"点击位置:({x},{y})"
        log.debug(msg, stacklevel=2)
        for i in range(times):
            self.set_mouse_pos(x, y)
            self.set_focus()
            self.mouse_down(x, y)
            self.mouse_up(x, y)
            # 多次点击执行很快所以暂停放到循环外

        if move_back and current_mouse_position:
            self.mouse_move(current_mouse_position)

        self.wait_pause()

        return True

    def mouse_drag_down(self, x, y, move_back=True) -> None:
        """鼠标从指定位置向下拖动

        Args:
            x (int): x坐标
            y (int): y坐标
            move_back (bool): 是否在拖动后将鼠标移动回原位置
        """
        if move_back:
            current_mouse_position = self.get_mouse_position()

        scale = cfg.set_win_size / 1080
        self.set_focus()
        self._mouse_move_to(x, y)
        self.mouse_down(x, y)
        self._mouse_move_to(x, y + int(300 * scale), duration=0.4)
        self.mouse_up(x, y)

        if move_back and current_mouse_position:
            self.mouse_move(current_mouse_position)

        msg = f"选择卡包:({x},{y})"
        log.debug(msg, stacklevel=2)

    def mouse_drag(self, x, y, drag_time=0.1, dx=0, dy=0, move_back=True) -> None:
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
        self._mouse_move_to(x, y)
        self.set_focus()
        self.mouse_down(x, y)
        self._mouse_move_to(x + dx, y + dy, duration=drag_time)
        if drag_time * 0.3 > 0.5:
            sleep(drag_time * 0.3)
        else:
            sleep(0.5)
        self.mouse_up(x, y)

        if move_back and current_mouse_position:
            self.mouse_move(current_mouse_position)

    def mouse_scroll(self, direction: int = -3) -> bool:
        """
        不支持的方法\n
        进行鼠标滚动操作
        Args:
            direction (int): 滚动方向，正值表示拉近，负值表示缩小
        Returns:
            bool (False) : 表示是否支持该操作
        """
        # 不支持的方法
        return False

    def mouse_click_blank(self, coordinate=(1, 1), times=1, move_back=True) -> bool:
        """在空白位置点击鼠标
        Args:
            coordinate (tuple): 坐标元组 (x, y)
            times (int): 点击次数
            move_back (bool): 是否在点击后将鼠标移动回原位置
        Returns:
            bool (True) : 总是返回True表示操作执行完毕
        """
        if move_back:
            current_mouse_position = self.get_mouse_position()

        msg = "点击（1，1）空白位置"
        log.debug(msg, stacklevel=2)
        x = coordinate[0] + random.randint(0, 10)
        y = coordinate[1] + random.randint(0, 10)
        for i in range(times):
            self.set_mouse_pos(x, y)
            self.set_focus()
            self.mouse_down(x, y)
            self.mouse_up(x, y)

        if move_back and current_mouse_position:
            self.mouse_move(current_mouse_position)

        self.wait_pause()
        return True

    def mouse_drag_link(self, position: list, drag_time=0.1) -> None:
        """鼠标从指定位置拖动到指定位置
        Args:
            x (int): 起始x坐标
            y (int): 起始y坐标
            position (list): 目标位置列表
            drag_time (float): 拖动时间
        """
        self._mouse_move_to(position[0][0], position[0][1])
        self.set_focus()
        self.mouse_down(position[0][0], position[0][1])
        for pos in position:
            self._mouse_move_to(pos[0], pos[1], duration=drag_time)
        self.mouse_up(position[-1][-1], position[-1][-1])

    def set_focus(self):
        """将游戏窗口设置为输入焦点以让 Unity 接受输入事件
        """
        hwnd = screen.handle._hWnd
        if hwnd:
            # 如果最小化则显示
            placement = win32gui.GetWindowPlacement(hwnd)
            if placement[1] == win32con.SW_SHOWMINIMIZED:
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                sleep(0.5)

            # 设置窗口的输入状态
            win32gui.EnableWindow(hwnd, True)

            # 发送激活消息（但不改变Z序）
            win32gui.SendMessage(hwnd, win32con.WM_ACTIVATE, win32con.WA_ACTIVE, 0)

            # 设置焦点状态
            win32gui.SendMessage(hwnd, win32con.WM_SETFOCUS, 0, 0)
        else:
            log.error("未初始化hwnd")

    def mouse_down(self, x, y):
        """鼠标左键按下
        Args:
            x (number): 相对于窗口左上角的 x 轴坐标
            y (number): 相对于窗口左上角的 y 轴坐标
        """
        x = int(x)
        y = int(y)
        hwnd = screen.handle._hWnd
        long_positon = win32api.MAKELONG(x, y)
        win32api.SendMessage(hwnd, win32con.WM_LBUTTONDOWN, 0, long_positon)
        sleep(0.01)

    def mouse_up(self, x, y):
        """鼠标左键抬起
        Args:
            x (number): 相对于窗口左上角的 x 轴坐标
            y (number): 相对于窗口左上角的 y 轴坐标
        """
        x = int(x)
        y = int(y)
        hwnd = screen.handle._hWnd
        long_positon = win32api.MAKELONG(x, y)
        win32api.SendMessage(hwnd, win32con.WM_LBUTTONUP, 0, long_positon)
        sleep(0.01)

    def set_mouse_pos(self, x, y):
        """移动光标位置
        Args:
            x (number): 相对于窗口左上角的 x 轴坐标
            y (number): 相对于窗口左上角的 y 轴坐标
        """
        x = int(x)
        y = int(y)
        hwnd = screen.handle._hWnd
        rect = win32gui.GetWindowRect(hwnd)
        self._mouse_move_to(rect[0] + x, rect[1] + y)

    def key_down(self, key: str):
        """键盘按键按下
        Args:
            key (str): 按键名称
        """
        hwnd = screen.handle._hWnd
        lparam = 0x00000001  # 重复次数为1
        win32api.SendMessage(hwnd, win32con.WM_KEYDOWN, key_list[key.lower()], lparam)

    def key_up(self, key: str):
        """键盘按键抬起
        Args:
            key (str): 按键名称
        """
        hwnd = screen.handle._hWnd
        lparam = 0xC0000001  # 转换状态为1（按键释放）
        win32api.SendMessage(hwnd, win32con.WM_KEYUP, key_list[key.lower()], lparam)

    def key_press(self, key):
        """一次键盘按键操作
        Args:
            key (str): 按键名称
        """
        self.set_focus()
        self.key_down(key)
        self.key_up(key)

    def mouse_move(self, coordinate=(1, 1)) -> None:
        """鼠标移动到指定坐标

        Args:
            coordinate (tuple): 坐标元组 (x, y)
        """
        self._mouse_move_to(coordinate[0], coordinate[1])
        self.wait_pause()

    def _mouse_move_to(self, x, y, duration: float = 0):
        """将鼠标移动到指定位置（绝对于屏幕坐标）

        Args:
            x (int): x坐标
            y (int): y坐标
        """
        x = int(x)
        y = int(y)
        if duration <= 0:
            self._set_mouse_pos(x, y)
        else:
            start_x, start_y = self.get_mouse_position()
            steps = int(duration / 0.01)
            for i in range(steps):
                new_x = int(start_x + (x - start_x) * (i + 1) / steps)
                new_y = int(start_y + (y - start_y) * (i + 1) / steps)
                self._set_mouse_pos(new_x, new_y)
                sleep(0.01)

    def _set_mouse_pos(self, x: int, y: int):
        """将鼠标移动到指定位置（绝对于屏幕坐标）

        Args:
            x (int): x坐标
            y (int): y坐标
        """
        try:
            win32api.SetCursorPos((x, y))
        except PyWinTypesError as e:
            # 奇怪的权限冲突 (183:当文件已存在时，无法创建该文件。)
            # 偶尔出现不影响使用

            log.debug(f"鼠标移动失败: {e}")
            try:
                pyautogui.moveTo(x, y)
            except Exception as e:
                log.error(f"鼠标移动失败: {type(e)}: {e}")