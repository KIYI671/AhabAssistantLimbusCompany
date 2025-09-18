import os

import cpufeature

from module.logger import log
from module.ocr.ocr import OCR
from module.update.check_update import start_update_thread


class OCRInstaller:
    def __init__(self, log):
        self.logger = log
        self.ocr_name, self.ocr_path = self._determine_ocr()

    def _cpu_support_avx2(self):
        """
        判断CPU是否支持AVX2指令集
        """
        return cpufeature.CPUFeature["AVX2"]

    def _determine_ocr(self):
        if self._cpu_support_avx2():
            ocr_name = "PaddleOCR-json"
            ocr_path = r".\3rdparty\PaddleOCR-json_v1.4.1\PaddleOCR-json.exe"
            self.logger.debug(
                f"CPU 支持 AVX2 指令集，使用 {ocr_name} \nThe CPU supports the AVX2 instruction set, using {ocr_name}")
        else:
            ocr_name = "RapidOCR-json"
            ocr_path = r".\3rdparty\RapidOCR-json_v0.2.0\RapidOCR-json.exe"
            self.logger.info(
                f"CPU 不支持 AVX2 指令集，使用 {ocr_name} \nThe CPU does not support the AVX2 instruction set, use {ocr_name}")
        return ocr_name, ocr_path

    def check_again(self):
        self._determine_ocr()

    def check_and_install(self):
        if not os.path.exists(self.ocr_path):
            self.logger.WARNING(f"OCR 路径不存在: {self.ocr_path}")
            self.install_ocr()

    def install_ocr(self):
        RapidOCR_url = "https://github.com/hiroi-sora/RapidOCR-json/releases/download/v0.2.0/RapidOCR-json_v0.2.0.7z"
        self.logger.info("开始从Github源下载RapidOCR")
        start_update_thread(RapidOCR_url)


ocr_installer = OCRInstaller(log)
ocr_installer.check_and_install()
ocr = OCR(ocr_installer.ocr_path, log)
