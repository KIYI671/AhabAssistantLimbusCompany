import os
import socket
import sys
import threading

from app.language_manager import LanguageManager
from app.my_app import MainWindow
from module.config import cfg

# 将当前工作目录设置为程序所在的目录，确保无论从哪里执行，其工作目录都正确设置为程序本身的位置，避免路径错误。
os.chdir(
    os.path.dirname(sys.executable)
    if getattr(sys, "frozen", False)
    else os.path.dirname(os.path.abspath(__file__))
)

# 获取管理员权限
import pyuac

if not pyuac.isUserAdmin():
    try:
        pyuac.runAsAdmin(False)
        sys.exit(0)
    except Exception:
        sys.exit(1)

from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtWidgets import QApplication

QApplication.setHighDpiScaleFactorRoundingPolicy(
    Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
)
QApplication.setAttribute(Qt.AA_DontCreateNativeWidgetSiblings)


# 创建一个辅助类用于在主线程处理信号
class ArgumentSignaler(QObject):
    arguments_received = Signal(list)


def start_socket_server(port, signaler):
    """后台线程：监听新实例发来的参数"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", port))
        s.listen(5)
        while True:
            conn, addr = s.accept()
            with conn:
                data = conn.recv(1024).decode("utf-8")
                if data:
                    # 收到参数后通过信号发送给主线程处理
                    signaler.arguments_received.emit(data.split("|"))


def send_args_to_existing_instance(port, args):
    """尝试将参数发送给已存在的实例"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1.0)  # 设置 1 秒超时
            s.connect(("127.0.0.1", port))
            s.sendall("|".join(args).encode("utf-8"))
        return True
    except ConnectionRefusedError:
        return False
    except Exception:
        return False


if __name__ == "__main__":
    # 定义一个唯一的端口号（建议选择 1024-65535 之间的随机数）
    APP_PORT = 62333

    # 1. 尝试发送参数给已有实例
    if send_args_to_existing_instance(APP_PORT, sys.argv[1:]):
        sys.exit(0)

    # 2. 如果发送失败，说明是第一个实例，开始初始化
    if cfg.zoom_scale != 0:
        os.environ["QT_SCALE_FACTOR"] = str(cfg.zoom_scale / 100)

    lang_manager = LanguageManager()
    lang = lang_manager.init_language()

    app = QApplication(sys.argv)
    app.setAttribute(Qt.AA_DontCreateNativeWidgetSiblings)

    # 创建主窗口
    ui = MainWindow(sys.argv)

    # 3. 设置参数监听信号
    signaler = ArgumentSignaler()

    def handle_args(args):
        # 处理新参数的逻辑
        args.insert(0, "aalc")
        ui.command_start(args)
        ui.showNormal()
        ui.activateWindow()
        ui.raise_()
        # 如果需要，可以在这里调用 ui.open_file(args[0]) 等

    signaler.arguments_received.connect(handle_args)

    # 4. 在后台启动 Socket 服务器（非阻塞主线程）
    # 注意：这里需要捕获 bind 异常，防止极短时间内双击导致的竞争
    try:
        threading.Thread(
            target=start_socket_server, args=(APP_PORT, signaler), daemon=True
        ).start()
    except OSError:
        # 如果走到这说明刚才的 bind 突然成功了但又瞬间失败，通常直接退出即可
        sys.exit(1)

    QTimer.singleShot(50, lambda: lang_manager.set_language(lang))

    sys.exit(app.exec())
