import atexit
import io
import os.path

import cv2
import numpy as np
from PIL import Image
from cv2 import createCLAHE

from module.ocr.PPOCR_api import GetOcrApi
from utils.singletonmeta import SingletonMeta


class OCR(metaclass=SingletonMeta):
    my_argument = {"config_path": "models/config_chinese.txt"}

    def __init__(self, exe_path, logger):
        self.exe_path = exe_path
        self.ocr = None
        self.logger = logger

    def init_ocr(self):
        if self.ocr is None:
            try:
                self.logger.DEBUG("开始初始化OCR...")
                self.ocr = GetOcrApi(self.exe_path, self.my_argument)
                self.logger.DEBUG("初始化OCR完成")
                atexit.register(self.exit_ocr)
            except Exception as e:
                self.logger.ERROR(f"初始化OCR失败：{e}")
                self.logger.ERROR("请尝试重新下载或解压")
                raise Exception("初始化OCR失败")

    def exit_ocr(self):
        if self.ocr is not None:
            self.ocr.exit()
            self.ocr = None
            self.logger.DEBUG("OCR已退出")

    def run(self, image):
        """执行OCR识别，支持Image对象、文件路径和np.ndarray对象"""
        self.init_ocr()
        try:
            if not isinstance(image, Image.Image):
                if isinstance(image, str):
                    image = open(os.path.abspath(image))
                else:  # 默认为 np.ndarray，避免需要import numpy
                    image = Image.fromarray(image)
            # 将 PIL Image 对象转换为 OpenCV 图片对象
            img_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            # 将 OpenCV 图片对象转换为灰度模式
            img_cv_gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
            # 自适应均衡化(均值化后更亮)
            clahe = createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            image = clahe.apply(img_cv_gray)
            image = Image.fromarray(image)
            image_stream = io.BytesIO()
            image.save(image_stream, format='PNG')
            image_bytes = image_stream.getvalue()
            original_dist = self.ocr.runBytes(image_bytes)

            self.log_results(original_dist)
            return original_dist
        except Exception as e:
            self.logger.ERROR(e)
            return "{}"

    def log_results(self, modified_dist):
        """记录OCR识别记录"""
        if "data" in modified_dist and "text" in modified_dist["data"][0]:
            print_list = [item["text"] for item in modified_dist["data"]]
            self.logger.DEBUG(f"OCR识别结果：{print_list}")
        else:
            self.logger.DEBUG(f"OCR识别结果：{modified_dist}")
