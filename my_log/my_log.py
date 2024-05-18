import logging
from datetime import datetime

from nb_log import get_logger

from my_error.my_error import logTypeError

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
                           '%(asctime)s - %(message)s',"%H:%M:%S"))


def my_log(log_type, msg):
    if log_type == "debug":
        debug_logger.debug(msg)
    elif log_type == "info":
        debug_logger.info(msg)
        info_logger.info(msg)
        """now = datetime.now()
        formatted_time = now.strftime("%H:%M:%S")
        win_log_msg = f"{formatted_time} infoLogger INFO {msg}"""
        my_logger.info(msg)
    elif log_type == "warning":
        debug_logger.warning(msg)
        info_logger.warning(msg)
        my_logger.info(msg)
        warning_logger.warning(msg)
    elif log_type == "error":
        debug_logger.error(msg)
        info_logger.error(msg)
        my_logger.info(msg)
        warning_logger.error(msg)
    elif log_type == "critical":
        debug_logger.critical(msg)
        info_logger.critical(msg)
        my_logger.info(msg)
        warning_logger.critical(msg)
    else:
        raise logTypeError("出现未知类型日志，请及时检查代码")
