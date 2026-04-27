from typing import List

from module.logger import log
from utils.singletonmeta import SingletonMeta


class PathManager(metaclass=SingletonMeta):
    """管理图片搜索路径及 dark 路径淘汰状态。"""

    def __init__(self):
        self.active_paths: List[str] = []
        self.is_dark_eliminated = False

    @property
    def pic_path(self) -> List[str]:
        return self.active_paths

    def initialize_paths(self, language: str) -> None:
        """根据语言初始化图片路径。"""
        if language == "zh_cn":
            self.active_paths = [
                "dark/zh_cn",
                "dark/en",
                "dark/share",
                "default/zh_cn",
                "default/en",
                "default/share",
            ]
        else:
            self.active_paths = ["dark/en", "dark/share", "default/en", "default/share"]
        self.is_dark_eliminated = False

        log.debug(f"路径管理器初始化完成，语言: {language}, 路径: {self.active_paths}")

    def eliminate_dark_paths(self) -> bool:
        """淘汰所有 dark 路径。"""
        if self.is_dark_eliminated:
            return False

        new_active_paths = [path for path in self.active_paths if not path.startswith("dark/")]
        if new_active_paths == self.active_paths:
            return False

        self.active_paths = new_active_paths
        self.is_dark_eliminated = True
        log.debug(f"淘汰所有dark路径，当前路径: {self.active_paths}")
        return True

    @staticmethod
    def is_path_dark(path: str) -> bool:
        return path.startswith("dark/")


path_manager = PathManager()
