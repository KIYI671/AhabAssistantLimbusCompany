import logging
import os
import sys

from utils.singletonmeta import SingletonMeta

# 修复nb_log的输出bug
for _name in ('stdin', 'stdout', 'stderr'):
    if getattr(sys, _name) is None:
        setattr(sys, _name, open(os.devnull, 'r' if _name == 'stdin' else 'w', encoding='utf-8', errors='ignore'))

from nb_log import get_logger


class Logger(metaclass=SingletonMeta):
    # 记录debug及以上级别日志
    debug_logger = get_logger('debugLogger',
                              log_filename='debugLog.log',
                              log_level_int=10,
                              log_path='./logs')

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
                                log_path='./logs')

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
        pass

    def DEBUG(self, msg):
        self.debug_logger.debug(msg)

    def INFO(self, msg):
        self.debug_logger.info(msg)
        self.info_logger.info(msg)
        """now = datetime.now()
        formatted_time = now.strftime("%H:%M:%S")
        win_log_msg = f"{formatted_time} infoLogger INFO {msg}"""
        self.my_logger.info(msg)

    def WARNING(self, msg):
        self.debug_logger.warning(msg)
        self.info_logger.warning(msg)
        self.my_logger.info(msg)
        self.warning_logger.warning(msg)

    def ERROR(self, msg):
        self.debug_logger.error(msg)
        self.info_logger.error(msg)
        self.my_logger.info(msg)
        self.warning_logger.error(msg)

    def CRITICAL(self, msg):
        self.debug_logger.critical(msg)
        self.info_logger.critical(msg)
        self.my_logger.info(msg)
        self.warning_logger.critical(msg)
