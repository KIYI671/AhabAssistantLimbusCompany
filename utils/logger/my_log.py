import logging
import os
import sys
import inspect
import re
from pathlib import Path

from utils.singletonmeta import SingletonMeta

# 修复nb_log的输出bug
for _name in ('stdin', 'stdout', 'stderr'):
    if getattr(sys, _name) is None:
        setattr(sys, _name, open(os.devnull, 'r' if _name == 'stdin' else 'w', encoding='utf-8', errors='ignore'))

from nb_log import get_logger


class Logger(metaclass=SingletonMeta):
    _project_root = None

    # 公共的格式化字符串
    _common_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - "%(caller_path)s:%(caller_line)d" - %(message)s',
        "%Y-%m-%d %H:%M:%S"
    )

    # 记录debug及以上级别日志
    debug_logger = get_logger('debugLogger',
                              log_filename='debugLog.log',
                              log_level_int=10,
                              log_path='./logs',
                              formatter_template=_common_formatter)

    # 记录info及以上级别日志
    info_logger = get_logger('infoLogger',
                             log_filename='infoLog.log',
                             is_add_stream_handler=False,
                             log_level_int=20,
                             log_path='./logs',
                             formatter_template=logging.Formatter(
                                 '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                                 "%Y-%m-%d %H:%M:%S"))
    # 记录warning及以上级别日志
    warning_logger = get_logger('warningLogger',
                                log_filename='warningLog.log',
                                is_add_stream_handler=False,
                                log_level_int=30,
                                log_path='./logs',
                                formatter_template=_common_formatter)

    # 用于输出目前的运行情况
    my_logger = get_logger('myLogger',
                           log_filename='myLog.log',
                           is_add_stream_handler=False,
                           log_level_int=20,
                           log_path='./logs',
                           log_file_handler_type=3,
                           formatter_template=logging.Formatter(
                               '%(asctime)s - %(message)s', "%H:%M:%S"))

    def __init__(self):
        if Logger._project_root is None:
            self._detect_project_root()

        # 装饰器正则表
        self._decorator_patterns = [
            re.compile(r'.*[\\/]decorator[\\/].*\.py$', re.IGNORECASE),  # 匹配所有 decorator 文件夹下的py文件
        ]

    def _detect_project_root(self):

        # 打包环境下, 获取项目根目录
        if hasattr(sys, '_MEIPASS'):
            Logger._project_root = Path(sys._MEIPASS)
            return

        # 使用当前工作目录
        Logger._project_root = Path.cwd()

    def _get_caller_info(self) -> tuple[str, int]:
        """
        获取堆栈内最近的且非log类的调用者信息 (自带过滤器)
        \n目前过滤了decorator目录

        Returns:
            tuple[str,int]: (文件路径, 行号)
        """
        stack = inspect.stack()

        # 寻找第一个非装饰器、非Logger的栈帧
        for frame_info in stack:
            frame = frame_info.frame
            filename = frame_info.filename

            # 跳过当前类的方法
            if frame_info.function in ['_get_caller_info', '_short_get_caller_info', 'DEBUG', 'INFO', 'WARNING',
                                       'ERROR', 'CRITICAL']:
                continue

            # 跳过装饰器文件
            if any(pattern.match(filename) for pattern in self._decorator_patterns):
                continue

            # 获取文件绝对路径
            abs_path = Path(filename).resolve()

            try:
                # 转换为相对路径
                rel_path = abs_path.relative_to(self._project_root)
                # 转换为Windows风格的路径字符串
                rel_path_str = str(rel_path).replace('/', '\\')
                return rel_path_str, frame_info.lineno
            except ValueError:
                # 如果不在项目根目录下，返回绝对路径
                return str(abs_path), frame_info.lineno

        # 如果找不到合适的栈帧，返回未知
        return "unknown", 0

    def DEBUG(self, msg):
        path, line = self._get_caller_info()
        extra = {'caller_path': path, 'caller_line': line}
        self.debug_logger.debug(msg, extra=extra)

    def INFO(self, msg):
        path, line = self._get_caller_info()
        extra = {'caller_path': path, 'caller_line': line}

        self.debug_logger.info(msg, extra=extra)
        self.info_logger.info(msg, extra=extra)
        self.my_logger.info(msg)

    def WARNING(self, msg):
        path, line = self._get_caller_info()
        extra = {'caller_path': path, 'caller_line': line}

        self.debug_logger.warning(msg, extra=extra)
        self.info_logger.warning(msg, extra=extra)
        self.warning_logger.warning(msg, extra=extra)
        self.my_logger.info(msg)

    def ERROR(self, msg):
        path, line = self._get_caller_info()
        extra = {'caller_path': path, 'caller_line': line}

        self.debug_logger.error(msg, extra=extra)
        self.info_logger.error(msg, extra=extra)
        self.warning_logger.error(msg, extra=extra)
        self.my_logger.info(msg)

    def CRITICAL(self, msg):
        path, line = self._get_caller_info()
        extra = {'caller_path': path, 'caller_line': line}

        self.debug_logger.critical(msg, extra=extra)
        self.info_logger.critical(msg, extra=extra)
        self.warning_logger.critical(msg, extra=extra)
        self.my_logger.info(msg)
