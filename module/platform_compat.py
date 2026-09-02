"""跨平台兼容层。

集中平台判断与平台相关的系统调用（打开文件/目录、脱离进程启动、结束进程），
避免各业务模块直接依赖 Windows 专属 API。
"""

import os
import shutil
import subprocess
import sys

IS_WINDOWS = os.name == "nt"
"""是否为 Windows 平台（pywin32 / UAC / Toast 等能力可用）"""

IS_LINUX = sys.platform.startswith("linux")


def open_path(path: str) -> None:
    """用系统默认方式打开文件或目录（资源管理器/浏览器等）。"""
    if IS_WINDOWS:
        os.startfile(path)  # noqa: S606
    elif sys.platform == "darwin":
        subprocess.Popen(["open", path])
    else:
        if shutil.which("xdg-open") is None:
            raise RuntimeError("未找到 xdg-open，无法打开路径")
        subprocess.Popen(["xdg-open", path])


def start_detached(command: list[str], cwd: str | None = None) -> subprocess.Popen:
    """以脱离当前进程的方式启动外部程序（父进程退出后子进程继续运行）。"""
    if IS_WINDOWS:
        # DETACHED_PROCESS 仅在 Windows 存在；POSIX 上 creationflags 必须为 0
        return subprocess.Popen(  # noqa: S603
            command,
            cwd=cwd,
            creationflags=getattr(subprocess, "DETACHED_PROCESS", 0),
            close_fds=True,
        )
    return subprocess.Popen(  # noqa: S603
        command,
        cwd=cwd,
        start_new_session=True,
    )


def kill_pid(pid: int, force: bool = True) -> bool:
    """尽力结束指定进程，返回是否成功。"""
    if pid <= 0:
        return False
    if IS_WINDOWS:
        return subprocess.run(  # noqa: S603
            ["taskkill", "/F", "/PID", str(pid)] if force else ["taskkill", "/PID", str(pid)],
            capture_output=True,
            check=False,
        ).returncode == 0
    import signal

    try:
        sig = signal.SIGKILL if force else signal.SIGTERM
        os.kill(pid, sig)
        return True
    except (ProcessLookupError, PermissionError):
        return False


def kill_process_by_name(process_name: str, force: bool = True) -> bool:
    """按进程名结束所有匹配进程（子串匹配，大小写不敏感），返回是否至少结束一个。"""
    import psutil

    killed = False
    target = process_name.lower()
    for proc in psutil.process_iter(["name", "pid"]):
        try:
            name = proc.info["name"]
            if name and target in name.lower():
                if force:
                    proc.kill()
                else:
                    proc.terminate()
                killed = True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return killed


def get_window_pid_on_windows(hwnd: int) -> int | None:
    """Windows 下通过窗口句柄取进程 PID；非 Windows 或失败返回 None。"""
    if not IS_WINDOWS:
        return None
    try:
        import win32process

        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        return pid
    except Exception:
        return None
