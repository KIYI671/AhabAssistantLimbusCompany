from copy import deepcopy
import inspect
import logging
import colorlog
from concurrent_log_handler import ConcurrentRotatingFileHandler
import os
import re
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from utils.singletonmeta import SingletonMeta


class TranslationFormatter(colorlog.ColoredFormatter):
    """自定义日志格式化器，用于日志消息国际化"""

    project_root = Path(sys._MEIPASS) if hasattr(sys, "_MEIPASS") else Path.cwd()

    def format(self, record):
        record.msg = QApplication.translate("Logger", str(record.msg))
        record.pathname = os.path.relpath(record.pathname, self.project_root)

        return super().format(record)


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

            # debug日志文件，按文件大小切割
            debug_file_handler = ConcurrentRotatingFileHandler(
                "./logs/debugLog.log",
                maxBytes=5 * 1024 * 1024,  # 每份 5 MB
                backupCount=10,            # 最多保留 10 份
                encoding="utf-8",
            )
            file_formatter = deepcopy(console_formatter)
            file_formatter.no_color = True  # 输出到文件时不要加颜色符号
            debug_file_handler.setFormatter(file_formatter)
            debug_file_handler.setLevel(logging.DEBUG)

            # UI界面里的log显示，只记录INFO及以上级别
            user_log_handler = logging.FileHandler(
                filename="./logs/user.log", encoding="utf-8"
            )
            user_log_handler.setLevel(logging.INFO)
            user_log_handler.setFormatter(
                TranslationFormatter(
                    "%(asctime)s - %(message)s", "%H:%M:%S", no_color=True
                ),
            )

            self.logger.setLevel(logging.DEBUG)
            self.logger.addHandler(console_handler)
            self.logger.addHandler(debug_file_handler)
            self.logger.addHandler(user_log_handler)

    def get_logger(self) -> logging.Logger:
        return self.logger
