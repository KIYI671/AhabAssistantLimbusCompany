import atexit
import io
import os.path

import Image

from module.ocr.PPOCR_api import GetOcrApi


class OCR:
    my_argument = {"config_path": "models/config_chinese.txt"}
    def __init__(self,exe_path,logger):
        self.exe_path=exe_path
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
            self.ocr=None

    def run(self,image):
        """执行OCR识别，支持Image对象、文件路径和np.ndarray对象"""
        self.init_ocr()
        try:
            if not isinstance(image, Image.Image):
                if isinstance(image,str):
                    image = Image.open(os.path.abspath(image))
                else: # 默认为 np.ndarray，避免需要import numpy
                    image = Image.fromarray(image)
            image_stream =io.BytesIO()
            image.save(image_stream, format='PNG')
            image_bytes =image_stream.getvalue()
            original_dist =self.ocr.runBytes(image_bytes)

            self.log_results(original_dist)
            return original_dist
        except Exception as e:
            self.logger.ERROR(e)
            return "{}"

    def log_results(self,modified_dist):
        """记录OCR识别记录"""
        if "data" in modified_dist and "text" in modified_dist["data"][0]:
            print_list = [item["text"] for item in modified_dist["data"]]
            self.logger.DEBUG(f"OCR识别结果：{print_list}")
        else:
            self.logger.DEBUG(f"OCR识别结果：{modified_dist}")