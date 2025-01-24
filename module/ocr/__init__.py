from module.logger import log
from module.ocr.ocr import OCR

# TODO: V0.2.0先不改变太多，之后再适配其他不支持AVX指令集的CPU

ocr_path = "./3rdparty/PaddleOCR-json_v1.4.1/PaddleOCR-json.exe"
ocr = OCR(ocr_path, log)
