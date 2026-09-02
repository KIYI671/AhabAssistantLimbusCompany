"""基于 pyautogui (X11/XWayland) 的前台输入实现，接口与 Windows 版 `Input` 一致。

Linux 的 X11 协议没有 Win32 PostMessage 后台消息通道的可靠等价物
（XSendEvent 会被 Unity/Proton 游戏忽略），因此 Linux 下统一使用前台输入。
"""

import random
import time
from typing import overload

import pyautogui
import pyperclip

from module.config import cfg
from utils.singletonmeta import SingletonMeta

from ...game_and_screen import screen
from ...logger import log
from . import AbstractInput
from .scroll_swipe import build_windows_scroll_swipe_plan

pyautogui.FAILSAFE = False


class LinuxInput(AbstractInput, metaclass=SingletonMeta):
    """基于 `pyautogui` 的输入类, 仅支持前台操作"""

    @overload
    def pos_offset(self, x: int, y: int) -> tuple[int, int]: ...
    @overload
    def pos_offset(self, pos: tuple[int, int]) -> tuple[int, int]: ...

    def pos_offset(self, *args) -> tuple[int, int]:  # type: ignore
        """根据当前窗口位置偏移点击位置"""
        if len(args) == 2:
            x, y = args
        elif isinstance(args[0], tuple):
            x, y = args[0]
        else:
            raise ValueError("pos_offset 接受两个整数参数或一个包含两个整数的元组")
        real_x, real_y, _, _ = screen.handle.rect(True)
        return x + real_x, y + real_y

    def get_mouse_position(self) -> tuple[int, int]:
        """获取鼠标当前位置（X11 异常时返回 (0, 0)）"""
        try:
            pos = pyautogui.position()
            return int(pos.x), int(pos.y)
        except Exception:
            log.debug("获取鼠标位置失败，返回 (0, 0)")
            return (0, 0)

    def mouse_click(self, x, y, times=1, move_back=False) -> bool:
        if move_back:
            current_mouse_position = self.get_mouse_position()

        msg = f"点击位置:({x},{y})"
        log.debug(msg, stacklevel=2)
        x, y = self.pos_offset(x, y)
        for i in range(times):
            pyautogui.click(x, y)
            # 多次点击执行很快所以暂停放到循环外

        if move_back and current_mouse_position:
            self.mouse_move(current_mouse_position)

        self.wait_pause()

        return True

    def mouse_drag_down(self, x, y, reverse=1, move_back=True) -> None:
        if move_back:
            current_mouse_position = self.get_mouse_position()

        scale = cfg.set_win_size / 1080
        x, y = self.pos_offset(x, y)
        pyautogui.moveTo(x, y)
        pyautogui.mouseDown()
        pyautogui.dragTo(x, y + int(300 * scale * reverse), duration=0.4)
        pyautogui.mouseUp()

        if move_back and current_mouse_position:
            self.mouse_move(current_mouse_position)

    def mouse_drag(self, x, y, drag_time=0.1, dx=0, dy=0, move_back=True) -> None:
        if move_back:
            current_mouse_position = self.get_mouse_position()
        x, y = self.pos_offset(x, y)
        pyautogui.moveTo(x, y)
        pyautogui.mouseDown()
        pyautogui.moveTo(x + dx, y + dy, duration=drag_time)
        if drag_time * 0.3 > 0.5:
            time.sleep(drag_time * 0.3)
        else:
            time.sleep(0.5)
        pyautogui.mouseUp()

        if move_back and current_mouse_position:
            self.mouse_move(current_mouse_position)

    def mouse_swipe_for_scroll(self, x, y, duration=0.3, dx=0, dy=0, move_back=True) -> None:
        if move_back:
            current_mouse_position = self.get_mouse_position()

        raw_plan, settle_duration = build_windows_scroll_swipe_plan(
            x, y, dx, dy, duration
        )
        plan = [
            (self.pos_offset(*point), move_duration)
            for point, move_duration in raw_plan
        ]
        pyautogui.moveTo(*plan[0][0])
        pyautogui.mouseDown()
        for point, move_duration in plan[1:]:
            pyautogui.moveTo(*point, duration=move_duration)
        if settle_duration:
            time.sleep(settle_duration)
        pyautogui.mouseUp()

        if move_back and current_mouse_position:
            self.mouse_move(current_mouse_position)

    def mouse_scroll(self, direction: int = -3) -> bool:
        if direction <= 0:
            msg = "鼠标滚动滚轮，远离界面"
        else:
            msg = "鼠标滚动滚轮，拉近界面"
        log.debug(msg, stacklevel=2)
        pyautogui.scroll(direction)
        return True

    def mouse_click_blank(self, coordinate=(1, 1), times=1, move_back=False) -> bool:
        if move_back:
            current_mouse_position = self.get_mouse_position()

        msg = "点击（1，1）空白位置"
        log.debug(msg, stacklevel=2)
        x = coordinate[0] + random.randint(0, 10)
        y = coordinate[1] + random.randint(0, 10)
        x, y = self.pos_offset(x, y)
        for i in range(times):
            pyautogui.click(x, y)

        if move_back and current_mouse_position:
            self.mouse_move(current_mouse_position)

        self.wait_pause()
        return True

    def mouse_to_blank(self, coordinate=(1, 1), move_back=False) -> None:
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

    def mouse_drag_link(self, position: list, drag_time=0.1, move_back=False) -> None:
        if move_back:
            current_mouse_position = self.get_mouse_position()

        x, y = self.pos_offset(position[0][0], position[0][1])
        pyautogui.moveTo(x, y)
        pyautogui.mouseDown()
        for pos in position:
            x, y = self.pos_offset(pos[0], pos[1])
            pyautogui.moveTo(x, y, duration=drag_time)
        pyautogui.mouseUp()

        if move_back and current_mouse_position:
            self.mouse_move(current_mouse_position)

    def key_press(self, key):
        return pyautogui.press(key)

    def input_text(self, text: str):
        """将 `text` 粘贴到前台窗口。仅用于前台操作，内部使用 `pyperclip.copy` + Ctrl+V，
        在 `pyperclip.copy` 失败时回退到直接打字。"""
        if not text:
            log.warning("未提供要粘贴的文本")
            return
        try:
            pyperclip.copy(text)
        except Exception:
            try:
                pyautogui.typewrite(text)
                return
            except Exception:
                log.error("pyautogui 直接输入失败")
                return
        pyautogui.hotkey("ctrl", "v")
