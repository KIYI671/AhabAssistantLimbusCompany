import ctypes
from ctypes import windll
from os import environ
from time import sleep

import pyautogui
import win32con
import win32gui

from command.mouse_activity import mouse_click_blank
from my_decorator.decorator import begin_and_finish_log

resolution = [[1920, 1080], [2560, 1440], [1280, 720], [1600, 900], [3200, 1800], [3840, 2160]]


@begin_and_finish_log("窗口设置")
def adjust_position_and_size(hwnd: object, windows_size=environ.get('window_size'), choice: object = 0) -> object:
    # 如果窗口最小化或不可见，先将其恢复
    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
    # 将窗口设为活动窗口
    win32gui.SetForegroundWindow(hwnd)

    """if isfullscreen(hwnd):
        sleep(1)
        mouse_click_blank()
        # 按下 Ctrl 键
        pyautogui.keyDown('alt')
        # 按下 Enter 键
        pyautogui.press('enter')
        # 释放 Ctrl 键
        pyautogui.keyUp('alt')"""

    # 告诉系统当前进程是 DPI 感知的,确保窗口在高 DPI 系统上正确显示,并适应不同的 DPI 缩放
    windll.user32.SetProcessDPIAware()
    # 将窗口始终置顶显示
    win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 0, 0, 1920, 1080, win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
    # 如果选择防止误触，则移除窗口标题栏、大小调整框、最大化按钮
    reduce_miscontact(hwnd)
    # 设置窗口位置与大小
    adjust_position(hwnd,windows_size)
    adjust_size(hwnd,windows_size)


def adjust_position(hwnd,windows_size):
    # 设置窗口位置
    win32gui.SetWindowPos(hwnd, None, 0, 0, resolution[windows_size][0], resolution[windows_size][1], win32con.SWP_NOSIZE)


def adjust_size(hwnd,windows_size):
    # 设置窗口大小
    win32gui.SetWindowPos(hwnd, None, 0, 0, resolution[windows_size][0], resolution[windows_size][1], win32con.SWP_NOMOVE)


def reduce_miscontact(hwnd):
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


"""
def isfullscreen(hwnd):
    # 定义与Windows API对应的类型
    user32 = ctypes.windll.user32
    SM_CXSCREEN = 0
    SM_CYSCREEN = 1

    # 使用ctypes获取屏幕宽度和高度
    screen_width = user32.GetSystemMetrics(SM_CXSCREEN)
    screen_height = user32.GetSystemMetrics(SM_CYSCREEN)
    # 获取窗口的矩形位置和尺寸
    rect = win32gui.GetWindowRect(hwnd)
    # 获取窗口的样式
    style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)

    # 检查窗口是否是弹出式窗口且没有边框
    is_popup = (style & win32con.WS_POPUP) == win32con.WS_POPUP
    # 检查窗口尺寸是否与屏幕尺寸相匹配
    is_fullscreen_size = (rect[2] - rect[0] == screen_width) and (rect[3] - rect[1] == screen_height)

    return is_popup and is_fullscreen_size


def is_window_minimized_or_invisible(hwnd):
    # 获取窗口的显示状态
    window_state = win32gui.GetWindowPlacement(hwnd)

    # 窗口状态标志
    # SW_SHOWMINIMIZED: 窗口最小化
    # SW_HIDE: 窗口隐藏
    minimized = window_state[1] == win32gui.SW_SHOWMINIMIZED
    hidden = window_state[1] == win32gui.SW_HIDE

    # 返回窗口是否最小化或不可见
    return minimized or hidden
"""
