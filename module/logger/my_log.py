import logging
import os
import sys
from collections import deque
from copy import deepcopy
from pathlib import Path
from threading import Lock

import colorlog
from concurrent_log_handler import ConcurrentRotatingFileHandler
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication
from ruamel.yaml import YAML

from module import CONFIG_PATH, VERSION_PATH
from utils.singletonmeta import SingletonMeta


class TranslationFormatter(colorlog.ColoredFormatter):
    """自定义日志格式化器，用于日志消息国际化"""

    project_root = Path(sys._MEIPASS) if hasattr(sys, "_MEIPASS") else Path.cwd()

    def format(self, record):
        record.msg = QApplication.translate("Logger", str(record.msg))
        record.pathname = os.path.relpath(record.pathname, self.project_root)

        return super().format(record)


class UILogDispatcher(QObject):
    """线程安全的 UI 日志环形缓冲区，保存user日志并通过信号分发给 UI 组件"""

    new_lines = Signal(list)
    cleared = Signal()

    def __init__(self, max_lines: int = 10000):
        super().__init__()
        self._lock = Lock()
        self._buffer = deque(maxlen=max_lines)

    def snapshot(self) -> list[str]:
        with self._lock:
            return list(self._buffer)

    def append_line(self, line: str) -> None:
        if not line:
            return
        with self._lock:
            self._buffer.append(line)
        self.new_lines.emit([line])

    def clear(self) -> None:
        with self._lock:
            self._buffer.clear()

        self.cleared.emit()


ui_log_dispatcher = UILogDispatcher()


class UILogHandler(logging.Handler):
    """将日志写入 UI 日志缓冲区"""

    def __init__(self, dispatcher: UILogDispatcher):
        super().__init__(level=logging.INFO)
        self.dispatcher = dispatcher

    def emit(self, record):
        try:
            msg = self.format(record)
            self.dispatcher.append_line(msg)
        except Exception:
            self.handleError(record)


class SettingConcurrentRotatingFileHandler(ConcurrentRotatingFileHandler):
    """自动输出设置文件内容在日志开头"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.version = "未知"
        self.config = {}

    def __read_config(self):
        yaml = YAML()
        with open(VERSION_PATH, "r", encoding="utf-8") as f:
            version = f.read().strip()
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config_data: dict = yaml.load(f)
            if config_data is None:
                raise ValueError("配置文件内容为空或格式错误")
            config = config_data

        self.version = version
        self.config = config

    def do_open(self, mode: str | None = None):
        stream = super().do_open(mode)
        if stream is None:
            return stream
        if stream.tell() == 0:
            try:
                self.__read_config()
                msg = f"""新文件创建, 当前配置文件内容如下: 
AALC 版本: {self.version}, 配置文件版本: {self.config.get("config_version", "未知")}
游戏分辨率: {self.config.get("set_win_size")}, 截图间隔: {self.config.get("screenshot_interval")}, 鼠标间隔 {self.config.get("mouse_action_interval")}
详细内容: {self.config}"""
            except Exception as e:
                msg = f"新文件创建, 但读取配置文件内容时发生错误: {e}"
            stream.write(msg + "\n")
        return stream


class Logger(metaclass=SingletonMeta):
    def __init__(self):
        self.logger = logging.getLogger("AALC")
        self.logger.propagate = False  # 避免泄露到其他logger导致重复记录

        # 移除其它第三方库给root logger添加的StreamHandler，避免重复输出
        _root_logger = logging.getLogger()
        _root_handlers = _root_logger.handlers
        for handler in _root_handlers:
            if isinstance(handler, logging.StreamHandler):
                _root_logger.removeHandler(handler)

        if not self.logger.handlers:
            # 控制台输出
            console_handler = logging.StreamHandler()
            console_formatter = TranslationFormatter(
                "%(log_color)s[%(levelname)s] %(asctime)s [AALC] %(pathname)s:%(lineno)d: %(message)s",
                log_colors={
                    "DEBUG": "cyan",
                    "INFO": "green",
                    "WARNING": "yellow",
                    "ERROR": "red",
                    "CRITICAL": "red,bg_white",
                },
            )
            console_handler.setFormatter(console_formatter)
            console_handler.setLevel(logging.DEBUG)

            # 创建日志目录
            os.makedirs("./logs", exist_ok=True)

            # debug日志文件，按文件大小切割
            debug_file_handler = SettingConcurrentRotatingFileHandler(
                "./logs/debugLog.log",
                maxBytes=5 * 1024 * 1024,  # 每份 5 MB
                backupCount=10,  # 最多保留 10 份
                encoding="utf-8",
            )
            file_formatter = deepcopy(console_formatter)
            file_formatter.no_color = True  # 输出到文件时不要加颜色符号
            debug_file_handler.setFormatter(file_formatter)
            debug_file_handler.setLevel(logging.DEBUG)

            # 显示在 UI 窗口中的日志，写到 ring buffer，不落盘
            ui_log_formatter = TranslationFormatter(
                "%(asctime)s - %(message)s", "%H:%M:%S", no_color=True
            )

            ui_log_handler = UILogHandler(ui_log_dispatcher)
            ui_log_handler.setLevel(logging.INFO)
            ui_log_handler.setFormatter(ui_log_formatter)

            self.logger.setLevel(logging.DEBUG)
            self.logger.addHandler(console_handler)
            self.logger.addHandler(debug_file_handler)
            self.logger.addHandler(ui_log_handler)

    def get_logger(self) -> logging.Logger:
        return self.logger
