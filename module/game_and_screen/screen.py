from ctypes import windll
from time import sleep
from typing import TYPE_CHECKING, overload

import win32api
import win32con
import win32gui

from app import mediator
from module.config import cfg
from module.logger import log
from utils.singletonmeta import SingletonMeta

if TYPE_CHECKING:
    from .game import Game


class Handle:
    """提供统一的获取窗口信息的接口"""

    _hwnd: int = 0

    def init_handle(self, title: str, class_name: str = "UnityWndClass") -> int:
        """获取窗口句柄"""
        self._hwnd = win32gui.FindWindow(class_name, title)
        return self._hwnd

    @property
    def hwnd(self) -> int:
        """获取窗口句柄"""
        if self._hwnd == 0:
            log.warning("窗口未初始化", stacklevel=3)
        return self._hwnd

    @property
    def isMinimized(self) -> bool:
        """判断窗口是否最小化"""
        if self.hwnd == 0:
            return False
        return bool(win32gui.IsIconic(self.hwnd))

    @property
    def isActive(self) -> bool:
        """判断窗口是否为活动窗口"""
        if self.hwnd == 0:
            return False
        return self.hwnd == win32gui.GetForegroundWindow()

    def rect(self, client: bool = False) -> tuple[int, int, int, int]:
        """获取窗口位置和大小

        Parameters
        ---
        client: bool
            是否获取客户区大小，默认为`False`
        """
        if self.hwnd == 0:
            return (0, 0, 0, 0)
        if client:
            _, _, width, height = win32gui.GetClientRect(self.hwnd)
            x, y = win32gui.ClientToScreen(self.hwnd, (0, 0))
            return (x, y, x + width, y + height)
        return win32gui.GetWindowRect(self.hwnd)

    def width(self, client: bool = False) -> int:
        """获取窗口宽度

        Parameters
        ---
        client: bool
            是否获取客户区大小，默认为`False`
        """
        if self.hwnd == 0:
            return 0
        rect = self.rect(client)
        return rect[2] - rect[0]

    def height(self, client: bool = False) -> int:
        """获取窗口高度

        Parameters
        ---
        client: bool
            是否获取客户区大小，默认为`False`
        """
        if self.hwnd == 0:
            return 0
        rect = self.rect(client)
        return rect[3] - rect[1]

    @property
    def monitor_info(self) -> dict:
        """获取窗口所在显示器的信息"""
        if self.hwnd == 0:
            return {
                "Monitor": (0, 0, 0, 0),
                "Work": (0, 0, 0, 0),
                "Flags": 0,
                "Device": "Unknown",
            }
        monitor_info = win32api.GetMonitorInfo(
            win32api.MonitorFromWindow(self.hwnd, win32con.MONITOR_DEFAULTTONEAREST)
        )
        return monitor_info

    def monitor_size(self, get_work: bool = False) -> tuple[int, int]:
        """获取窗口所在显示器的分辨率

        Parameters
        ---
        get_work: bool
            是否获取工作区分辨率，默认为`False`
        """
        info = self.monitor_info
        if get_work:
            rect = info["Work"]
        else:
            rect = info["Monitor"]
        width = rect[2] - rect[0]
        height = rect[3] - rect[1]
        return width, height

    def setForeground(self) -> None:
        """将窗口设为前台窗口"""
        if self.hwnd == 0:
            return
        win32gui.SetForegroundWindow(self.hwnd)

    def setMaximized(self, value: bool = True) -> None:
        """最大化窗口"""
        if self.hwnd == 0:
            return
        if value:
            win32gui.ShowWindow(self.hwnd, win32con.SW_MAXIMIZE)
        else:
            win32gui.ShowWindow(self.hwnd, win32con.SW_RESTORE)

    def switchFullScreenMode(self) -> bool:
        """切换全屏模式 (发送Alt+Enter)"""
        if self.hwnd == 0:
            return False
        hwnd = self.hwnd

        if self.isMinimized:
            self.restore()
            sleep(0.5)
        # 模拟按下
        win32api.PostMessage(
            hwnd, win32con.WM_SYSKEYDOWN, win32con.VK_RETURN, 0x00000001
        )
        sleep(0.05)
        win32api.PostMessage(hwnd, win32con.WM_SYSKEYUP, win32con.VK_RETURN, 0xC0000001)
        return True

    def restore(self) -> None:
        """恢复窗口"""
        if self.hwnd == 0:
            return
        win32gui.ShowWindow(self.hwnd, win32con.SW_RESTORE)

    @overload
    def client_to_screen(self, x: int, y: int, /) -> tuple[int, int]: ...
    @overload
    def client_to_screen(
        self,
        x: int,
        y: int,
        /,
        client_rect: tuple[int, int, int, int],
        window_rect: tuple[int, int, int, int],
    ) -> tuple[int, int]: ...
    def client_to_screen(
        self,
        x: int,
        y: int,
        /,
        client_rect: tuple[int, int, int, int] | None = None,
        window_rect: tuple[int, int, int, int] | None = None,
    ) -> tuple[int, int]:
        """将客户区坐标转换为屏幕坐标"""
        if self.hwnd == 0:
            return (x, y)
        if client_rect is None or window_rect is None:
            client_rect = self.rect(True)
            window_rect = self.rect(False)

        x_diff = window_rect[0] - client_rect[0]
        y_diff = window_rect[1] - client_rect[1]
        return (x + x_diff, y + y_diff)

    def mouse_pos_to_client_mouse(self, x: int, y: int) -> tuple[int, int]:
        """将鼠标坐标转换为客户区坐标"""
        if self.hwnd == 0:
            return (x, y)
        client_rect = self.rect(True)
        return (x - client_rect[0], y - client_rect[1])

    def set_window_pos(self, x: int, y: int) -> None:
        """将窗口移动到屏幕坐标 (x, y)"""
        if self.hwnd == 0:
            return
        x = int(x)
        y = int(y)
        win32gui.SetWindowPos(
            self.hwnd,
            None,
            x,
            y,
            0,
            0,
            win32con.SWP_NOSIZE | win32con.SWP_NOZORDER,
        )

    def bring_window_into_view(self, work_area: bool = False):
        """将窗口移动到屏幕可见区域"""
        rect = self.rect(True)
        window_rect = self.rect(False)
        monitor_info = self.monitor_info
        left, top, right, bottom = (
            monitor_info["Work"] if work_area else monitor_info["Monitor"]
        )
        need_x = rect[0]
        need_y = rect[1]
        if rect[2] > right:
            need_x = right - (rect[2] - rect[0])
        elif rect[0] < left:
            need_x = left

        if rect[3] > bottom:
            need_y = bottom - (rect[3] - rect[1])
        elif rect[1] < top:
            need_y = top

        x, y = self.client_to_screen(
            need_x, need_y, client_rect=rect, window_rect=window_rect
        )
        if need_x != rect[0] or need_y != rect[1]:
            self.set_window_pos(x, y)


class Screen(metaclass=SingletonMeta):
    def __init__(self, title: str, game: "Game"):
        self.title = title
        self.game = game
        self.handle = Handle()

    def init_handle(self) -> bool:
        try:
            self.handle.init_handle(self.title)
            if self.handle.hwnd == 0:
                log.info(f"未能获取到游戏窗口: {self.title},尝试启动游戏")
                self.game.start_game()
                sleep(30)
                self.handle.init_handle(self.title)

            if self.handle.hwnd == 0:
                log.error(f"未能获取到游戏窗口: {self.title}")
                self.game.start_game()
                return False
            else:
                return True
        except Exception as e:
            log.error(f"未能获取到游戏窗口: {e}")
            self.game.start_game()
            return False

    def set_win(self) -> None:
        """设置窗口大小与位置"""

        def _set_win():
            # 如果窗口最小化或不可见，先将其恢复
            if self.handle.isMinimized or (
                not self.handle.isActive and not cfg.background_click
            ):
                self.handle.restore()
            # 将窗口设为活动窗口
            if not cfg.background_click:
                self.handle.setForeground()
            self.set_win_size = cfg.set_win_size
            self.set_win_position = cfg.set_win_position
            if cfg.set_windows:
                self.check_win_size(self.set_win_size)
                self.reduce_miscontact(self.set_win_position)
                self.adjust_win_size(
                    (int(self.set_win_size * 16 / 9), self.set_win_size)
                )
                self.adjust_win_position(self.set_win_position)

        _set_win()
        while True:
            try:
                width = self.handle.width(True)
                height = self.handle.height(True)
                if (
                    width != int(cfg.set_win_size * 16 / 9)
                    or height != cfg.set_win_size
                ):
                    _set_win()
                    sleep(1)
                else:
                    break
            except Exception as e:
                log.error(f"设置窗口出错: {e}")

    def reduce_miscontact(self, pos_style: str) -> None:
        """通过调整窗口置顶减少误触"""
        # 获取适用于win32gui与win32con的窗口句柄
        hwnd = self.handle.hwnd

        # 告诉系统当前进程是 DPI 感知的,确保窗口在高 DPI 系统上正确显示,并适应不同的 DPI 缩放
        windll.user32.SetProcessDPIAware()

        # 设置窗口始终置顶
        if not cfg.background_click:
            win32gui.SetWindowPos(
                hwnd,
                win32con.HWND_TOPMOST,
                0,
                0,
                0,
                0,
                win32con.SWP_NOMOVE | win32con.SWP_NOSIZE,
            )
        # 获取窗口的当前样式属性值
        style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
        # 移除窗口的可调整大小的边框，使得窗口大小固定
        style &= ~win32con.WS_THICKFRAME
        if pos_style != "free":
            # # 移除窗口的标题栏
            style &= ~win32con.WS_CAPTION
            # 移除窗口的单行边框
            style &= ~win32con.WS_BORDER
        # 位运算符 &= 结合按位取反操作符 ~
        # 将 win32con.WS_SIZEBOX、win32con.WS_MAXIMIZEBOX 这常量对应的位设置为 0，
        # 移除窗口大小调整框、最大化按钮
        style &= ~(win32con.WS_SIZEBOX | win32con.WS_MAXIMIZEBOX)
        # 将修改后的样式值 style 应用到窗口的样式属性上
        win32gui.SetWindowLong(hwnd, win32con.GWL_STYLE, style)
        win32gui.SetWindowPos(
            hwnd,
            None,
            0,
            0,
            0,
            0,
            win32con.SWP_NOMOVE
            | win32con.SWP_NOSIZE
            | win32con.SWP_NOZORDER
            | win32con.SWP_FRAMECHANGED,
        )

    def adjust_win_size(self, set_win_size: tuple[int, int] = (1920, 1080)) -> None:
        """调整窗口大小"""
        hwnd = self.handle.hwnd
        client_width, client_height = set_win_size

        # 获取当前窗口和客户区大小
        window_rect = win32gui.GetWindowRect(hwnd)
        client_rect = win32gui.GetClientRect(hwnd)

        # 计算边框和标题栏厚度
        window_width = window_rect[2] - window_rect[0]
        window_height = window_rect[3] - window_rect[1]
        current_client_width = client_rect[2]
        current_client_height = client_rect[3]

        width_diff = window_width - current_client_width
        height_diff = window_height - current_client_height

        # 计算需要的窗口大小
        required_window_width = client_width + width_diff
        required_window_height = client_height + height_diff
        # 设置窗口
        win32gui.SetWindowPos(
            hwnd,
            None,
            0,
            0,
            required_window_width,
            required_window_height,
            win32con.SWP_NOZORDER | win32con.SWP_NOMOVE,
        )

    def adjust_win_position(self, set_win_position: str = "free") -> None:
        """调整窗口位置"""
        if set_win_position == "free":
            return
        hwnd = self.handle.hwnd
        monitor_info = self.handle.monitor_info
        is_back: bool = cfg.background_click
        left, top, right, bottom = (
            monitor_info["Monitor"] if is_back else monitor_info["Work"]
        )
        width = self.handle.width(True)
        height = self.handle.height(True)
        if set_win_position == "left_top":
            pos = (left, top)
        elif set_win_position == "right_top":
            pos = (right - width, top)
        elif set_win_position == "left_bottom":
            pos = (left, bottom - height)
        elif set_win_position == "right_bottom":
            pos = (right - width, bottom - height)
        elif set_win_position == "center":
            pos = (
                left + (right - left - width) // 2,
                top + (bottom - top - height) // 2,
            )
        else:
            log.error(f"未知的窗口位置选项: {set_win_position}")
            return
        win32gui.SetWindowPos(hwnd, None, *pos, 0, 0, win32con.SWP_NOSIZE)

    def check_win_size(self, set_win_size: int) -> None:
        """检查窗口大小是否合适，若不合适则切换全屏再切换回窗口模式"""
        try:
            screen_width, screen_height = self.handle.monitor_size(
                not cfg.background_click  # 前台模式使用工作区大小
            )
            if screen_width < set_win_size * 16 / 9 or screen_height < set_win_size:
                log.error("屏幕分辨率过低，请重新设定分辨率")
                log.debug(f"窗口所在的屏幕分辨率: {screen_width}x{screen_height}")
                if not cfg.background_click:
                    screen_width, screen_height = self.handle.monitor_size(False)
                    if (
                        screen_width >= set_win_size * 16 / 9
                        and screen_height >= set_win_size
                    ):
                        log.info("当前屏幕全尺寸可考虑使用后台输入模式")
                mediator.link_start.emit()
                sleep(1)  # 等待结束
                return

            # 如果全屏，则切回窗口
            width = self.handle.width()
            height = self.handle.height()
            screen_width, screen_height = self.handle.monitor_size()
            if width == screen_width and height == screen_height:
                if cfg.set_win_position == "free":
                    win_pos = self.handle.rect()[:2]
                self.handle.switchFullScreenMode()
                sleep(0.5)
                # 进行判断如果还是全屏，再执行一次操作
                width = self.handle.width()
                height = self.handle.height()
                if width == screen_width and height == screen_height:
                    self.handle.switchFullScreenMode()
                    sleep(0.5)
                if cfg.set_win_position == "free":
                    self.handle.set_window_pos(*win_pos)
                    sleep(0.1)
        except Exception as e:
            log.error(f"检查屏幕分辨率失败: {e}")

    def reset_win(self) -> bool:
        """重置窗口"""
        try:
            hwnd = self.handle.hwnd
            # 获取窗口的当前样式
            style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
            # 获取窗口的当前扩展样式
            ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)

            # 恢复窗口样式：标题栏、大小调整框、最大化按钮
            style |= (
                win32con.WS_CAPTION | win32con.WS_THICKFRAME | win32con.WS_MAXIMIZEBOX
            )
            # 应用修改后的样式
            win32gui.SetWindowLong(hwnd, win32con.GWL_STYLE, style)

            # 取消始终置顶
            ex_style &= ~win32con.WS_EX_TOPMOST
            # 应用修改后的扩展样式
            win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, ex_style)

            # 更新窗口，使样式改变生效
            win32gui.SetWindowPos(
                hwnd,
                None,
                0,
                0,
                0,
                0,
                win32con.SWP_FRAMECHANGED
                | win32con.SWP_NOMOVE
                | win32con.SWP_NOSIZE
                | win32con.SWP_NOZORDER,
            )

            # 恢复窗口状态
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            win32gui.SetWindowPos(
                hwnd,
                win32con.HWND_NOTOPMOST,
                0,
                0,
                0,
                0,
                win32con.SWP_NOMOVE | win32con.SWP_NOSIZE,
            )

            # 获取窗口客户区的大小
            client_width = self.handle.width(client=True)
            client_height = self.handle.height(client=True)

            # 获取窗口的大小（包括边框、标题栏等）
            window_width = self.handle.width()
            window_height = self.handle.height()

            win32gui.SetWindowPos(
                hwnd,
                win32con.HWND_NOTOPMOST,
                0,
                0,
                window_width * 2 - client_width,
                window_height * 2 - client_height,
                win32con.SWP_NOMOVE,
            )
        except Exception as e:
            log.error(f"重置窗口失败: {e}")
            return False
        else:
            return True
