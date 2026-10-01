"""Linux 前台输入，复用上游的交互门和列表滚动手势。"""

import os
import random
import time
from typing import overload

import pyperclip

from module.config import cfg
from module.logger import log
from module.platform_compat import is_wayland_session
from utils.singletonmeta import SingletonMeta

from ...game_and_screen import screen
from . import AbstractInput
from .scroll_swipe import build_windows_scroll_swipe_plan

if os.environ.get("DISPLAY"):
    import pyautogui

    pyautogui.FAILSAFE = False
else:
    pyautogui = None


class LinuxInput(AbstractInput, metaclass=SingletonMeta):
    """Linux 仅支持前台操作。backend 提供鼠标、键盘的同一坐标空间。"""

    @property
    def backend(self):
        if pyautogui is None:
            raise RuntimeError("Linux 前台输入需要 X11 会话和 DISPLAY")
        return pyautogui

    def prepare(self) -> None:
        if is_wayland_session():
            raise RuntimeError("此版本仅支持 X11 前台输入，请登录 X11 会话后再启动任务")
        self.backend

    @staticmethod
    def _window_is_ready() -> bool:
        """窗口重建或冷启动期间不允许向桌面注入输入。"""
        try:
            left, top, right, bottom = screen.handle.rect(True)
        except Exception as error:
            log.debug(f"读取 Linux 游戏窗口区域失败，跳过输入: {error}")
            return False
        return right > left and bottom > top

    @overload
    def pos_offset(self, x: int, y: int) -> tuple[int, int]: ...
    @overload
    def pos_offset(self, pos: tuple[int, int]) -> tuple[int, int]: ...

    def pos_offset(self, *args) -> tuple[int, int]:
        if len(args) == 2:
            x, y = args
        elif len(args) == 1 and isinstance(args[0], tuple):
            x, y = args[0]
        else:
            raise ValueError("pos_offset 接受两个整数参数或一个包含两个整数的元组")
        real_x, real_y, _, _ = screen.handle.rect(True)
        return x + real_x, y + real_y

    def get_mouse_position(self) -> tuple[int, int]:
        try:
            x, y = self.backend.position()
            return int(x), int(y)
        except Exception:
            log.debug("获取鼠标位置失败，返回 (0, 0)")
            return (0, 0)

    def mouse_click(self, x, y, times=1, move_back=False) -> bool:
        if not self._window_is_ready():
            return False
        previous = self.get_mouse_position() if move_back else None
        log.debug(f"点击位置:({x},{y})", stacklevel=2)
        x, y = self.pos_offset(x, y)
        for _ in range(times):
            self.backend.click(x, y)
        if previous is not None:
            self.mouse_move(previous)
        self.wait_pause()
        return True

    def _drag_path(self, plan, settle_duration=0, move_back=True) -> None:
        """移到起点后再按下；途中失败也释放已按下的按钮。"""
        if not self._window_is_ready() or not plan:
            return
        previous = self.get_mouse_position() if move_back else None
        backend = self.backend
        backend.moveTo(*plan[0][0])
        try:
            backend.mouseDown()
            for point, duration in plan[1:]:
                backend.moveTo(*point, duration=duration)
            if settle_duration:
                time.sleep(settle_duration)
        finally:
            backend.mouseUp()
        if previous is not None:
            self.mouse_move(previous)

    def mouse_drag_down(self, x, y, reverse=1, move_back=True) -> None:
        distance = int(300 * cfg.set_win_size / 1080 * reverse)
        self._drag_path(
            [(self.pos_offset(x, y), 0), (self.pos_offset(x, y + distance), 0.4)],
            move_back=move_back,
        )

    def mouse_drag(self, x, y, drag_time=0.1, dx=0, dy=0, move_back=True) -> None:
        self._drag_path(
            [(self.pos_offset(x, y), 0), (self.pos_offset(x + dx, y + dy), drag_time)],
            settle_duration=max(0.5, drag_time * 0.3),
            move_back=move_back,
        )

    def mouse_swipe_for_scroll(self, x, y, duration=0.3, dx=0, dy=0, move_back=True) -> None:
        raw_plan, settle_duration = build_windows_scroll_swipe_plan(x, y, dx, dy, duration)
        plan = [(self.pos_offset(*point), move_duration) for point, move_duration in raw_plan]
        self._drag_path(plan, settle_duration=settle_duration, move_back=move_back)

    def mouse_scroll(self, direction: int = -3) -> bool:
        if not self._window_is_ready():
            return False
        self.backend.scroll(direction)
        return True

    def mouse_click_blank(self, coordinate=(1, 1), times=1, move_back=False) -> bool:
        x = coordinate[0] + random.randint(0, 10)
        y = coordinate[1] + random.randint(0, 10)
        return self.mouse_click(x, y, times=times, move_back=move_back)

    def mouse_to_blank(self, coordinate=(1, 1), move_back=False) -> None:
        if not self._window_is_ready():
            return
        previous = self.get_mouse_position() if move_back else None
        self.mouse_move(self.pos_offset(*coordinate))
        if previous is not None:
            self.mouse_move(previous)

    def mouse_move(self, coordinate=(1, 1)) -> None:
        """移动到屏幕绝对坐标。"""
        self.backend.moveTo(int(coordinate[0]), int(coordinate[1]))
        self.wait_pause()

    def mouse_drag_link(self, position: list, drag_time=0.1, move_back=False) -> None:
        self._drag_path([(self.pos_offset(*pos), drag_time) for pos in position], move_back=move_back)

    def key_press(self, key):
        if self._window_is_ready():
            self.backend.press(key)

    def input_text(self, text: str):
        if not text:
            log.warning("未提供要粘贴的文本")
            return
        if not self._window_is_ready():
            return
        try:
            pyperclip.copy(text)
        except Exception:
            self.backend.typewrite(text)
            return
        self.backend.hotkey("ctrl", "v")
