import os
import socket
import sys
import threading

# 尽早清除 SSLKEYLOGFILE，避免 OpenSSL 在建立 HTTPS 连接时因跨 CRT 边界崩溃。
# 该变量通常由调试代理（如 Fiddler/Charles/Wireshark）设置，Python 内嵌的 OpenSSL
# 在 Windows 上不提供 OPENSSL_Applink 符号，一试写文件就会抛错退出。
# 此处仅清除当前进程的环境变量，不影响系统设置和其他进程。
_ORIG_SSLKEYLOGFILE = os.environ.pop("SSLKEYLOGFILE", None)

# 将当前工作目录设置为程序所在的目录，确保无论从哪里执行，其工作目录都正确设置为程序本身的位置，避免路径错误。
os.chdir(
    os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))
)
# 解决 Windows DPI 缩放问题
from ctypes import c_void_p, windll

try:
    # 1. 尝试 Win10 1703+ 的最强方案 (Per Monitor V2)
    # -4 对应 DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2
    windll.user32.SetProcessDpiAwarenessContext(c_void_p(-4))
except (AttributeError, OSError):
    try:
        # 2. 尝试 Win8.1+ 的方案 (Per Monitor)
        # 2 对应 PROCESS_PER_MONITOR_DPI_AWARE
        windll.shcore.SetProcessDpiAwareness(2)
    except (AttributeError, OSError):
        try:
            # 3. 最后的兜底方案 (Win7/Vista)
            windll.user32.SetProcessDPIAware()
        except Exception:
            pass

from app.language_manager import LanguageManager
from app.my_app import MainWindow
from module.config import cfg
from module.logger import log


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

QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
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
    if _ORIG_SSLKEYLOGFILE is not None:
        log.warning(f"检测到冲突的环境变量 SSLKEYLOGFILE={_ORIG_SSLKEYLOGFILE}，"
                     f"已在进程内清除，避免 OpenSSL 崩溃")

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
        threading.Thread(target=start_socket_server, args=(APP_PORT, signaler), daemon=True).start()
    except OSError:
        # 如果走到这说明刚才的 bind 突然成功了但又瞬间失败，通常直接退出即可
        sys.exit(1)

    QTimer.singleShot(50, lambda: lang_manager.set_language(lang))

    sys.exit(app.exec())
