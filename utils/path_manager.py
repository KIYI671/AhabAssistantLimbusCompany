from typing import List

from utils.singletonmeta import SingletonMeta


class PathManager(metaclass=SingletonMeta):
    """管理图片搜索路径及 dark 路径淘汰状态。"""

    def __init__(self):
        self.all_paths: List[str] = []
        self.active_paths: List[str] = []
        self.dark_paths: List[str] = []
        self.is_dark_eliminated = False
        self.dynamic_optimization = True
        self._pic_path_reference: list[str] | None = None

    def initialize_paths(self, language: str, pic_path_ref=None, config=None) -> None:
        """根据语言初始化图片路径，并同步全局 pic_path。"""
        if language == "zh_cn":
            self.all_paths = ["zh_cn_dark", "en_dark", "share_dark", "zh_cn", "en", "share"]
        else:
            self.all_paths = ["en_dark", "share_dark", "en", "share"]

        self.active_paths = self.all_paths.copy()
        self.dark_paths = [path for path in self.all_paths if "_dark" in path]
        self.is_dark_eliminated = False

        if config and hasattr(config, "get_value"):
            self.dynamic_optimization = config.get_value("dynamic_path_optimization", True)
        else:
            self.dynamic_optimization = True

        if pic_path_ref is None:
            from utils import pic_path

            pic_path_ref = pic_path

        self._pic_path_reference = pic_path_ref
        self._sync_pic_path()

        self._get_log().info(
            f"路径管理器初始化完成，语言: {language}, 路径: {self.active_paths}, 动态优化: {self.dynamic_optimization}"
        )

    def eliminate_dark_paths(self) -> bool:
        """淘汰所有 dark 路径，并同步全局 pic_path。"""
        if self.is_dark_eliminated or not self.dynamic_optimization:
            return False

        new_active_paths = [path for path in self.active_paths if "_dark" not in path]
        if new_active_paths == self.active_paths:
            return False

        self.active_paths = new_active_paths
        self.is_dark_eliminated = True
        self._sync_pic_path()
        self._get_log().info(f"淘汰所有dark路径，当前路径: {self.active_paths}")
        return True

    def get_active_paths(self) -> List[str]:
        return self.active_paths.copy()

    @staticmethod
    def is_path_dark(path: str) -> bool:
        return "_dark" in path

    def get_dark_paths(self) -> List[str]:
        return self.dark_paths.copy()

    def ensure_language_priority(self, language: str) -> None:
        """调整默认语言路径优先级，同时保留其余路径的相对顺序。"""
        if not self.active_paths:
            return

        if language == "zh_cn":
            priority_paths = ["zh_cn", "en", "share"]
        else:
            priority_paths = ["en", "share"]

        sorted_paths = [path for path in priority_paths if path in self.active_paths]
        sorted_paths.extend(path for path in self.active_paths if path not in sorted_paths)

        if sorted_paths != self.active_paths:
            self.active_paths = sorted_paths
            self._sync_pic_path()
            self._get_log().debug(f"已调整语言优先级，当前路径: {self.active_paths}")

    def _sync_pic_path(self) -> None:
        if self._pic_path_reference is None:
            return
        self._pic_path_reference.clear()
        self._pic_path_reference.extend(self.active_paths)

    @staticmethod
    def _get_log():
        from module.logger import log

        return log


path_manager = PathManager()
