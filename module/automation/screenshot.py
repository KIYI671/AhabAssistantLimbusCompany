from ctypes import windll
from PIL import Image
from module.logger import log
from module.config import cfg
import pyautogui
import win32gui
import win32ui
import cv2
import numpy as np


class ScreenShot:
    
    @staticmethod
    def take_screenshot(gray: bool = True) -> Image.Image | None:
        """
        截取屏幕截图
        Args:
            gray (bool): 是否转为灰度图
        Returns:
            PIL.Image: 截图图像
        """
        if cfg.background_click:
            try:
                return ScreenShot.backgroud_screenshot(gray)
            except Exception as e:
                log.DEBUG(f"后台截图报错 {type(e).__name__}: {e}")
                return None
        else:
            try:
                return ScreenShot.take_screenshot_gdi(gray)
            except Exception as e:
                msg = f"GDI截图失败，尝试使用pyautogui截图，错误信息：{e}"
                log.DEBUG(msg)
                try:
                    return ScreenShot.take_screenshot_pyautogui(gray)
                except Exception as e2:
                    msg = f"pyautogui截图失败，错误信息：{e2}"
                    log.DEBUG(msg)
                    return None

    @staticmethod
    def take_screenshot_gdi(gray: bool = True) -> Image.Image:
        """
        截取屏幕截图（避免HDR/系统渲染差异，直接从GDI获取）。
        Args:
            gray (bool): 是否转为灰度图
        Returns:
            PIL.Image: 截图图像
        """
        # 设置DPI感知，避免缩放影响
        windll.user32.SetProcessDPIAware()

        # 获取屏幕尺寸
        hdc_screen = windll.user32.GetDC(0)
        screen_width = windll.user32.GetSystemMetrics(0)
        screen_height = windll.user32.GetSystemMetrics(1)

        # 创建设备上下文
        hdc_mem = windll.gdi32.CreateCompatibleDC(hdc_screen)
        hbitmap = windll.gdi32.CreateCompatibleBitmap(hdc_screen, screen_width, screen_height)
        windll.gdi32.SelectObject(hdc_mem, hbitmap)

        # 使用BitBlt复制屏幕内容到内存DC
        SRCCOPY = 0x00CC0020
        windll.gdi32.BitBlt(hdc_mem, 0, 0, screen_width, screen_height, hdc_screen, 0, 0, SRCCOPY)

        # 转换成PIL图像（需要 pywin32）
        import win32ui
        bmp = win32ui.CreateBitmapFromHandle(hbitmap)
        bmpinfo = bmp.GetInfo()
        bmpstr = bmp.GetBitmapBits(True)

        image = Image.frombuffer(
            'RGB',
            (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
            bmpstr, 'raw', 'BGRX', 0, 1
        )

        # 清理
        windll.gdi32.DeleteObject(hbitmap)
        windll.gdi32.DeleteDC(hdc_mem)
        windll.user32.ReleaseDC(0, hdc_screen)

        # 转灰度
        if gray:
            image = image.convert("L")

        # =========================
        # 添加窗口大小约束 (保持16:9)
        # =========================
        size_height = cfg.set_win_size
        size_width = int(size_height / 9 * 16)

        # 防止越界
        size_width = min(size_width, image.width)
        size_height = min(size_height, image.height)

        # 裁剪截图 (从左上角开始)
        image = image.crop((0, 0, size_width, size_height))

        return image
    
    @staticmethod
    def take_screenshot_pyautogui(gray: bool = True) -> Image.Image:
        """
        截取屏幕截图,使用pyautogui。
        Args:
            gray (bool): 是否将图片转化为灰度图
        Returns:
            screenshot: 截取的屏幕截图。
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

    @staticmethod
    def backgroud_screenshot(gray: bool = True) -> Image.Image:
        try:
            # 查找游戏窗口句柄（Unity引擎创建的游戏窗口通常使用"UnityWndClass"类名）
            hwnd = win32gui.FindWindow("UnityWndClass", "LimbusCompany")

            # 获取窗口的坐标和尺寸（返回(left, top, right, bottom)）
            rect = win32gui.GetWindowRect(hwnd)
            width, height = rect[2] - rect[0], rect[3] - rect[1]

            # 获取窗口设备上下文(DC)，用于后续绘图操作
            hwnd_dc = win32gui.GetWindowDC(hwnd)
            # 创建兼容的设备上下文
            mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
            # 创建内存设备上下文，用于临时存储位图
            save_dc = mfc_dc.CreateCompatibleDC()

            # 创建与窗口兼容的位图对象
            save_bit_map = win32ui.CreateBitmap()
            save_bit_map.CreateCompatibleBitmap(mfc_dc, width, height)

            # 将位图选入内存设备上下文
            save_dc.SelectObject(save_bit_map)

            # 将窗口内容绘制到内存设备上下文中（PW_RENDERFULLCONTENT=3表示渲染全部内容）
            windll.user32.PrintWindow(hwnd, save_dc.GetSafeHdc(), 3)

            # 获取位图信息（高度、宽度等）和像素数据
            bmpinfo = save_bit_map.GetInfo()
            bmpstr = save_bit_map.GetBitmapBits(True)

            # 将原始字节数据转换为numpy数组，并重塑为4通道(BGRA)图像格式
            capture = np.frombuffer(bmpstr, dtype=np.uint8).reshape(
                (bmpinfo["bmHeight"], bmpinfo["bmWidth"], 4)
            )
            # 确保内存连续排列，并移除Alpha通道（保留BGR）
            capture = np.ascontiguousarray(capture)[..., :-1]

            # 清理资源（按创建顺序逆序释放）
            win32gui.DeleteObject(save_bit_map.GetHandle())  # 删除位图对象
            save_dc.DeleteDC()  # 删除内存设备上下文
            mfc_dc.DeleteDC()  # 删除兼容设备上下文
            win32gui.ReleaseDC(hwnd, hwnd_dc)  # 释放窗口设备上下文

            # 将BGR格式转换为RGB格式
            capture_rgb = cv2.cvtColor(capture, cv2.COLOR_BGRA2RGB)
            
            # 将numpy数组转换为PIL图像对象
            pil_image = Image.fromarray(capture_rgb)

            # 将图片转换为灰度图
            if gray:
                pil_image = pil_image.convert("L")


            return pil_image
        except Exception as e:
            log.ERROR(f"后台截图报错: {e}")