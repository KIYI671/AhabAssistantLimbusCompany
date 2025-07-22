from ctypes import windll

import pyautogui

from module.config import cfg


class ScreenShot:

    @staticmethod
    def take_screenshot(gray = True):
        """
        截取屏幕截图。
        :param gray: 是否将图片转化为灰度图
        :return screenshot: 截取的屏幕截图。
        """
        # 根据配置获取窗口的高度
        size_height = cfg.set_win_size
        # 计算窗口的宽度，保持16:9的宽高比
        size_width = size_height / 9 * 16

        """# 如果move参数为True，则尝试移动鼠标到屏幕左上角
        if move:
            try:
                pyautogui.moveTo(1, 1)
            except:
                pass"""

        # 设置进程的DPI感知，以确保截图在不同DPI设置下正确显示
        windll.user32.SetProcessDPIAware()
        # 进行全屏截图
        screenshot_temp = pyautogui.screenshot()
        if gray:
            # 将截图转换为灰度图像
            screenshot = screenshot_temp.convert('L')
        else:
            screenshot = screenshot_temp

        # 裁剪截图到指定的宽高
        screenshot = screenshot.crop((0, 0, size_width, size_height))

        # 返回裁剪后的截图
        return screenshot
