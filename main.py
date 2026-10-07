import os
import socket
import sys
import threading

# 尽早清除 SSLKEYLOGFILE，避免 OpenSSL 在建立 HTTPS 连接时因跨 CRT 边界崩溃。
# 该变量通常由调试代理（如 Fiddler/Charles/Wireshark）设置，Python 内嵌的 OpenSSL
# 在 Windows 上不提供 OPENSSL_Applink 符号，一试写文件就会抛错退出。
# 此处仅清除当前进程的环境变量，不影响系统设置和其他进程。
_ORIG_SSLKEYLOGFILE = os.environ.pop("SSLKEYLOGFILE", None)


def _abort_startup(title: str, message: str) -> None:
    """启动阶段的致命错误：此时日志系统还没就绪，直接弹窗说明原因后退出。"""
    sys.stderr.write(f"{title}: {message}\n")
    from PySide6.QtWidgets import QApplication, QMessageBox

    QApplication([])
    QMessageBox.critical(None, title, message)
    sys.exit(1)


# 程序所在目录：打包后是 exe 所在目录，源码运行是仓库根目录
APP_DIR = (
    os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))
)

# macOS 的 .app 从「访达」启动时只继承 launchd 的最小 PATH（/usr/bin:/bin:/usr/sbin:/sbin），
# 找不到 Homebrew 安装的 adb 等外部命令，这里补上常见的安装位置。
if sys.platform == "darwin":
    for _bin_dir in ("/opt/homebrew/bin", "/usr/local/bin"):
        if os.path.isdir(_bin_dir) and _bin_dir not in os.environ.get("PATH", "").split(os.pathsep):
            os.environ["PATH"] = _bin_dir + os.pathsep + os.environ.get("PATH", "")

# 将当前工作目录设置为程序的数据目录，确保相对路径（配置、日志、图片资源）都指向可写位置。
# macOS 打包版的数据目录在 ~/Library/Application Support/AALC，程序目录只当只读资源来源，
# 详见 utils/app_data_dir.py。
WORK_DIR = APP_DIR
if sys.platform == "darwin" and getattr(sys, "frozen", False):
    from utils.app_data_dir import prepare_macos_data_dir

    try:
        WORK_DIR = prepare_macos_data_dir(APP_DIR)
    except OSError as error:
        _abort_startup(
            "AALC 启动失败",
            f"无法准备数据目录：\n{error}\n\n请检查磁盘剩余空间，以及「访达 → 前往文件夹 → "
            "~/Library/Application Support」的写入权限。",
        )
os.chdir(WORK_DIR)

# 解决 Windows DPI 缩放问题（仅 Windows；macOS 的 HiDPI 由系统与 Qt 自动处理）
if sys.platform == "win32":
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

# 先配好日志（给 "AALC" logger 挂 handler），再 import 会在 import 期就打日志的 app/config 模块，
# 否则那些启动日志会丢。
from module.logger import log
from module.logger.my_log import Logger

Logger()

from app.language_manager import LanguageManager
from app.my_app import MainWindow
from module.config import cfg

# 获取管理员权限（仅 Windows；macOS 桌面应用通常不需要提权，pyuac 依赖 pywin32 也无法在 mac 导入）
if sys.platform == "win32":
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
