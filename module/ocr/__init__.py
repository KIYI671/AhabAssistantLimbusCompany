import os

import cpufeature

from module.config import cfg
from module.logger import log
from module.ocr.ocr import OCR
from module.update.check_update import start_update_thread


class OCRInstaller:
    def __init__(self,log):
        self.logger = log
        self.ocr_name,self.ocr_path = self._determine_ocr()

    def _cpu_support_avx2(self):
        """
        判断CPU是否支持AVX2指令集
        """
        return cpufeature.CPUFeature["AVX2"]

    def _determine_ocr(self):
        if self._cpu_support_avx2():
            ocr_name ="PaddleOCR-json"
            ocr_path = r".\3rdparty\PaddleOCR-json_v1.4.1\PaddleOCR-json.exe"
            self.logger.DEBUG(f"CPU 支持 AVX2 指令集，使用 {ocr_name} \nThe CPU supports the AVX2 instruction set, using {ocr_name}")
        else:
            ocr_name = "RapidOCR-json"
            ocr_path = r".\3rdparty\RapidOCR-json_v0.2.0\RapidOCR-json.exe"
            self.logger.INFO(f"CPU 不支持 AVX2 指令集，使用 {ocr_name} \nThe CPU does not support the AVX2 instruction set, use {ocr_name}")
        return ocr_name, ocr_path

    def check_and_install(self):
        if not os.path.exists(self.ocr_path):
            self.logger.WARNING(f"OCR 路径不存在: {self.ocr_path}")
            self.install_ocr()

    def install_ocr(self):
        RapidOCR_url = "https://github.com/hiroi-sora/RapidOCR-json/releases/download/v0.2.0/RapidOCR-json_v0.2.0.7z"
        start_update_thread(RapidOCR_url)
        if cfg.language == 'zh_cn':
            self.logger.INFO(f"请在下载 {self.ocr_name} 完成后，将下载的文件解压并转移到 “3rdparty” 文件夹中，然后重启程序。")
        else:
            self.logger.INFO(f"After downloading {self.ocr_name}, please unzip the downloaded file and transfer it to the “3rdparty” folder, then restart the program.")

ocr_installer = OCRInstaller(log)
ocr_installer.check_and_install()
ocr = OCR(ocr_installer.ocr_path, log)
