from ctypes import windll
from PIL import Image

from module.config import cfg


class ScreenShot:
    
    @staticmethod
    def take_screenshot(gray: bool = True) -> Image.Image:
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
