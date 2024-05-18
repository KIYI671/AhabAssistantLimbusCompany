from my_error.my_error import userStopError
from my_log.my_log import my_log


# 一个任务开始与结束的日志
def begin_and_finish_log(task_name):
    def decorator(func):
        def wrapper(*args, **kw):
            msg = "开始执行 " + task_name
            my_log("info", msg)

            # 真正函数
            func(*args, **kw)

            msg = "结束执行 " + task_name
            my_log("info", msg)

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
