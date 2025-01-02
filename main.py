import os
import sys

# 将当前工作目录设置为程序所在的目录，确保无论从哪里执行，其工作目录都正确设置为程序本身的位置，避免路径错误。
os.chdir(os.path.dirname(sys.executable) if getattr(sys, 'frozen', False)else os.path.dirname(os.path.abspath(__file__)))

# 获取管理员权限
import pyuac
if not pyuac.isUserAdmin():
    try:
        pyuac.runAsAdmin(False)
        sys.exit(0)
    except Exception:
        sys.exit(1)

from win32api import GetLastError
from win32event import CreateMutex

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication
from my_gui import MainWindow

# 启用 DPI 缩放
QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
QApplication.setAttribute(Qt.AA_DontCreateNativeWidgetSiblings)
QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)

if __name__ == "__main__":
    # 构建互斥锁
    mutex = CreateMutex(None, False, 'AALC.Running')
    # 获取最后一个Windows错误代码。如果在创建互斥量时发生了错误，这个错误代码将表示错误的原因
    last_error = GetLastError()
    # 检查互斥量是否创建成功，如果mutex为None或者last_error大于0，这意味着创建互斥量失败，或者另一个实例已经在运行
    if not mutex or last_error > 0:
        # 使用非零退出码表示错误
        sys.exit(1)

    app = QApplication(sys.argv)
    app.setAttribute(Qt.AA_DontCreateNativeWidgetSiblings)
    ui = MainWindow()
    sys.exit(app.exec_())
