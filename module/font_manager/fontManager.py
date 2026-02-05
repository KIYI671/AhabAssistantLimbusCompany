import os
from typing import TypedDict

from PySide6.QtGui import QFontDatabase
from qfluentwidgets import qconfig

from module.logger import log
from utils.singletonmeta import SingletonMeta


class Font(TypedDict):
    families: list[str]
    font_id: int
    font_path: str


class FontManager(metaclass=SingletonMeta):
    def __init__(self):
        self.loaded_fonts: dict[str, Font] = {}
        """字体路径: 字体信息"""

    def unload_font(self, font_path: str) -> None:
        """卸载字体"""
        font_path = os.path.abspath(font_path)
        if font_path in self.loaded_fonts:
            font_id = self.loaded_fonts.pop(font_path)["font_id"]
            QFontDatabase.removeApplicationFont(font_id)
        else:
            log.warning(f"尝试卸载未加载的字体: {font_path}", stacklevel=2)

    def load_font(self, font_path: str) -> list[str]:
        """加载字体并返回字体族列表"""
        font_path = os.path.abspath(font_path)
        if font_path in self.loaded_fonts:
            return self.loaded_fonts[font_path]["families"]

        font_id = QFontDatabase.addApplicationFont(font_path)
        if font_id < 0:
            log.warning(f"无法加载字体文件: {font_path}", stacklevel=2)
            return qconfig.fontFamilies.value

        families = QFontDatabase.applicationFontFamilies(font_id)
        if not families:
            log.warning(f"无法获取字体族名称: {font_path}", stacklevel=2)
            return qconfig.fontFamilies.value
        self.loaded_fonts[font_path] = Font(
            families=families, font_id=font_id, font_path=font_path
        )
        return families
