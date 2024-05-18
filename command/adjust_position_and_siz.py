from ctypes import windll

import win32con
import win32gui

from my_decorator.decorator import begin_and_finish_log


@begin_and_finish_log("窗口设置")
def adjust_position_and_size(hwnd: object, choice: object = 0) -> object:
    # 如果窗口最小化或不可见，先将其恢复
    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
    # 将窗口设为活动窗口
    win32gui.SetForegroundWindow(hwnd)
    # 告诉系统当前进程是 DPI 感知的,确保窗口在高 DPI 系统上正确显示,并适应不同的 DPI 缩放
    windll.user32.SetProcessDPIAware()
    # 将窗口始终置顶显示
    win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 0, 0, 1920, 1080, win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
    # 如果选择防止误触，则移除窗口标题栏、大小调整框、最大化按钮
    reduce_miscontact(hwnd)
    # 设置窗口位置与大小
    adjust_position(hwnd)
    adjust_size(hwnd)


def adjust_position(hwnd):
    # 设置窗口位置
    win32gui.SetWindowPos(hwnd, None, 0, 0, 1920, 1080, win32con.SWP_NOSIZE)


def adjust_size(hwnd):
    # 设置窗口大小
    win32gui.SetWindowPos(hwnd, None, 0, 0, 1920, 1080, win32con.SWP_NOMOVE)


def reduce_miscontact(hwnd):
    # 获取窗口的当前样式属性值
    style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
    style &= ~win32con.WS_CAPTION
    style &= ~win32con.WS_THICKFRAME
    style &= ~win32con.WS_BORDER
    # 位运算符 &= 结合按位取反操作符 ~
    # 将 win32con.WS_SIZEBOX、win32con.WS_MAXIMIZEBOX 这常量对应的位设置为 0，移除窗口大小调整框、最大化按钮
    style &= ~(win32con.WS_SIZEBOX | win32con.WS_MAXIMIZEBOX)
    # 将修改后的样式值 style 应用到窗口的样式属性上
    win32gui.SetWindowLong(hwnd, win32con.GWL_STYLE, style)
