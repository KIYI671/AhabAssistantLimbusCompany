import random
from os import environ
from time import sleep

import pyautogui

from my_log.my_log import my_log


def mouse_click(coordinate, times=1, offset_x=0, offset_y=0):
    if coordinate is None:
        msg = "传入位置为空，无法进行点击"
        my_log("debug", msg)
        return False
    # 满足某些精确点击要求
    x = coordinate[0]
    y = coordinate[1]
    if offset_x == 0 and offset_y == 0:
        x += random.randint(-10, 10)
        y += random.randint(-10, 10)
    msg = f"点击位置:({x},{y})"
    my_log("debug", msg)
    for i in range(times):
        pyautogui.click(x, y)
        sleep(0.1)
    sleep(0.8)
    return True


def mouse_drag_down(coordinate):
    scale = 0
    if environ.get('window_size'):
        scale = int(environ.get('window_size'))
    scale_factors = [1, 1.333, 0.667, 0.833, 1.667, 2]
    pyautogui.moveTo(coordinate[0], coordinate[1])
    pyautogui.mouseDown()
    pyautogui.dragTo(coordinate[0], coordinate[1] + int(300 * scale_factors[scale]), duration=0.4)
    pyautogui.mouseUp()
    msg = f"选择卡包:({coordinate[0]},{coordinate[1]})"
    my_log("debug", msg)
    sleep(0.5)


def mouse_drag(coordinate, time=0.1, x=0, y=0):
    pyautogui.moveTo(coordinate[0], coordinate[1])
    pyautogui.mouseDown()
    pyautogui.dragTo(coordinate[0] + x, coordinate[1] + y, duration=time)
    pyautogui.mouseUp()
    sleep(0.5)


def mouse_scroll_farthest(direction=-3):
    msg = "鼠标滚动滚轮，放大/缩小界面"
    my_log("debug", msg)
    pyautogui.scroll(direction)
    sleep(0.5)


def mouse_click_blank(coordinate=(1, 1), times=1):
    msg = "点击（1，1）空白位置"
    my_log("debug", msg)
    x = coordinate[0] + random.randint(0, 10)
    y = coordinate[1] + random.randint(0, 10)
    for i in range(times):
        pyautogui.click(x, y)
    sleep(0.9)
    return True
