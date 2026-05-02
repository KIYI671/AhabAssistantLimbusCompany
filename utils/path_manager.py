from typing import List

from module.logger import log
from utils.singletonmeta import SingletonMeta


class PathManager(metaclass=SingletonMeta):
    """管理图片搜索路径及 dark 路径淘汰状态。"""

    DEFAULT_ACTIVE_PATHS = [
        "dark/zh_cn",
        "dark/en",
        "dark/share",
        "default/zh_cn",
        "default/en",
        "default/share",
    ]

    def __init__(self):
        self.active_paths: List[str] = []
        self.is_dark_eliminated = False
        self.is_zh_cn_eliminated = False
        self.current_theme: str | None = None
        self.current_language: str | None = None

    @property
    def pic_path(self) -> List[str]:
        return self.active_paths

    def initialize_paths(self, reset_eliminations: bool = True) -> None:
        """初始化图片路径，不读取用户语言设置。"""
        if reset_eliminations:
            self.is_dark_eliminated = False
            self.is_zh_cn_eliminated = False
            self.current_theme = None
            self.current_language = None

        self.active_paths = self.DEFAULT_ACTIVE_PATHS.copy()
        if self.is_dark_eliminated:
            self.active_paths = [path for path in self.active_paths if not path.startswith("dark/")]
        if self.is_zh_cn_eliminated:
            self.active_paths = [path for path in self.active_paths if not path.endswith("/zh_cn")]

        log.info(f"路径管理器初始化完成，路径: {self.active_paths}")

    def set_theme(self, theme: str, log_stacklevel: int = 3) -> bool:
        """记录当前图片主题。"""
        if theme not in {"dark", "default"}:
            return False
        if self.current_theme == theme:
            return False

        previous_theme = self.current_theme or "未知"
        self.current_theme = theme
        log.info(f"图片主题由{previous_theme}识别为{theme}", stacklevel=log_stacklevel)
        return True

    def set_language(self, lang_code: str, log_stacklevel: int = 3) -> bool:
        """记录当前游戏语言。"""
        if lang_code not in {"zh_cn", "en"}:
            return False

        changed = self.current_language != lang_code
        previous_language = self.current_language or "未知"
        self.current_language = lang_code

        from module.config import cfg

        if cfg.language_in_game != lang_code:
            cfg.unsaved_set_value("language_in_game", lang_code, stacklevel=log_stacklevel)
            changed = True
        if changed:
            log.info(f"图片语言由{previous_language}识别为{lang_code}", stacklevel=log_stacklevel)
        return changed

    def eliminate_dark_paths(self) -> bool:
        """淘汰所有 dark 路径。"""
        if self.is_dark_eliminated:
            return False

        new_active_paths = [path for path in self.active_paths if not path.startswith("dark/")]
        if new_active_paths == self.active_paths:
            return False

        self.active_paths = new_active_paths
        self.is_dark_eliminated = True
        log.info(f"淘汰所有dark路径，当前路径: {self.active_paths}")
        return True

    def eliminate_zh_cn_paths(self) -> bool:
        """淘汰所有中文路径。"""
        if self.is_zh_cn_eliminated:
            return False

        new_active_paths = [path for path in self.active_paths if not path.endswith("/zh_cn")]
        if new_active_paths == self.active_paths:
            return False

        self.active_paths = new_active_paths
        self.is_zh_cn_eliminated = True
        from module.config import cfg

        if cfg.language_in_game != "en":
            cfg.unsaved_set_value("language_in_game", "en", stacklevel=3)
        self.current_language = "en"
        log.info(f"淘汰所有zh_cn路径，当前路径: {self.active_paths}")
        return True

    @staticmethod
    def is_path_dark(path: str) -> bool:
        return path.startswith("dark/")

    @staticmethod
    def is_path_default(path: str) -> bool:
        return path.startswith("default/")

    @staticmethod
    def is_path_zh_cn(path: str) -> bool:
        return path.endswith("/zh_cn")

    @staticmethod
    def is_path_en_or_share(path: str) -> bool:
        return path.endswith("/en") or path.endswith("/share")


path_manager = PathManager()
