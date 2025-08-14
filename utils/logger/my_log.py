import logging
import os
import sys
import inspect
import re
from pathlib import Path

from PyQt5.QtWidgets import QApplication
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

        self._decorate_logger()

    def _decorate_logger(self):
        """ 装饰日志记录器
        \n 使用闭包装饰器来动态捕获传入信息, 从而实现翻译
        \n 且能够支持传入参数的格式化, (format方法)
        例子:
        log.INFO("这是一个{}日志", "测试") >> 这是一个测试日志
        log.INFO("这是一个{text}日志", text = "测试") >> 这是一个测试日志
        第一个参数, 也就是msg参数, 会在info日志里被翻译, 如果被QT_TRANSLATE_NOOP标记 (content = "Logger")
        但是在debug日志里不会被翻译, 却会被format方法格式化
        """
        # 定义一个闭包装饰器来捕获原始方法, 并设置输出的字符串是否翻译
        def decorator_log(func, tr=False):

            # 使用闭包捕获原始方法
            def wrapped_log(level, msg, args, exc_info=None, extra=None, stack_info=False,
             stacklevel=1, **kwargs):
                if tr:
                    translated_msg = self._translate_logger_message(msg)
                else:
                    translated_msg = msg
                translated_msg = translated_msg.format(*args, **kwargs) if args or kwargs else translated_msg
                return func(level, translated_msg, args=(), exc_info=exc_info, extra=extra, stack_info=stack_info,
             stacklevel=stacklevel) # 原函数 // format方法来格式化多好(( 居然只支持类printf的
        
            return wrapped_log # 新的_log函数
        self.debug_logger._log = decorator_log(self.debug_logger._log)
        self.my_logger._log = decorator_log(self.my_logger._log, tr=True)
        self.info_logger._log = decorator_log(self.info_logger._log, tr=True)
        self.warning_logger._log = decorator_log(self.warning_logger._log)

    def _detect_project_root(self):

        # 打包环境下, 获取项目根目录
        if hasattr(sys, '_MEIPASS'):
            Logger._project_root = Path(sys._MEIPASS)
            return

        # 使用当前工作目录
        Logger._project_root = Path.cwd()


    def _translate_logger_message(self, msg: str) -> str:
        """
        翻译日志消息
        :param msg: 日志消息
        :return: 翻译后的日志消息
        """

        return QApplication.translate("Logger", msg)

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

    def DEBUG(self, msg, *args, **kwargs):
        path, line = self._get_caller_info()
        extra = {'caller_path': path, 'caller_line': line}
        self.debug_logger.debug(msg, extra=extra, *args, **kwargs)

    def INFO(self, msg, *args, **kwargs):
        path, line = self._get_caller_info()
        extra = {'caller_path': path, 'caller_line': line}

        self.debug_logger.info(msg, extra=extra, *args, **kwargs)
        self.info_logger.info(msg, extra=extra, *args, **kwargs)
        self.my_logger.info(msg, *args, **kwargs)

    def WARNING(self, msg, *args, **kwargs):
        path, line = self._get_caller_info()
        extra = {'caller_path': path, 'caller_line': line}

        self.debug_logger.warning(msg, extra=extra, *args, **kwargs)
        self.info_logger.warning(msg, extra=extra, *args, **kwargs)
        self.warning_logger.warning(msg, extra=extra, *args, **kwargs)
        self.my_logger.info(msg, *args, **kwargs)

    def ERROR(self, msg, *args, **kwargs):
        path, line = self._get_caller_info()
        extra = {'caller_path': path, 'caller_line': line}

        self.debug_logger.error(msg, extra=extra, *args, **kwargs)
        self.info_logger.error(msg, extra=extra, *args, **kwargs)
        self.warning_logger.error(msg, extra=extra, *args, **kwargs)
        self.my_logger.info(msg, *args, **kwargs)

    def CRITICAL(self, msg, *args, **kwargs):
        path, line = self._get_caller_info()
        extra = {'caller_path': path, 'caller_line': line}

        self.debug_logger.critical(msg, extra=extra, *args, **kwargs)
        self.info_logger.critical(msg, extra=extra, *args, **kwargs)
        self.warning_logger.critical(msg, extra=extra, *args, **kwargs)
        self.my_logger.info(msg, *args, **kwargs)
