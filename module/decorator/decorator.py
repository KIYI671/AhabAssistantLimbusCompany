import time

from module.logger import log
from module.my_error.my_error import userStopError


# 一个任务开始与结束的日志，并记录耗时
def begin_and_finish_time_log(task_name, calculate_time=True):
    def decorator(func):
        def wrapper(*args, **kw):
            msg = "开始执行 " + task_name
            log.INFO(msg)

            # 计时开始
            start_time = time.time()

            # 真正函数
            func(*args, **kw)

            # 计时结束
            end_time = time.time()
            elapsed_time = end_time - start_time

            msg = "结束执行 " + task_name
            log.INFO(msg)

            if calculate_time:
                # 将总秒数转换为小时、分钟和秒
                hours, remainder = divmod(elapsed_time, 3600)
                minutes, seconds = divmod(remainder, 60)
                time_string = f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"

                time_msg = msg + " 耗时:" + time_string
                log.DEBUG(time_msg)

            return elapsed_time

        return wrapper

    return decorator


# 检查globalVar.exitCode符合条件结束该线程
def check_and_exit(signal):
    def decorator(func):
        def wrapper(*args, **kw):
            signal.connect(lambda: raise_exception())

            # 真正函数
            func(*args, **kw)

        return wrapper

    return decorator


def raise_exception():
    raise userStopError("用户主动终止程序")
