import sys
from win32api import GetLastError
from win32event import CreateMutex
from command.check_admin import check_admin
from my_gui import mygui

if __name__ == "__main__":
    # 构建互斥锁
    mutex = CreateMutex(None, False, 'AALC.Running')
    # 获取最后一个Windows错误代码。如果在创建互斥量时发生了错误，这个错误代码将表示错误的原因
    last_error = GetLastError()
    # 检查互斥量是否创建成功，如果mutex为None或者last_error大于0，这意味着创建互斥量失败，或者另一个实例已经在运行
    if not mutex or last_error > 0:
        # 使用非零退出码表示错误
        sys.exit(1)

    check_admin()
    mygui()
