"""AALC 独立更新器。

参考 MAA.Updater（MaaAssistantArknights）的设计，把更新做成完全自动的静默流程：

- 无终端窗口：随 ``updater.spec`` 以无窗口（console=False）方式打包，全部输出
  重定向到 ``update_temp/updater.log``，任何子进程都以无窗口标记启动；
- 无人工确认：不含任何 ``input()`` 等待，失败自动重试，最终失败通过原生
  MessageBox 提示（而非终端），并尽量恢复旧版本可用后自动重启 AALC；
- 可视进度：用 Win32 原生小窗口展示阶段与进度（``--no-progress-ui`` 可关闭），
  参考 MAA.Updater 的进度窗口；
- 平滑交接：支持 ``--parent-pid`` 等待主程序优雅退出（限时内不退出再强制清理），
  避免更新器主动杀掉正在保存配置的主程序。

命令行兼容形式：
    AALC Updater.exe <file_name>
    AALC Updater.exe --apply-update <file_name>
    任意位置可附加 --parent-pid <pid> / --no-progress-ui
"""

import contextlib
import ctypes
import json
import os
import shutil
import subprocess
import sys
import threading
import time
import traceback
from pathlib import Path, PurePosixPath

import psutil

# Windows 进程创建标记：统一无窗口启动，避免任何控制台闪现
_CREATE_NO_WINDOW = 0x08000000
_DETACHED_PROCESS = 0x00000008
_CREATE_NEW_PROCESS_GROUP = 0x00000200

_PARENT_EXIT_WAIT_SECONDS = 15
_EXTRACT_MAX_ATTEMPTS = 3
_FS_OP_MAX_ATTEMPTS = 4
_FS_OP_RETRY_DELAY_SECONDS = 0.5
_LOG_ROTATE_SIZE = 512 * 1024

TEMP_DIR_NAME = "update_temp"
LOG_FILE_NAME = "updater.log"


class UpdateManifestError(ValueError):
    """更新清单包含不能安全应用的内容。"""


class UpdatePayloadError(RuntimeError):
    """更新包无法解压或缺失关键内容。"""


# ---------------------------------------------------------------------------
# 日志与错误提示
# ---------------------------------------------------------------------------

_LOG_STREAM = None


def _setup_logging():
    """把 stdout/stderr 重定向到日志文件（无窗口模式下可追溯更新全过程）。"""
    global _LOG_STREAM
    log_dir = os.path.abspath(f"./{TEMP_DIR_NAME}")
    log_path = os.path.join(log_dir, LOG_FILE_NAME)
    try:
        os.makedirs(log_dir, exist_ok=True)
        try:
            # 简单轮转：超过阈值时把旧日志挪到 .1，避免无限膨胀
            if os.path.exists(log_path) and os.path.getsize(log_path) > _LOG_ROTATE_SIZE:
                backup_path = f"{log_path}.1"
                with contextlib.suppress(OSError):
                    os.remove(backup_path)
                os.replace(log_path, backup_path)
        except OSError:
            pass
        _LOG_STREAM = open(log_path, "a", encoding="utf-8", buffering=1, errors="replace")
    except OSError:
        _LOG_STREAM = open(os.devnull, "w", encoding="utf-8")
        log_path = None
    sys.stdout = _LOG_STREAM
    sys.stderr = _LOG_STREAM
    return log_path


def _log(message):
    """写一行带时间戳的更新日志；日志不可用时静默丢弃。"""
    if _LOG_STREAM is None:
        return
    try:
        _LOG_STREAM.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}\n")
    except OSError:
        pass


def show_error_dialog(title, text):
    """用原生 MessageBox 提示致命错误（无控制台场景下的兜底交互）。"""
    if os.name != "nt":
        return
    try:
        # MB_ICONERROR | MB_SETFOREGROUND：确保前置显示
        ctypes.windll.user32.MessageBoxW(None, ctypes.c_wchar_p(text), ctypes.c_wchar_p(title), 0x00000010 | 0x00010000)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# 进度窗口
# ---------------------------------------------------------------------------

class _NullProgress:
    """进度接口的空实现（进度窗被禁用或不可用时使用）。"""

    def start(self):
        pass

    def update(self, stage=None, detail=None, value=None, maximum=None):
        pass

    def close(self):
        pass


class UpdateProgressWindow:
    """Win32 原生更新进度窗口（参考 MAA.Updater）。

    - 窗口与消息泵运行在独立线程，更新逻辑线程只写入共享状态；
    - 进度未知时展示来回摆动的不定进度条；
    - 任何 Win32 调用失败都静默降级为无进度窗，绝不阻塞更新流程。
    """

    def __init__(self, enabled=True):
        self._enabled = enabled and os.name == "nt"
        self._lock = threading.Lock()
        self._stage = "正在准备更新..."
        self._detail = ""
        self._value = 0
        self._maximum = 0  # 0 表示不定进度
        self._closing = False
        self._thread = None

    @property
    def enabled(self):
        """进度窗是否处于启用状态（Win32 失败后会自动降级为 False）。"""
        return self._enabled

    def start(self):
        if not self._enabled:
            return
        self._thread = threading.Thread(target=self._window_thread, name="AALCUpdaterProgressUI", daemon=True)
        self._thread.start()

    def update(self, stage=None, detail=None, value=None, maximum=None):
        if not self._enabled:
            return
        with self._lock:
            if stage is not None:
                self._stage = stage
            if detail is not None:
                self._detail = detail
            if value is not None:
                self._value = max(0, int(value))
            if maximum is not None:
                self._maximum = max(0, int(maximum))

    def close(self):
        if not self._enabled:
            return
        with self._lock:
            self._closing = True
        if self._thread is not None:
            self._thread.join(timeout=2)
            self._thread = None

    def _window_thread(self):
        try:
            self._window_loop()
        except Exception as exc:  # 进度窗失败不允许影响更新流程
            _log(f"进度窗口不可用，已降级为无进度窗更新: {exc}")
            self._enabled = False

    def _window_loop(self):
        user32 = ctypes.windll.user32
        gdi32 = ctypes.windll.gdi32
        kernel32 = ctypes.windll.kernel32

        WM_SETTEXT = 0x000C
        WM_SETFONT = 0x0030
        PBM_SETPOS = 0x0402
        PBM_SETRANGE32 = 0x0406
        WS_CHILD = 0x40000000
        WS_VISIBLE = 0x10000000
        WS_CAPTION = 0x00C00000
        WS_SYSMENU = 0x00080000
        CW_USEDEFAULT = 0x80000000
        DEFAULT_GUI_FONT = 17
        PM_REMOVE = 1

        WNDPROC = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, ctypes.c_void_p, ctypes.c_uint, ctypes.c_size_t, ctypes.c_ssize_t)

        class WNDCLASSW(ctypes.Structure):
            _fields_ = [
                ("style", ctypes.c_uint),
                ("lpfnWndProc", WNDPROC),
                ("cbClsExtra", ctypes.c_int),
                ("cbWndExtra", ctypes.c_int),
                ("hInstance", ctypes.c_void_p),
                ("hIcon", ctypes.c_void_p),
                ("hCursor", ctypes.c_void_p),
                ("hbrBackground", ctypes.c_void_p),
                ("lpszMenuName", ctypes.c_wchar_p),
                ("lpszClassName", ctypes.c_wchar_p),
            ]

        class MSG(ctypes.Structure):
            _fields_ = [
                ("hwnd", ctypes.c_void_p),
                ("message", ctypes.c_uint),
                ("wParam", ctypes.c_size_t),
                ("lParam", ctypes.c_ssize_t),
                ("time", ctypes.c_uint),
                ("pt_x", ctypes.c_long),
                ("pt_y", ctypes.c_long),
            ]

        user32.CreateWindowExW.restype = ctypes.c_void_p
        gdi32.GetStockObject.restype = ctypes.c_void_p
        kernel32.GetModuleHandleW.restype = ctypes.c_void_p
        # DefWindowProcW 会作为窗口过程回调被调用：必须声明完整签名，
        # 否则 lParam 指针值超过 C int 范围时回调内部会抛 OverflowError
        user32.DefWindowProcW.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_size_t, ctypes.c_ssize_t]
        user32.DefWindowProcW.restype = ctypes.c_ssize_t
        user32.SendMessageW.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p, ctypes.c_void_p]
        user32.SendMessageW.restype = ctypes.c_ssize_t

        hinstance = ctypes.c_void_p(kernel32.GetModuleHandleW(None))
        window_class_name = "AALCUpdaterProgressWnd"

        # comctl32 的进度条控件需要注册公共控件
        with contextlib.suppress(Exception):
            ctypes.windll.comctl32.InitCommonControls()

        wnd_proc = WNDPROC(user32.DefWindowProcW)
        wc = WNDCLASSW()
        wc.lpfnWndProc = wnd_proc
        wc.hInstance = hinstance
        wc.hbrBackground = ctypes.c_void_p(gdi32.GetStockObject(0))  # WHITE_BRUSH
        wc.lpszClassName = window_class_name
        if not user32.RegisterClassW(ctypes.byref(wc)):
            raise OSError("RegisterClassW failed")

        hwnd = ctypes.c_void_p(
            user32.CreateWindowExW(
                0,
                window_class_name,
                "AALC 正在更新 | AALC Updating",
                WS_CAPTION | WS_SYSMENU,
                ctypes.c_int(CW_USEDEFAULT),
                ctypes.c_int(CW_USEDEFAULT),
                430,
                155,
                None,
                None,
                hinstance,
                None,
            )
        )
        if not hwnd:
            raise OSError("CreateWindowExW failed")

        def create_child(class_name, text, x, y, width, height):
            return ctypes.c_void_p(
                user32.CreateWindowExW(
                    0, class_name, text, WS_CHILD | WS_VISIBLE, x, y, width, height, hwnd, None, hinstance, None
                )
            )

        label_stage = create_child("STATIC", "正在准备更新...", 16, 12, 392, 20)
        label_detail = create_child("STATIC", "", 16, 38, 392, 20)
        progress_bar = create_child("msctls_progress32", None, 16, 68, 392, 26)

        hfont = ctypes.c_void_p(gdi32.GetStockObject(DEFAULT_GUI_FONT))
        for control in (label_stage, label_detail):
            user32.SendMessageW(control, WM_SETFONT, hfont, 1)

        msg = MSG()
        started_at = time.monotonic()
        last_stage = last_detail = None
        last_value = last_maximum = None
        while True:
            with self._lock:
                closing = self._closing
                stage, detail = self._stage, self._detail
                value, maximum = self._value, self._maximum
            if closing or not user32.IsWindow(hwnd):
                break
            while user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, PM_REMOVE):
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))
            if stage != last_stage:
                user32.SendMessageW(label_stage, WM_SETTEXT, 0, ctypes.c_wchar_p(stage))
                last_stage = stage
            if detail != last_detail:
                user32.SendMessageW(label_detail, WM_SETTEXT, 0, ctypes.c_wchar_p(detail))
                last_detail = detail
            if maximum != last_maximum:
                user32.SendMessageW(progress_bar, PBM_SETRANGE32, 0, max(maximum, 1))
                last_maximum = maximum
                last_value = None
            if maximum > 0:
                position = min(value, maximum)
            else:
                # 不定进度：0 -> 100 -> 0 来回摆动
                tick = int((time.monotonic() - started_at) * 1000 // 30) % 200
                position = 200 - tick if tick > 100 else tick
            if position != last_value:
                user32.SendMessageW(progress_bar, PBM_SETPOS, position, 0)
                last_value = position
            time.sleep(0.05)

        user32.DestroyWindow(hwnd)
        user32.PostQuitMessage(0)


# ---------------------------------------------------------------------------
# 命令行参数
# ---------------------------------------------------------------------------

class UpdaterArguments:
    """更新器命令行参数。"""

    def __init__(self, file_name=None, apply_mode=False, parent_pid=None, no_progress_ui=False):
        self.file_name = file_name
        self.apply_mode = apply_mode
        self.parent_pid = parent_pid
        self.no_progress_ui = no_progress_ui


def parse_updater_args(argv):
    """解析更新器命令行，兼容旧版 ``<file>`` 与 ``--apply-update <file>`` 形式。"""
    file_name = None
    apply_mode = False
    parent_pid = None
    no_progress_ui = False

    index = 0
    while index < len(argv):
        arg = argv[index]
        if arg == "--apply-update":
            apply_mode = True
        elif arg == "--parent-pid" and index + 1 < len(argv):
            index += 1
            with contextlib.suppress(ValueError):
                parent_pid = int(argv[index])
        elif arg == "--no-progress-ui":
            no_progress_ui = True
        elif file_name is None and not arg.startswith("-"):
            file_name = arg
        index += 1

    return UpdaterArguments(file_name=file_name, apply_mode=apply_mode, parent_pid=parent_pid, no_progress_ui=no_progress_ui)


# ---------------------------------------------------------------------------
# 更新器主体
# ---------------------------------------------------------------------------

class Updater:
    """应用程序更新器，负责检查、下载、解压和安装最新版本的应用程序。"""

    def __init__(self, file_name=None, no_progress_ui=False):
        self.process_names = ["AALC.exe"]
        self.updater_name = "AALC Updater.exe"
        self.apply_updater_name = "AALC Updater.apply.exe"

        self.temp_path = os.path.abspath(f"./{TEMP_DIR_NAME}")
        os.makedirs(self.temp_path, exist_ok=True)

        self.file_name = file_name
        self.no_progress_ui = no_progress_ui
        self.log_path = os.path.join(self.temp_path, LOG_FILE_NAME)

        self.cover_folder_path = os.path.abspath("./")

        self.exe_path = os.path.abspath("./assets/binary/7za.exe")
        self.delete_folder_path = os.path.abspath("./assets/images")
        self.changes_file_path = os.path.abspath(f"./{TEMP_DIR_NAME}/changes.json")

        if self.file_name is None:
            self.download_file_path = None
            self.extract_folder_path = self.temp_path
        else:
            self.download_file_path = os.path.join(self.temp_path, self.file_name)
            self.extract_folder_path = os.path.join(self.temp_path, self.file_name.rsplit(".", 1)[0])

        self.progress = _NullProgress()
        self._incremental_update_plan = None

    # ------------------------------------------------------------------
    # 对外流程
    # ------------------------------------------------------------------

    def run(self, apply_mode=False, parent_pid=None, progress=None):
        """执行完整更新流程，返回是否成功。"""
        self.progress = progress or _NullProgress()
        self.progress.update(stage="正在准备更新...", detail="校验更新包")
        try:
            self._prepare_update_payload(apply_mode)
        except UpdatePayloadError as exc:
            self._abort_safely(str(exc), install_modified=False)
            return False

        try:
            self.validate_update_payload()
        except UpdateManifestError as exc:
            self._abort_safely(f"更新清单无效，已取消更新: {exc}", install_modified=False)
            return False

        # 引导进程把剩余工作交给包内新更新器（其自身体积大、可能需要先自更新）
        if not apply_mode and self._handoff_to_new_updater():
            return True

        self._wait_for_parent_exit(parent_pid)

        self.progress.update(stage="正在关闭 AALC 进程...", detail="清理可能占用更新文件的进程")
        self.terminate_processes()

        try:
            self.cover_folder()
        except Exception as exc:
            self._abort_safely(f"覆盖安装失败: {exc}", install_modified=True)
            return False

        self.progress.update(stage="正在清理临时文件...", detail="")
        self.cleanup()
        relaunch_app(self.progress)
        return True

    def _abort_safely(self, reason, install_modified):
        """更新中止：弹窗说明原因；未改动安装时自动恢复旧版本运行。"""
        _log(f"更新中止: {reason}")
        if install_modified:
            hint = "\n\n本次更新未完成，安装目录可能不完整，请重新更新或手动恢复。"
        else:
            hint = "\n\n安装文件未被改动，将自动重启当前版本的 AALC。"
        show_error_dialog("AALC 更新失败", f"{reason}{hint}\n\n详细日志: {self.log_path}")
        self.progress.update(stage="更新失败", detail=reason)
        if not install_modified:
            relaunch_app(self.progress)

    def _wait_for_parent_exit(self, parent_pid):
        """等待主程序优雅退出（MAA.Updater 的 ParentPid 等待策略）。

        主程序启动更新器后会自行保存配置并退出；限时内未退出则放行，
        由随后的进程清扫兜底强制结束，避免更新被挂死的主程序卡住。
        """
        if not parent_pid:
            return
        _log(f"等待主程序退出 (PID={parent_pid})，最多 {_PARENT_EXIT_WAIT_SECONDS}s ...")
        self.progress.update(stage="正在等待 AALC 退出...", detail="主程序正在保存配置并退出")
        deadline = time.monotonic() + _PARENT_EXIT_WAIT_SECONDS
        while time.monotonic() < deadline:
            try:
                if not psutil.pid_exists(parent_pid):
                    _log("主程序已退出")
                    return
            except psutil.Error:
                return
            time.sleep(0.2)
        _log("等待主程序退出超时，转由进程清扫兜底")

    # ------------------------------------------------------------------
    # 解压与校验
    # ------------------------------------------------------------------

    def extract_file(self):
        """解压下载的更新包，自动重试有限次数。"""
        _log("开始解压更新包...")
        self.progress.update(stage="正在解压更新包...", detail=os.path.basename(self.download_file_path or ""))
        last_error = None
        for attempt in range(1, _EXTRACT_MAX_ATTEMPTS + 1):
            try:
                self._reset_extraction_workspace()
                if os.path.exists(self.exe_path):
                    self._run_7zip_extract()
                else:
                    shutil.unpack_archive(self.download_file_path, self.temp_path)
                _log("解压完成")
                return True
            except Exception as exc:
                last_error = exc
                _log(f"解压失败(第 {attempt}/{_EXTRACT_MAX_ATTEMPTS} 次): {exc}")
                time.sleep(1)
        _log("多次解压失败，请查看日志或手动下载更新")
        self._last_extract_error = last_error
        return False

    def _run_7zip_extract(self):
        """调用 7za 解压；无窗口启动并捕获输出，避免控制台闪现。"""
        try:
            result = subprocess.run(
                [self.exe_path, "x", self.download_file_path, f"-o{self.temp_path}", "-aoa"],
                check=True,
                capture_output=True,
                creationflags=_CREATE_NO_WINDOW,
            )
            if result.stdout:
                _log(result.stdout.decode("utf-8", "replace").strip())
        except subprocess.CalledProcessError as exc:
            detail = (exc.stderr or b"").decode("utf-8", "replace").strip()
            if detail:
                _log(f"7za 输出: {detail}")
            raise

    def _reset_extraction_workspace(self):
        """清理本次解压目标，避免复用上一次更新残留的载荷或清单。"""
        if not self.download_file_path:
            return

        if self.extract_folder_path and os.path.isdir(self.extract_folder_path):
            shutil.rmtree(self.extract_folder_path, ignore_errors=True)
        if self.changes_file_path and os.path.exists(self.changes_file_path):
            with contextlib.suppress(OSError):
                os.remove(self.changes_file_path)

    def _prepare_update_payload(self, apply_mode):
        # 引导进程已解压过同一归档（handoff 只发生在解压成功后），apply 模式直接复用，避免重复解压。
        if apply_mode and os.path.isdir(self.extract_folder_path) and os.listdir(self.extract_folder_path):
            _log("复用引导进程的解压结果...")
            return
        if not self.extract_file():
            detail = f"（最后错误: {getattr(self, '_last_extract_error', None)}）" if hasattr(self, "_last_extract_error") else ""
            raise UpdatePayloadError(f"更新包解压失败{detail}")

    def validate_update_payload(self):
        """在终止应用进程前验证增量更新清单及其所有目标路径。"""
        self._incremental_update_plan = None
        if not os.path.exists(self.changes_file_path):
            return
        self._incremental_update_plan = self._load_incremental_update_plan()

    # ------------------------------------------------------------------
    # 新旧更新器交接
    # ------------------------------------------------------------------

    def _get_extracted_updater_path(self):
        return os.path.join(self.extract_folder_path, self.updater_name)

    def _get_staged_updater_path(self):
        return os.path.join(self.temp_path, self.apply_updater_name)

    def _handoff_to_new_updater(self, current_executable=None):
        if not self.file_name:
            return False

        extracted_updater_path = self._get_extracted_updater_path()
        if not os.path.exists(extracted_updater_path):
            return False

        current_executable_path = os.path.abspath(current_executable or sys.argv[0])
        staged_updater_path = self._get_staged_updater_path()

        try:
            if os.path.abspath(extracted_updater_path) == current_executable_path:
                return False

            shutil.copy2(extracted_updater_path, staged_updater_path)
            extra_args = ["--no-progress-ui"] if self.no_progress_ui else []
            subprocess.Popen(
                [staged_updater_path, "--apply-update", self.file_name, *extra_args],
                creationflags=_DETACHED_PROCESS | _CREATE_NEW_PROCESS_GROUP,
                cwd=self.cover_folder_path,
            )
            _log("已切换到新版本更新器继续更新...")
            return True
        except Exception as exc:
            _log(f"切换到新版本更新器失败，将继续使用当前更新器: {exc}")
            return False

    # ------------------------------------------------------------------
    # 进程清理
    # ------------------------------------------------------------------

    def terminate_processes(self):
        """终止相关进程以准备更新。"""
        _log("开始清理占用安装目录的进程...")
        install_root = os.path.normcase(os.path.abspath(self.cover_folder_path)) + os.sep
        for proc in psutil.process_iter(attrs=["pid", "name"]):
            if proc.pid == os.getpid():
                continue  # 更新器自身位于 update_temp（安装根目录内），不能杀自己
            try:
                exe_path = proc.exe()
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                continue
            # 覆盖 AALC 及安装目录内的附属进程（如 adb 服务），否则其可执行文件会被占用无法覆盖
            is_install_binary = os.path.normcase(exe_path).startswith(install_root)
            if proc.info["name"] in self.process_names or any(name in proc.info["name"] for name in self.process_names) or is_install_binary:
                try:
                    proc.terminate()
                    try:
                        proc.wait(timeout=10)  # 等待最多10秒
                    except psutil.TimeoutExpired:
                        proc.kill()  # 超时强制终止
                        proc.wait(timeout=5)  # 再次等待
                    _log(f"已终止进程 PID: {proc.info['pid']} ({proc.info['name']})")
                except psutil.AccessDenied:
                    _log(f"无权限终止进程 PID: {proc.info['pid']}")
                except psutil.NoSuchProcess:
                    _log(f"进程 PID: {proc.info['pid']} 已退出")
        _log("进程清理完成")

    # ------------------------------------------------------------------
    # 覆盖安装
    # ------------------------------------------------------------------

    def cover_folder(self):
        """覆盖安装最新版本的文件。"""
        if os.path.exists(self.changes_file_path):
            self._apply_incremental_update()
            return

        # 全量包：先移除旧资源目录，再整体覆盖
        _log("开始覆盖安装...")
        if not os.path.isdir(self.extract_folder_path):
            raise UpdatePayloadError(f"解压目录缺失，更新包内容不完整: {self.extract_folder_path}")
        try:
            self._retry_fs(lambda: shutil.rmtree(self.delete_folder_path), "删除旧资源目录")
        except FileNotFoundError:
            _log("待删除目录不存在，跳过")
        except Exception as exc:
            _log(f"删除旧资源文件失败: {exc}")

        entries = self._collect_copy_entries()
        self.progress.update(stage="正在安装新文件...", detail="", value=0, maximum=len(entries))
        for index, (source, destination) in enumerate(entries, start=1):
            self._copy_file_with_retry(source, destination)
            self.progress.update(value=index)
        _log(f"覆盖安装完成，共写入 {len(entries)} 个文件")

    def _collect_copy_entries(self):
        """枚举解压目录内所有待复制文件，按稳定顺序返回 (源, 目标) 列表。"""
        entries = []
        for current_root, dir_names, file_names in os.walk(self.extract_folder_path):
            dir_names.sort()
            relative_root = os.path.relpath(current_root, self.extract_folder_path)
            destination_root = self.cover_folder_path if relative_root == "." else os.path.join(self.cover_folder_path, relative_root)
            with contextlib.suppress(OSError):
                os.makedirs(destination_root, exist_ok=True)
            for file_name in sorted(file_names):
                source = os.path.join(current_root, file_name)
                destination = os.path.join(destination_root, file_name)
                entries.append((source, destination))
        return entries

    def _retry_fs(self, operation, description, attempts=_FS_OP_MAX_ATTEMPTS):
        """对文件操作做有限次自动重试，应对杀软扫描等短暂占用。"""
        for attempt in range(1, attempts + 1):
            try:
                return operation()
            except OSError as exc:
                if attempt == attempts:
                    raise
                _log(f"{description} 失败(第 {attempt}/{attempts} 次): {exc}，{_FS_OP_RETRY_DELAY_SECONDS}s 后自动重试")
                time.sleep(_FS_OP_RETRY_DELAY_SECONDS)

    def _copy_file_with_retry(self, source, destination):
        """复制单个文件；目标被占用时按 MAA.Updater 的思路改名腾位后重试。"""

        def do_copy():
            parent = os.path.dirname(destination)
            if parent:
                os.makedirs(parent, exist_ok=True)
            shutil.copy2(source, destination)

        try:
            self._retry_fs(do_copy, f"写入 {os.path.basename(destination)}")
            return
        except OSError:
            if not os.path.exists(destination):
                raise

        # 目标存在且始终写不进去（例如被短暂锁定）：把旧文件改名让出位置后重试
        backup_path = f"{destination}.old-{os.getpid()}-{int(time.time())}"
        _log(f"目标仍被占用，尝试改名腾位: {backup_path}")
        os.replace(destination, backup_path)
        self._retry_fs(do_copy, f"写入 {os.path.basename(destination)}")

    def _apply_incremental_update(self):
        """根据 changes.json 执行增量更新。"""
        changes = self._incremental_update_plan or self._load_incremental_update_plan()

        _log("检测到增量更新清单，执行增量更新...")
        total = sum(len(changes[key]) for key in changes)
        self.progress.update(stage="正在应用增量更新...", detail="", value=0, maximum=total)
        done = 0

        for dir_path, full_path in changes["deleted_dir"]:
            try:
                shutil.rmtree(full_path)
                _log(f"删除目录: {dir_path}")
            except FileNotFoundError:
                _log(f"删除目录不存在: {dir_path}")
            done += 1
            self.progress.update(value=done)

        for file_path, full_path in changes["deleted"]:
            try:
                os.remove(full_path)
                _log(f"删除文件: {file_path}")
            except FileNotFoundError:
                _log(f"删除文件不存在: {file_path}")
            done += 1
            self.progress.update(value=done)

        for dir_path, full_path in changes["added_dir"]:
            os.makedirs(full_path, exist_ok=True)
            _log(f"创建目录: {dir_path}")
            done += 1
            self.progress.update(value=done)

        for kind, label in (("added", "新增文件"), ("modified", "更新文件")):
            for file_path, source, destination in changes[kind]:
                try:
                    self._copy_file_with_retry(source, destination)
                    _log(f"{label}: {file_path}")
                except FileNotFoundError:
                    _log(f"源文件不存在: {file_path}")
                except OSError as exc:
                    raise UpdatePayloadError(f"应用增量更新失败: {file_path}: {exc}") from exc
                done += 1
                self.progress.update(value=done)

        _log("增量更新完成")

    # ------------------------------------------------------------------
    # 增量清单安全校验（保持原有逻辑不变）
    # ------------------------------------------------------------------

    def _normalize_manifest_path(self, relative_path):
        """兼容带归档根目录前缀与普通相对路径的增量清单。"""
        if not isinstance(relative_path, str) or not relative_path or "\0" in relative_path:
            raise UpdateManifestError("更新清单包含空路径或非字符串路径")

        portable_path = relative_path.replace("\\", "/")
        if portable_path.startswith("/") or (len(portable_path) >= 2 and portable_path[1] == ":"):
            raise UpdateManifestError(f"更新清单包含绝对路径: {relative_path}")

        raw_parts = PurePosixPath(portable_path).parts
        if any(part == ".." or ":" in part for part in raw_parts):
            raise UpdateManifestError(f"更新清单包含非法相对路径: {relative_path}")

        parts = [part for part in raw_parts if part not in ("", ".")]
        if not parts:
            raise UpdateManifestError("更新清单包含空路径")

        archive_root_name = os.path.basename(os.path.normpath(self.extract_folder_path))
        if os.path.normcase(parts[0]) == os.path.normcase(archive_root_name):
            parts = parts[1:]

        if not parts:
            raise UpdateManifestError("更新清单不能指向归档根目录")

        return os.path.join(*parts)

    @staticmethod
    def _resolve_path_within_root(root_path, relative_path):
        """解析路径并拒绝经父目录或链接离开可信根目录的情况。"""
        try:
            root = Path(root_path).resolve()
            candidate = (root / relative_path).resolve()
        except OSError as exc:
            raise UpdateManifestError(f"无法解析更新清单路径: {relative_path}") from exc
        try:
            candidate.relative_to(root)
        except ValueError as exc:
            raise UpdateManifestError(f"更新清单路径逃离可信根目录: {relative_path}") from exc
        return os.fspath(candidate)

    def _load_incremental_update_plan(self):
        try:
            with open(self.changes_file_path, "r", encoding="utf-8") as f:
                raw_changes = json.load(f)
        except (OSError, json.JSONDecodeError) as exc:
            raise UpdateManifestError("无法读取更新清单") from exc

        if not isinstance(raw_changes, dict):
            raise UpdateManifestError("更新清单必须是对象")

        plan = {"deleted_dir": [], "deleted": [], "added_dir": [], "added": [], "modified": []}
        for operation, entries in raw_changes.items():
            if operation not in plan:
                raise UpdateManifestError(f"更新清单包含未知操作: {operation}")
            if not isinstance(entries, list):
                raise UpdateManifestError(f"更新清单操作 {operation} 必须是路径列表")

            for original_path in entries:
                normalized_path = self._normalize_manifest_path(original_path)
                target_path = self._resolve_path_within_root(self.cover_folder_path, normalized_path)
                if operation in {"added", "modified"}:
                    source_path = self._resolve_path_within_root(self.extract_folder_path, normalized_path)
                    plan[operation].append((original_path, source_path, target_path))
                else:
                    plan[operation].append((original_path, target_path))

        return plan

    # ------------------------------------------------------------------
    # 清理与重启
    # ------------------------------------------------------------------

    def cleanup(self):
        """清理下载和解压的临时文件。"""
        _log("开始清理...")
        self._cleanup_file(self.download_file_path, "下载文件")
        self._cleanup_tree(self.extract_folder_path, "提取目录")
        self._cleanup_file(self.changes_file_path, "变更清单文件")
        _log("清理完成")

    @staticmethod
    def _cleanup_file(path, label):
        if not path:
            return
        try:
            os.remove(path)
        except FileNotFoundError:
            _log(f"{label}不存在，跳过")
        except Exception as exc:
            _log(f"清理{label}失败: {exc}")

    @staticmethod
    def _cleanup_tree(path, label):
        if not path:
            return
        try:
            shutil.rmtree(path)
        except FileNotFoundError:
            _log(f"{label}不存在，跳过")
        except Exception as exc:
            _log(f"清理{label}失败: {exc}")


def relaunch_app(progress=None):
    """启动（新版本）AALC 主程序，替代旧的 ``cmd /c start`` 方案（无终端闪现）。"""
    exe_path = os.path.abspath("./AALC.exe")
    if not os.path.exists(exe_path):
        _log("未找到 AALC.exe，跳过自动重启")
        return
    _log("正在启动 AALC...")
    if progress is not None:
        progress.update(stage="正在启动 AALC...", detail="更新完成")
    try:
        subprocess.Popen(
            [exe_path],
            cwd=os.path.dirname(exe_path) or None,
            creationflags=_DETACHED_PROCESS | _CREATE_NEW_PROCESS_GROUP,
            close_fds=True,
        )
    except OSError as exc:
        _log(f"AALC 启动失败: {exc}")
        show_error_dialog("AALC 更新完成", f"更新已完成，但自动启动 AALC 失败，请手动运行 AALC.exe。\n\n{exc}")


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------

def _maybe_relaunch_from_temp():
    """引导：把更新器自身复制到 update_temp 再重启，避免安装根目录内的自身被覆盖。"""
    temp_path = os.path.abspath(f"./{TEMP_DIR_NAME}")
    file_path = sys.argv[0]
    destination_path = os.path.join(temp_path, os.path.basename(file_path))

    if file_path == destination_path:
        return

    try:
        if os.path.exists("./Update.exe"):
            os.remove("./Update.exe")
        os.makedirs(temp_path, exist_ok=True)
        shutil.copy(file_path, destination_path)
    except OSError as exc:
        _log(f"初始化更新器失败: {exc}")
        show_error_dialog("AALC 更新失败", f"初始化更新器失败: {exc}\n\n详细日志: {os.path.join(temp_path, LOG_FILE_NAME)}")
        relaunch_app()
        sys.exit(2)

    subprocess.Popen(
        [destination_path] + sys.argv[1:],
        creationflags=_DETACHED_PROCESS | _CREATE_NEW_PROCESS_GROUP,
        cwd=os.path.abspath("./"),
    )
    sys.exit(0)


def main():
    log_path = _setup_logging()
    if not getattr(sys, "frozen", False):
        # 沿用原版的保护：未打包环境直接运行会覆写开发目录，必须拒绝
        _log("更新器只支持打包成 exe 后在 AALC 安装目录中运行")
        show_error_dialog("AALC 更新器", "更新程序只支持在打包后的 AALC 安装目录中运行。")
        sys.exit(1)

    args = parse_updater_args(sys.argv[1:])
    if args.apply_mode and not args.file_name:
        show_error_dialog("AALC 更新器", "缺少更新包文件名参数，更新已取消。")
        sys.exit(2)

    _log(f"更新器启动: argv={sys.argv[1:]}, apply_mode={args.apply_mode}, log={log_path}")
    _maybe_relaunch_from_temp()

    progress = UpdateProgressWindow(enabled=not args.no_progress_ui)
    progress.start()
    updater = Updater(args.file_name, no_progress_ui=args.no_progress_ui)
    try:
        succeeded = updater.run(apply_mode=args.apply_mode, parent_pid=args.parent_pid, progress=progress)
    except Exception as exc:
        _log(f"更新过程出现未处理异常: {exc}")
        _log(traceback.format_exc())
        show_error_dialog("AALC 更新失败", f"{exc}\n\n详细日志: {updater.log_path}")
        succeeded = False
    finally:
        progress.close()
    _log(f"更新器退出，结果: {'成功' if succeeded else '失败'}")
    sys.exit(0 if succeeded else 2)


if __name__ == "__main__":
    main()
