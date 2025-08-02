from ctypes import windll
from time import sleep

import pyautogui
import win32con
import win32gui

from module.config import cfg
from utils.singletonmeta import SingletonMeta


class Screen(metaclass=SingletonMeta):
    def __init__(self, title, logger,game):
        self.logger = logger
        self.title = title
        self.game = game
        self.handle = None

    def init_handle(self):
        try:
            # 获取所有标题匹配的窗口
            windows = pyautogui.getWindowsWithTitle(self.title)

            while not windows:
                self.logger.ERROR(f"未能获取到游戏窗口: {self.title},尝试启动游戏")
                self.game.start_game()
                sleep(30)
                windows = pyautogui.getWindowsWithTitle(self.title)

            # 使用 next() 和生成器表达式直接获取第一个匹配的窗口
            self.handle = next((t for t in windows if t.title == self.title), None)

            if self.handle is None:
                self.logger.ERROR(f"未能获取到游戏窗口: {self.title}")
                self.game.start_game()
                return False
            else:
                return True
        except Exception as e:
            self.logger.ERROR(f"未能获取到游戏窗口: {e}")
            self.game.start_game()

    def set_win(self):
        # 如果窗口最小化或不可见，先将其恢复
        if self.handle.isMinimized or not self.handle.isActive:
            self.handle.restore()
        # 将窗口设为活动窗口
        win32gui.SetForegroundWindow(self.handle._hWnd)
        self.set_win_size = cfg.set_win_size
        self.set_win_position = cfg.set_win_position
        if cfg.set_windows:
            self.check_win_size(self.set_win_size)
            self.reduce_miscontact()
            self.adjust_win_size(self.set_win_size)
            self.adjust_win_position(self.set_win_position)

    def reduce_miscontact(self):
        # 获取适用于win32gui与win32con的窗口句柄
        hwnd = self.handle._hWnd

        # 告诉系统当前进程是 DPI 感知的,确保窗口在高 DPI 系统上正确显示,并适应不同的 DPI 缩放
        windll.user32.SetProcessDPIAware()

        # 设置窗口始终置顶
        win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0, win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
        # 获取窗口的当前样式属性值
        style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
        # 移除窗口的标题栏
        style &= ~win32con.WS_CAPTION
        # 移除窗口的可调整大小的边框，使得窗口大小固定
        style &= ~win32con.WS_THICKFRAME
        # 移除窗口的单行边框
        style &= ~win32con.WS_BORDER
        # 位运算符 &= 结合按位取反操作符 ~
        # 将 win32con.WS_SIZEBOX、win32con.WS_MAXIMIZEBOX 这常量对应的位设置为 0，移除窗口大小调整框、最大化按钮
        style &= ~(win32con.WS_SIZEBOX | win32con.WS_MAXIMIZEBOX)
        # 将修改后的样式值 style 应用到窗口的样式属性上
        win32gui.SetWindowLong(hwnd, win32con.GWL_STYLE, style)

    def adjust_win_size(self, set_win_size):
        hwnd = self.handle._hWnd
        win32gui.SetWindowPos(hwnd, None, 0, 0, int(cfg.set_win_size * 16 / 9), cfg.set_win_size, win32con.SWP_NOMOVE)

    def adjust_win_position(self, set_win_position):
        hwnd = self.handle._hWnd
        win32gui.SetWindowPos(hwnd, None, 0, 0, 0, 0, win32con.SWP_NOSIZE)

    def check_win_size(self, set_win_size):
        try:
            screen_width = pyautogui.size().width
            screen_height = pyautogui.size().height
            if screen_width < set_win_size * 16 / 9 or screen_height < set_win_size:
                self.logger.ERROR(f"屏幕分辨率过低，请重新设定分辨率")
                pyautogui.hotkey('ctrl', 'q')
            pyautogui.hotkey('alt', 'enter')
            sleep(0.5)
            # 进行判断如果全屏，再执行一次操作
            # 获取窗口位置和大小
            width = self.handle.width
            height = self.handle.height
            # 获取屏幕分辨率
            screen_width, screen_height = pyautogui.size()
            # 判断窗口是否全屏
            if width == screen_width and height == screen_height:
                pyautogui.hotkey('alt', 'enter')
        except Exception as e:
            self.logger.ERROR(f"检查屏幕分辨率失败: {e}")

    def reset_win(self):
        hwnd = self.handle._hWnd
        # 获取窗口的当前样式
        style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
        # 获取窗口的当前扩展样式
        ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)

        # 恢复窗口样式：标题栏、大小调整框、最大化按钮
        style |= win32con.WS_CAPTION | win32con.WS_THICKFRAME | win32con.WS_MAXIMIZEBOX
        # 应用修改后的样式
        win32gui.SetWindowLong(hwnd, win32con.GWL_STYLE, style)

        # 取消始终置顶
        ex_style &= ~win32con.WS_EX_TOPMOST
        # 应用修改后的扩展样式
        win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, ex_style)

        # 更新窗口，使样式改变生效
        win32gui.SetWindowPos(hwnd, None, 0, 0, 0, 0,
                              win32con.SWP_FRAMECHANGED | win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOZORDER)

        # 恢复窗口状态
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        win32gui.SetWindowPos(hwnd, win32con.HWND_NOTOPMOST, 0, 0, 0, 0, win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)

        # 获取窗口客户区的大小
        client_rect = win32gui.GetClientRect(hwnd)
        client_width = client_rect[2]
        client_height = client_rect[3]

        # 获取窗口的大小（包括边框、标题栏等）
        window_rect = win32gui.GetWindowRect(hwnd)
        window_width = window_rect[2] - window_rect[0]
        window_height = window_rect[3] - window_rect[1]

        win32gui.SetWindowPos(hwnd, win32con.HWND_NOTOPMOST, 0, 0, window_width * 2 - client_width,
                              window_height * 2 - client_height, win32con.SWP_NOMOVE)
