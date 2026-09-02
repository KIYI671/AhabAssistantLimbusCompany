from time import sleep
from typing import TYPE_CHECKING, overload

from module.platform_compat import IS_WINDOWS

if IS_WINDOWS:
    import win32api
    import win32con
    import win32gui

from app import mediator
from module.config import cfg
from module.logger import log
from utils.singletonmeta import SingletonMeta

if TYPE_CHECKING:
    from .game import Game


def create_handle():
    """按平台创建对应的窗口句柄管理器"""
    if IS_WINDOWS:
        return Handle()
    from module.game_and_screen.x11_handle import X11Handle

    return X11Handle()


class Handle:
    """提供统一的获取窗口信息的接口"""

    _hwnd: int = 0
    _transparent = False

    def __init__(self):
        self._enum_windows_list = []

    def init_handle(self, title: str = "LimbusCompany", class_name: str = "UnityWndClass") -> int:
        """获取窗口句柄"""
        hwnd = win32gui.FindWindow(class_name, title)
        if hwnd:
            self._hwnd = hwnd
        else:
            self._hwnd = 0
            try:
                self._enum_windows_list.clear()
                win32gui.EnumWindows(self._enum_windows_callback, None)
            except win32gui.error:
                pass
            except Exception as e:
                log.error(f"枚举窗口时发生错误: {e}", stacklevel=3)
            if self._hwnd == 0:
                log.error("未能获取到游戏窗口", stacklevel=3)
                log.debug(f"枚举窗口列表: {self._enum_windows_list}")
                self._enum_windows_list.clear()
        return self._hwnd

    def _enum_windows_callback(self, hwnd, _):
        """该函数于GUI线程中返回停止信号固定触发`win32gui.error`报错, 外部调用务必捕获异常, 以防崩溃"""
        class_name = win32gui.GetClassName(hwnd)
        window_text = win32gui.GetWindowText(hwnd)

        if class_name == "UnityWndClass" and window_text == "LimbusCompany":
            self._enum_windows_list.append(f"hwnd: {hwnd}, class_name: {class_name}, window_text: {window_text}")
            log.debug(f"在枚举窗口中找到匹配的窗口: {hwnd}", stacklevel=4)
            self._hwnd = hwnd
            self._enum_windows_list.clear()
            return False  # 停止枚举
        elif class_name == "UnityWndClass" or window_text == "LimbusCompany":
            self._enum_windows_list.append(f"hwnd: {hwnd}, class_name: {class_name}, window_text: {window_text}")
        return True  # 继续枚举

    @property
    def hwnd(self) -> int:
        """获取窗口句柄"""
        if self._hwnd == 0:
            if cfg.config.simulator:
                log.debug("模拟器模式下无法获取窗口句柄", stacklevel=3)
            else:
                self.init_handle()
        elif not win32gui.IsWindow(self._hwnd):
            log.warning(f"窗口句柄无效，可能窗口已关闭，重新获取, 当前句柄为 {self._hwnd}", stacklevel=3)
            self.init_handle()
            if win32gui.IsWindow(self._hwnd):
                log.info(f"重新获取窗口句柄成功, 新句柄为 {self._hwnd}", stacklevel=3)
        return self._hwnd

    @property
    def pid(self) -> int:
        """游戏窗口所属进程 PID（用于结束游戏进程）"""
        from module.platform_compat import get_window_pid_on_windows

        return get_window_pid_on_windows(self.hwnd) or 0

    @property
    def isTransparent(self) -> bool:
        """判断窗口是否透明"""
        return self._transparent

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
        monitor_info = win32api.GetMonitorInfo(win32api.MonitorFromWindow(self.hwnd, win32con.MONITOR_DEFAULTTONEAREST))
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
        win32api.PostMessage(hwnd, win32con.WM_SYSKEYDOWN, win32con.VK_RETURN, 0x00000001)
        sleep(0.05)
        win32api.PostMessage(hwnd, win32con.WM_SYSKEYUP, win32con.VK_RETURN, 0xC0000001)
        return True

    def restore(self, activate: bool = False) -> None:
        """恢复窗口

        Parameters
        ---
        activate: bool
            是否在恢复的同时激活窗口（对应 SW_RESTORE），默认仅显示不激活
        """
        if self.hwnd == 0:
            return
        win32gui.ShowWindow(self.hwnd, win32con.SW_RESTORE if activate else win32con.SW_SHOWNOACTIVATE)

    @overload
    def client_to_window(self, x: int, y: int, /) -> tuple[int, int]: ...
    @overload
    def client_to_window(
        self,
        x: int,
        y: int,
        /,
        client_rect: tuple[int, int, int, int],
        window_rect: tuple[int, int, int, int],
    ) -> tuple[int, int]: ...
    def client_to_window(
        self,
        x: int,
        y: int,
        /,
        client_rect: tuple[int, int, int, int] | None = None,
        window_rect: tuple[int, int, int, int] | None = None,
    ) -> tuple[int, int]:
        """将客户区屏幕坐标转换为窗口外框屏幕坐标"""
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

    def set_window_size(self, width: int, height: int) -> None:
        """设置窗口（外框）大小，保持位置与 Z 序不变"""
        if self.hwnd == 0:
            return
        win32gui.SetWindowPos(
            self.hwnd,
            None,
            0,
            0,
            int(width),
            int(height),
            win32con.SWP_NOZORDER | win32con.SWP_NOMOVE,
        )

    def set_topmost(self, topmost: bool) -> None:
        """设置窗口是否始终置顶"""
        if self.hwnd == 0:
            return
        win32gui.SetWindowPos(
            self.hwnd,
            win32con.HWND_TOPMOST if topmost else win32con.HWND_NOTOPMOST,
            0,
            0,
            0,
            0,
            win32con.SWP_NOMOVE | win32con.SWP_NOSIZE,
        )

    def set_decorated(self, keep_caption: bool = True) -> None:
        """调整窗口装饰：始终移除可调整边框与最大化按钮，keep_caption 决定是否保留标题栏"""
        if self.hwnd == 0:
            return
        style = win32gui.GetWindowLong(self.hwnd, win32con.GWL_STYLE)
        style &= ~win32con.WS_THICKFRAME
        if not keep_caption:
            style &= ~win32con.WS_CAPTION
            style &= ~win32con.WS_BORDER
        style &= ~(win32con.WS_SIZEBOX | win32con.WS_MAXIMIZEBOX)
        win32gui.SetWindowLong(self.hwnd, win32con.GWL_STYLE, style)
        win32gui.SetWindowPos(
            self.hwnd,
            None,
            0,
            0,
            0,
            0,
            win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOZORDER | win32con.SWP_FRAMECHANGED,
        )

    def set_window_transparent(self, transparent: bool = True) -> None:
        """设置窗口是否透明, 同时设置鼠标穿透"""
        hwnd = self.hwnd
        if hwnd == 0:
            return
        if not cfg.background_click:
            transparent = False

        ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
        if not (ex_style & win32con.WS_EX_LAYERED) and transparent:
            ex_style = ex_style | win32con.WS_EX_LAYERED
            win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, ex_style)

        if transparent:
            ex_style |= win32con.WS_EX_LAYERED
            ex_style |= win32con.WS_EX_TRANSPARENT
            win32gui.SetLayeredWindowAttributes(hwnd, 0, 0, win32con.LWA_ALPHA)
        else:
            ex_style &= ~win32con.WS_EX_LAYERED
            ex_style &= ~win32con.WS_EX_TRANSPARENT
        win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, ex_style)
        self._transparent = transparent

    def bring_window_into_view(self, work_area: bool = False) -> None:
        """将窗口移动到屏幕可见区域"""
        rect = self.rect(True)
        window_rect = self.rect(False)
        monitor_info = self.monitor_info
        left, top, right, bottom = monitor_info["Work"] if work_area else monitor_info["Monitor"]
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
        elif rect[1] == top:
            if cfg.set_win_position == "free":
                if rect[3] - rect[1] != bottom - top:
                    need_y = (
                        top - self.client_to_window(0, 0, client_rect=rect, window_rect=window_rect)[1]
                    )  # 防止标题栏不在窗口内

        x, y = self.client_to_window(need_x, need_y, client_rect=rect, window_rect=window_rect)
        if need_x != rect[0] or need_y != rect[1]:
            self.set_window_pos(x, y)


class Screen(metaclass=SingletonMeta):
    def __init__(self, title: str, game: "Game"):
        self.title = title
        self.game = game
        self.handle = create_handle()

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
            if self.handle.isMinimized or (not self.handle.isActive and not cfg.background_click):
                self.handle.restore()
            # 将窗口设为活动窗口
            if not cfg.background_click:
                self.handle.setForeground()
            self.set_win_size = cfg.set_win_size
            self.set_win_position = cfg.set_win_position
            if cfg.set_windows:
                self.check_win_size(self.set_win_size)
                self.reduce_miscontact(self.set_win_position)
                self.adjust_win_size((int(self.set_win_size * 16 / 9), self.set_win_size))
                self.adjust_win_position(self.set_win_position)

        _set_win()
        while True:
            try:
                width = self.handle.width(True)
                height = self.handle.height(True)
                if width != int(cfg.set_win_size * 16 / 9) or height != cfg.set_win_size:
                    _set_win()
                    sleep(1)
                else:
                    break
            except Exception as e:
                log.error(f"设置窗口出错: {e}")

    def reduce_miscontact(self, pos_style: str) -> None:
        """通过调整窗口置顶减少误触"""
        # 设置窗口始终置顶
        if not cfg.background_click:
            self.handle.set_topmost(True)
        # 移除窗口的可调整大小的边框，使得窗口大小固定；非 free 定位时同时移除标题栏
        self.handle.set_decorated(keep_caption=(pos_style == "free"))
        sleep(0.1)  # 确保样式修改生效

    def adjust_win_size(self, set_win_size: tuple[int, int] = (1920, 1080)) -> None:
        """调整窗口大小"""
        client_width, client_height = set_win_size

        # 获取当前窗口和客户区大小，计算装饰（边框+标题栏）厚度后补偿
        window_rect = self.handle.rect()
        client_rect = self.handle.rect(True)
        window_width = window_rect[2] - window_rect[0]
        window_height = window_rect[3] - window_rect[1]
        current_client_width = client_rect[2] - client_rect[0]
        current_client_height = client_rect[3] - client_rect[1]

        required_window_width = client_width + (window_width - current_client_width)
        required_window_height = client_height + (window_height - current_client_height)
        self.handle.set_window_size(required_window_width, required_window_height)

    def adjust_win_position(self, set_win_position: str = "free") -> None:
        """调整窗口位置"""
        if set_win_position == "free":
            return
        monitor_info = self.handle.monitor_info
        is_back: bool = cfg.background_click
        left, top, right, bottom = monitor_info["Monitor"] if is_back else monitor_info["Work"]
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
        self.handle.set_window_pos(*pos)

    def check_win_size(self, set_win_size: int) -> None:
        """检查窗口大小是否合适，若不合适则切换全屏再切换回窗口模式"""
        try:
            screen_width, screen_height = self.handle.monitor_size(
                not cfg.background_click  # 前台模式使用工作区大小
            )
            if cfg.win_input_type != "window_move":
                if screen_width < set_win_size * 16 / 9 or screen_height < set_win_size:
                    log.error("屏幕分辨率过低，请重新设定分辨率，或考虑使用后台增强模式")
                    log.debug(f"窗口所在的屏幕分辨率: {screen_width}x{screen_height}")
                    if not cfg.background_click:
                        screen_width, screen_height = self.handle.monitor_size(False)
                        if screen_width >= set_win_size * 16 / 9 and screen_height >= set_win_size:
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

    def reset_win(self, activate: bool = True) -> bool:
        """重置窗口。

        任务结束链路会传 activate=False，只恢复窗口样式，不重新抢占前台焦点。
        """
        try:
            log.debug(f"开始重置游戏窗口，activate={activate}")
            # 恢复窗口样式：标题栏、大小调整框、最大化按钮
            self.handle.set_decorated(keep_caption=True)

            # 取消始终置顶
            self.handle.set_topmost(False)
            self.handle.set_window_transparent(False)

            # 恢复窗口状态
            # 结束清理只需要恢复外观，不应该把前台再交回游戏窗口。
            self.handle.restore(activate=activate)

            # 获取窗口客户区的大小
            client_width = self.handle.width(client=True)
            client_height = self.handle.height(client=True)

            # 获取窗口的大小（包括边框、标题栏等）
            window_width = self.handle.width()
            window_height = self.handle.height()

            self.handle.set_window_size(
                window_width * 2 - client_width,
                window_height * 2 - client_height,
            )
        except Exception as e:
            log.error(f"重置窗口失败: {e}")
            return False
        else:
            log.debug("重置游戏窗口完成")
            return True
