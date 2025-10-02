from ast import List
import gc
import math
import random
import time
from PIL.Image import Image

import cv2
import numpy as np

from utils.image_utils import ImageUtils
from utils.singletonmeta import SingletonMeta

from .screenshot import ScreenShot
from ..config import cfg
from ..logger import log
from ..ocr import ocr

class Automation(metaclass=SingletonMeta):
    """自动化管理类，用于管理与游戏窗口有关的自动化操作"""

    def __init__(self, windows_title):
        self.windows_title = windows_title
        self.screenshot = None
        self.input_handler = None

        self.init_input()

        self.img_cache = {}
        self.last_screenshot_time = 0
        self.last_click_time = 0
        self.model = 'clam'

    def init_input(self):
        """初始化输入处理器，将输入操作如点击、拖动等绑定至实例变量"""
        if cfg.simulator:
            if cfg.simulator_type == 0:
                from ..simulator.mumu_control import MumuControl
                if MumuControl.connection_device is not None:
                    self.input_handler = MumuControl.connection_device
            else:
                from module.simulator.simulator_control import SimulatorControl
                self.input_handler = SimulatorControl.connection_device
        else:
            if cfg.background_click:
                from .input import BackgroundInput
                log.debug("使用后台点击模块")
                self.input_handler = BackgroundInput()
            else:
                from .input import Input
                log.debug("使用前台点击模块")
                self.input_handler = Input()
        if self.input_handler is None:
            from .input import BackgroundInput
            self.input_handler = BackgroundInput()
        self.mouse_click = self.input_handler.mouse_click
        self.mouse_click_blank = self.input_handler.mouse_click_blank
        self.mouse_drag = self.input_handler.mouse_drag
        self.mouse_drag_down = self.input_handler.mouse_drag_down
        self.mouse_scroll = self.input_handler.mouse_scroll
        self.set_pause = self.input_handler.set_pause
        self.wait_pause = self.input_handler.wait_pause
        self.mouse_to_blank = self.input_handler.mouse_to_blank
        self.mouse_drag_link = self.input_handler.mouse_drag_link
        self.key_press = self.input_handler.key_press

    def check_pause(self) -> bool:
        """
        检查是否处于暂停状态

        Returns:
            bool: 是否处于暂停状态
        """
        return self.input_handler.is_pause

    def get_restore_time(self) -> float:
        """
        获取上一次结束暂停的时间
        Returns:
            float: 上一次结束暂停的时间
        """
        return self.input_handler.restore_time if self.input_handler.restore_time else 0

    def click_element(self, target, find_type="image", threshold=0.8, max_retries=1, take_screenshot=False,
                      offset=True, action="click", times=1, dx=0, dy=0, model=None, my_crop=None, click=True,
                      drag_time=None, interval=0.5):
        """查找并点击屏幕上的元素"""
        if model is None:
            model = self.model
        coordinates = self.find_element(target, find_type, threshold, max_retries, take_screenshot, model=model,
                                        my_crop=my_crop, addtional_stack=1)
        if coordinates:
            if click:
                return self.mouse_action_with_pos(coordinates, offset, action, times, drag_time, dx, dy, find_type,
                                                  interval)
            return coordinates
        return False

    def calculate_click_position(self, coordinates, offset=True):
        """
        根据给定的坐标计算点击位置。
        参数:
        coordinates (tuple): 一个包含(x, y)坐标的元组，表示点击的位置。
        返回:
        tuple: 经过计算后的点击位置坐标。
        """
        # TODO:后续适配无需窗口设置模式
        x, y = coordinates
        screenshot = np.array(self.screenshot)
        if offset:
            x = max(0, min(screenshot.shape[1], x + random.randint(-10, 10)))
            y = max(0, min(screenshot.shape[0], y + random.randint(-10, 10)))
        return x, y

    def mouse_action_with_pos(self, coordinates, offset=True, action="click", times=1, drag_time=None, dx=0, dy=0,
                              find_type=None, interval=0.5) -> bool:
        """
        在指定坐标上执行点击操作
        Args:
            coordinates: 坐标位置，用于计算点击位置
            offset: 是否使用偏移量计算点击位置，默认为True
            action: 鼠标操作类型，默认为"click"
            move_back: 是否在操作后将鼠标移动回原位置，默认为False
        Returns:
           bool (True) : 总是返回True表示操作执行完毕
        """
        if find_type == 'image_with_multiple_targets' and len(coordinates) > 0:
            for c in coordinates:
                self.mouse_action_with_pos(c, offset, action, times, dx, dy, find_type="image", interval=1)
            return True

        if cfg.mouse_action_interval and interval == 0.5:
            interval = cfg.mouse_action_interval

        if self.last_click_time == 0:
            self.last_click_time = time.time()
        if time.time() - self.last_click_time < interval:
            time.sleep(interval)
            self.last_click_time = time.time()

        # 计算传入的位置
        x, y = self.calculate_click_position(coordinates, offset)

        # 定义鼠标操作映射
        action_map = {
            "click": self.mouse_click,
            "drag": self.mouse_drag,
            "drag_down": self.mouse_drag_down,
            "scroll": self.mouse_scroll
        }
        # 根据操作类型执行相应的鼠标操作
        if action in action_map:
            if action == "click":
                self.mouse_click(x, y, times=times)
            elif action == "drag":
                self.mouse_drag(x, y, drag_time=drag_time, dx=dx, dy=dy)
            elif action == "drag_down":
                self.mouse_drag_down(x, y)
            elif action == "scroll":
                self.mouse_scroll()
            self.last_click_time = time.time()
        else:
            # 如果操作类型未知，抛出异常
            raise ValueError(f"未知的操作类型{action}")

        return True

    def take_screenshot(self, gray: bool = True) -> Image:
        """
        截取当前屏幕并返回图像对象。
        Args:
            gray (bool): 是否将图像转换为灰度图，默认为True。
        Returns:
            Image: 截取当前屏幕的图像对象
        """
        start_time = time.time()
        screenshot_interval_time = cfg.screenshot_interval if cfg.screenshot_interval else 0.85
        while True:
            try:
                result = ScreenShot.take_screenshot(gray)
                if result:
                    self.screenshot = result
                    if self.last_screenshot_time == 0:
                        self.last_screenshot_time = time.time()
                        interval_time = 100
                    else:
                        interval_time = time.time() - self.last_screenshot_time
                    if interval_time > screenshot_interval_time:
                        self.last_screenshot_time = time.time()
                        return result
                    else:
                        return None
            except Exception as e:
                log.error(f"截图失败:{e}")
            time.sleep(1)
            if time.time() - start_time > 60:
                raise RuntimeError("截图超时")

    def find_element(self, target, find_type='image', threshold=0.8, max_retries=1, take_screenshot=False,
                     model=None, my_crop=None, addtional_stack=0):
        """
        查找元素，并根据指定的查找类型执行不同的查找策略。
        Args:
            target: 查找目标，可以是图像路径或文字。
            find_type: 查找类型，例如'image', 'text'等。
            threshold: 查找阈值，用于图像查找时的相似度匹配。
            max_retries: 最大重试次数。
            take_screenshot: 是否需要先截图。
            model: 查找的策略,'clam' 为在模板图片位置查找，'normal' 为模板图片位置扩大范围查找，'aggressive' 为全截屏区域查找
            my_crop: 用于OCR识别的已截取的部分图片
            addtional_stack: 用于日志堆栈层级调整
        Returns:
            查找到的元素位置，或者在图像计数查找时返回计数。
        """
        if model is None:
            model = self.model
        # 如果不需要截图，则重试次数设置为1
        max_retries = 1 if not take_screenshot else max_retries
        for i in range(max_retries):
            if take_screenshot:
                # 截图并根据裁剪参数获取截图结果
                while self.take_screenshot() is None:
                    continue
            # 根据查找类型执行不同的查找策略
            if find_type in ['image', 'text']:
                center = None
                if find_type in ['image']:
                    # 使用图像查找方法查找元素
                    center = self.find_image_element(target, threshold, model=model, my_crop=my_crop, addtional_stack=addtional_stack)
                elif find_type == 'text':
                    # 使用文本查找方法查找元素
                    center = self.find_text_element(target, my_crop, addtional_stack=addtional_stack)
                if center:
                    return center
            elif find_type in ['feature']:
                return self.find_feature_element(target, my_crop, addtional_stack=addtional_stack)
            elif find_type in ['image_with_multiple_targets']:
                # 使用多目标图像查找方法查找元素
                return self.find_image_with_multiple_targets(target, threshold, addtional_stack=addtional_stack)
            else:
                raise ValueError("错误的类型")

            if i < max_retries - 1:
                time.sleep(1)  # 在重试前等待一定时间
        return None

    def find_image_with_multiple_targets(self, target, threshold, addtional_stack) -> List:
        """
        在当前截图中查找多个目标图像的位置
        """
        try:
            template = ImageUtils.load_image(target)
            if "assets" in target:
                bbox = ImageUtils.get_bbox(template)
                template = ImageUtils.crop(template, bbox)
            if template is None:
                raise ValueError("读取图片失败")
            screenshot = np.array(self.screenshot)
            matches = ImageUtils.match_template_with_multiple_targets(screenshot, template, threshold)
            if len(matches) == 0:
                return []
            else:
                log.debug(f"找到{len(matches)}个目标：{matches}", stacklevel=addtional_stack + 3)
                return matches
        except Exception as e:
            log.error(f"寻找图片出错:{e}")
            return []

    def find_str_in_text(self, target, ocr_dict):
        """
        返回目标文本的坐标
        """
        for text in ocr_dict.keys():
            if target.lower() in text.lower():
                log.debug(f"识别到目标：{text},坐标为：{ocr_dict[text]}")
                return ocr_dict[text]
        return False

    def find_text_element(self, target, my_crop=None, all_text=False, only_text=False, addtional_stack=0):
        """
        寻找文本元素所在的坐标位置
        """
        if my_crop is not None:
            # 根据my_crop（为左上与右下四个坐标），截取self.screenshot的部分区域进行ocr
            cropped_image = self.screenshot.crop(my_crop)
            ocr_result = ocr.run(cropped_image)
        else:
            ocr_result = ocr.run(self.screenshot)
        if ocr_result.txts:
            ocr_text_list = [ocr_result.txts[i] for i in range(len(ocr_result.txts))]
            if only_text:
                return ocr_text_list
            ocr_position_list = []

            for box in ocr_result.boxes:
                x = (box[0][0] + box[2][0]) / 2
                y = (box[0][1] + box[2][1]) / 2
                ocr_position_list.append([x, y])

            ocr_dict = {text: position for text, position in zip(ocr_text_list, ocr_position_list)}
            log.debug(f"识别到文本及其坐标：{ocr_dict}", stacklevel=addtional_stack + 3)
        else:
            ocr_dict = {}
        if ocr_dict == {}:
            return False
        if isinstance(target, str):
            return self.find_str_in_text(target, ocr_dict)
        elif isinstance(target, list):
            if all_text:
                for key in target:
                    if self.find_str_in_text(str(key), ocr_dict) is False:
                        return False
                return True
            for key in target:
                if self.find_str_in_text(str(key), ocr_dict):
                    return self.find_str_in_text(str(key), ocr_dict)
            return False
        elif isinstance(target, dict):
            for key, value in target.items():
                if self.find_str_in_text(str(key), ocr_dict):
                    return value, str(key)
            return None

    def get_text_from_screenshot(self, my_crop=None):
        """
        从屏幕截图中提取文字
        """
        if my_crop is not None:
            # 根据my_crop（为左上与右下四个坐标），截取self.screenshot的部分区域进行ocr
            cropped_image = self.screenshot.crop(my_crop)
            ocr_result = ocr.run(cropped_image)
        else:
            ocr_result = ocr.run(self.screenshot)
        if ocr_result.txts:
            ocr_text_list = [ocr_result.txts[i] for i in range(len(ocr_result.txts))]
        else:
            ocr_text_list = []
        
        return ocr_text_list

    def find_feature_element(self, target, pic_crop=None, min_matches=8, addtional_stack=0):
        """
        寻找特征元素所在的坐标位置
        """
        try:
            template = ImageUtils.load_image(target, resize=False)
            screenshot = np.array(self.screenshot)
            if cfg.set_win_size < 1440:
                screenshot = cv2.resize(screenshot, None, fx=1440 / cfg.set_win_size, fy=1440 / cfg.set_win_size,
                                        interpolation=cv2.INTER_AREA)
            elif cfg.set_win_size > 1440:
                screenshot = cv2.resize(screenshot, None, fx=cfg.set_win_size / 1440, fy=cfg.set_win_size / 1440,
                                        interpolation=cv2.INTER_AREA)
            if pic_crop:
                if cfg.set_win_size < 1440:
                    pic_crop = [int(i * 1440 / cfg.set_win_size) for i in pic_crop]
                elif cfg.set_win_size > 1440:
                    pic_crop = [int(i * cfg.set_win_size / 1440) for i in pic_crop]
                screenshot = ImageUtils.crop(screenshot, pic_crop)
            result, num_matches = ImageUtils.feature_matching(template, screenshot, min_matches)
            log.debug(
                f"匹配目标特征图片：{target.replace('./assets/images/', '')}结果{result}, 找到 {num_matches} 个匹配点",
                stacklevel=addtional_stack + 3,
            )
            return result
        except Exception as e:
            error_message = str(e)
            if "cv::flann" in error_message:
                pass
            else:
                log.error(f"匹配图片特征失败:{e}")
            return None

    def clear_img_cache(self) -> None:
        """清除图片缓存"""
        self.img_cache.clear()
        gc.collect()  # 强制垃圾回收，清理内存
        log.debug("图片缓存已清除", stacklevel=2)

    def find_image_element(self, target, threshold, cacheable=True, model='clam', my_crop=None, addtional_stack=0):
        """
        在当前截图中查找目标图像的位置
        """
        try:
            if cacheable and target in self.img_cache:
                bbox = self.img_cache[target]['bbox']
                template = self.img_cache[target]['template']
            else:
                template = ImageUtils.load_image(target)
                if "assets" in target:
                    bbox = ImageUtils.get_bbox(template)
                    template = ImageUtils.crop(template, bbox)
                else:
                    bbox = None
                if cacheable:
                    self.img_cache[target] = {'bbox': bbox, 'template': template}
            screenshot = np.array(self.screenshot)
            if my_crop:
                screenshot = ImageUtils.crop(screenshot, my_crop)
            center, matchVal = ImageUtils.match_template(screenshot, template, bbox, model)  # 匹配模板
            log.debug(
                f"目标图片：{target.replace('./assets/images/', '')}, 相似度：{matchVal:.2f}, "
                f"目标位置：{center}",
                stacklevel=addtional_stack + 3,
            )
            if isinstance(matchVal, (int, float)) and not math.isinf(matchVal) and matchVal >= threshold:
                return center
        except Exception as e:
            log.error(f"寻找图片失败:{e}")
        return None

    def get_screenshot_crop(self, crop):
        """
        获取指定区域的彩色截图
        """
        self.take_screenshot(False)
        screenshot = np.array(self.screenshot)
        screenshot = screenshot[:, :, ::-1]
        screenshot = ImageUtils.crop(screenshot, crop)
        return screenshot
