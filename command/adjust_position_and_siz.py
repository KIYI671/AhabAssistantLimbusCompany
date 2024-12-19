import ctypes
from ctypes import windll
from os import environ
from time import sleep

import pyautogui
import win32con
import win32gui

from command.mouse_activity import mouse_click_blank
from my_decorator.decorator import begin_and_finish_time_log
from my_error.my_error import resolutionSettingError

resolution = [[1920, 1080], [2560, 1440], [1280, 720], [1600, 900], [3200, 1800], [3840, 2160]]


@begin_and_finish_time_log("窗口设置", False)
def adjust_position_and_size(hwnd: object, choice: object = 0) -> object:
    # 如果窗口最小化或不可见，先将其恢复
    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
    # 将窗口设为活动窗口
    win32gui.SetForegroundWindow(hwnd)

    # 获取窗口分辨率大小
    windows_size = "0"
    if environ.get('window_size'):
        windows_size = environ.get('window_size')

    windows_size = int(windows_size)

    # 将窗口状态重置，减少可能出现的问题
    # 按下 Ctrl 键
    pyautogui.keyDown('alt')
    # 按下 Enter 键
    pyautogui.press('enter')
    # 释放 Ctrl 键
    pyautogui.keyUp('alt')
    # 判断是否是全屏，如果是则设为窗口
    if isfullscreen(hwnd):
        sleep(1)
        #mouse_click_blank()
        # 按下 Ctrl 键
        pyautogui.keyDown('alt')
        # 按下 Enter 键
        pyautogui.press('enter')
        # 释放 Ctrl 键
        pyautogui.keyUp('alt')

    user32 = ctypes.windll.user32
    SM_CXSCREEN = 0
    SM_CYSCREEN = 1
    screen_width = user32.GetSystemMetrics(SM_CXSCREEN)
    screen_height = user32.GetSystemMetrics(SM_CYSCREEN)
    if resolution[windows_size][0] > screen_width or resolution[windows_size][1] > screen_height:
        raise resolutionSettingError(
            "屏幕过小，无法支持设置的分辨率!!!\nThe screen is too small to support the set resolution!!!")

    # 告诉系统当前进程是 DPI 感知的,确保窗口在高 DPI 系统上正确显示,并适应不同的 DPI 缩放
    windll.user32.SetProcessDPIAware()
    # 将窗口始终置顶显示
    win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 0, 0, 1920, 1080, win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
    # 如果选择防止误触，则移除窗口标题栏、大小调整框、最大化按钮
    reduce_miscontact(hwnd)
    # 设置窗口位置与大小
    adjust_position(hwnd, windows_size)
    adjust_size(hwnd, windows_size)


def adjust_position(hwnd, windows_size):
    # 设置窗口位置
    win32gui.SetWindowPos(hwnd, None, 0, 0, resolution[windows_size][0], resolution[windows_size][1],
                          win32con.SWP_NOSIZE)


def adjust_size(hwnd, windows_size):
    # 设置窗口大小
    win32gui.SetWindowPos(hwnd, None, 0, 0, resolution[windows_size][0], resolution[windows_size][1],
                          win32con.SWP_NOMOVE)


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


# 判断窗口是否是全屏
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


def reset_win(hwnd):
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
