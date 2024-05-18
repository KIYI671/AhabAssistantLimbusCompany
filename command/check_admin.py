import ctypes
import sys
from os import _exit

from command.error_box import show_error_box


def check_admin():
    if ctypes.windll.shell32.IsUserAnAdmin():
        return True
    else:
        if sys.platform.startswith("win32"):
            # 启动新的进程，要求用户通过UAC（用户账户控制）来获取管理员权限
            result = ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, __file__, None, 1)
            if result <= 32:
                return False
            else:
                return True
        else:
            show_error_box("该程序暂时仅支持在Windows系统中使用")
        # 退出当前进程
        _exit(0)
