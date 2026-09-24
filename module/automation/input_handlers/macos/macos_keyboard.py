"""macOS 后台按键注入（CGEventPostToPid）。

PlayCover/MaaTools 协议没有键盘指令（见 ``playcover_control`` 模块说明），但游戏本体跑在
PlayTools 注入的进程里、直接读硬件键盘：把合成键盘事件投递到**游戏进程**即可，不需要
窗口拥有焦点，也不打扰用户当前操作（实机验证：游戏处于后台时 Enter/P/ESC 都已生效）。

- ``CGEventPostToPid(pid, event)``：把事件投进目标进程的事件流（macOS 10.11+ 公开 API，
  见 CGEvent.h）；全局的 ``CGEventPost`` 只进前台 App，做不到后台。
- 发送进程需要「辅助功能」权限（``AXIsProcessTrusted``），否则事件被系统丢弃。此时
  ``available()`` 为 False，调用方回退到触摸。
- 只维护确实要用的按键（见 ``KEYCODES``）：Enter（确认/开始回合）、P（自动选择技能）、
  ESC（返回/暂停）。其余按键（方向键、文本）继续走触摸兜底。
- 启动预热：AALC 启动时先投一次游戏未绑定的 F13（``warm_up``），把「解析游戏进程」与
  「macOS 首次跨进程投递的隐私检查」这两笔一次性成本提前付掉 —— 否则战斗里首次注入比
  后续慢一倍以上，P 与 Enter 之间仅隔 0.5s，会被拖到回合开不起来。
"""

import os
import subprocess
import sys
import threading
from time import sleep

from module.logger import log

if sys.platform == "darwin":
    try:
        import Quartz
        from ApplicationServices import AXIsProcessTrusted
    except ImportError:  # 精简的 pyobjc 安装（缺 ApplicationServices 桥接）
        Quartz = None
        AXIsProcessTrusted = None
else:  # 非 macOS：模块保持可导入，能力恒为 False
    Quartz = None
    AXIsProcessTrusted = None

_KEY_RETURN = 36
_KEY_P = 35
_KEY_ESCAPE = 53

KEYCODES: dict[str, int] = {
    "enter": _KEY_RETURN,
    "return": _KEY_RETURN,
    "p": _KEY_P,
    "esc": _KEY_ESCAPE,
}
"""可注入的按键（键名与 pyautogui 一致）；其余键名不支持，由调用方走触摸兜底。"""

_KEY_PRESS_INTERVAL = 0.05
"""keyDown 与 keyUp 的间隔：PlayTools 按 keyDown/keyUp 成对处理按下与释放。"""

_WARMUP_KEYCODE = 105
"""预热用的按键：macOS 虚拟键码 F13。游戏没有绑定该键，投递只为把首次注入的成本提前付掉。"""

_LOCAL_HOSTS = frozenset({"127.0.0.1", "localhost", "::1", "0.0.0.0"})
_PLAYCOVER_APPS_MARKER = "/io.playcover.PlayCover/Applications/"

_pid_cache: dict[tuple[str, int], int] = {}
_cache_lock = threading.RLock()
_warned_no_permission = False
_warmup_lock = threading.RLock()
_warmed_up = False


def available() -> bool:
    """能否把按键送进游戏进程：macOS + pyobjc + 已授予辅助功能权限。"""
    if Quartz is None:
        return False
    if AXIsProcessTrusted is None:
        return True
    try:
        return bool(AXIsProcessTrusted())
    except Exception as e:
        log.debug(f"查询辅助功能权限失败: {e}")
        return False


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:  # 进程存在但不属于当前用户
        return True
    except OSError:
        return False
    return True


def _pid_from_listen_port(port: int) -> int | None:
    """MaaTools 服务监听在游戏进程内，按端口反查即可拿到游戏 pid。"""
    try:
        result = subprocess.run(
            ["/usr/sbin/lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN", "-t"],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError) as e:
        log.debug(f"lsof 查询 MaaTools 监听端口失败: {e}")
        return None
    pids = [int(item) for item in result.stdout.split() if item.isdigit()]
    if len(pids) == 1:
        return pids[0]
    log.debug(f"MaaTools 端口 {port} 的监听进程不唯一: {pids}")
    return None


def _pid_from_running_apps() -> int | None:
    """回退：在 PlayCover 容器 Applications 目录下运行的进程即游戏本体。"""
    try:
        from AppKit import NSWorkspace
    except ImportError:
        return None
    found: list[int] = []
    for app in NSWorkspace.sharedWorkspace().runningApplications():
        url = app.executableURL()
        if url is not None and _PLAYCOVER_APPS_MARKER in str(url.path()):
            found.append(int(app.processIdentifier()))
    if len(found) == 1:
        return found[0]
    log.debug(f"PlayCover 容器内候选游戏进程 {found}，无法唯一确定")
    return None


def game_pid(host: str, port: int) -> int | None:
    """MaaTools 服务对应的游戏进程 pid（带缓存，进程消失后重新解析）。

    只有本机 PlayCover 才谈得上注入：远程 host 直接返回 None，调用方走触摸兜底。
    """
    if str(host) not in _LOCAL_HOSTS:
        log.debug(f"PlayCover 游戏不在本机（host={host}），无法注入按键")
        return None
    key = (str(host), int(port))
    with _cache_lock:
        cached = _pid_cache.get(key)
        if cached is not None and _alive(cached):
            return cached
        pid = _pid_from_listen_port(int(port)) or _pid_from_running_apps()
        if pid is None:
            log.debug(f"未定位到 PlayCover 游戏进程（host={host} port={port}）")
            return None
        _pid_cache[key] = pid
        log.info(f"PlayCover 游戏进程 pid={pid}（MaaTools {host}:{port}），按键经 CGEventPostToPid 注入")
        return pid


def _post_keycode(pid: int, keycode: int) -> None:
    """把一次按键（keyDown + keyUp）投递给目标进程。"""
    source = Quartz.CGEventSourceCreate(Quartz.kCGEventSourceStateHIDSystemState)
    for down in (True, False):
        Quartz.CGEventPostToPid(pid, Quartz.CGEventCreateKeyboardEvent(source, keycode, down))
        sleep(_KEY_PRESS_INTERVAL)


def press(key: str, host: str, port: int) -> bool:
    """向游戏进程注入一次按键（keyDown + keyUp）；不支持或不可用时返回 False。"""
    global _warned_no_permission
    keycode = KEYCODES.get(key)
    if keycode is None:
        return False
    if not available():
        if not _warned_no_permission:
            log.warning(
                "未授予「辅助功能」权限，按键无法注入游戏（触摸兜底仍可用）："
                "请到 系统设置 → 隐私与安全性 → 辅助功能 勾选运行 AALC 的程序"
            )
            _warned_no_permission = True
        return False
    pid = game_pid(host, port)
    if pid is None:
        return False
    _post_keycode(pid, keycode)
    log.debug(f"注入按键 {key}(keyCode={keycode}) -> pid={pid}")
    return True


def warm_up(host: str, port: int) -> bool:
    """预热按键注入：AALC 启动时先注一次键，把「首次注入」的一次性成本提前付掉。

    首次注入比后续慢得多，因为要现付两笔一次性成本：反查游戏 pid（起一次 lsof，
    失败还要枚举 NSWorkspace），以及 macOS 首次跨进程投递事件时的隐私检查（实测
    首次约 350ms，之后每次约 140ms）。战斗中 P 与 Enter 之间只隔 0.5s，首次注入
    变慢会把这一对拆开、回合开不起来。启动时先投一次游戏未绑定的 F13，pid 也顺带
    缓存好，之后战斗里的首次注入就与后续注入同速了。

    游戏没启动（定位不到进程）或没授权时直接跳过并返回 False，调用方可在下次设备
    初始化时再试；成功后本进程内不再重复注入。
    """
    global _warmed_up
    with _warmup_lock:
        if _warmed_up:
            return True
        if not available():
            log.debug("跳过按键注入预热：不可用（非 macOS 或缺辅助功能权限）")
            return False
        pid = game_pid(host, port)
        if pid is None:
            log.debug("跳过按键注入预热：未定位到 PlayCover 游戏进程")
            return False
        _post_keycode(pid, _WARMUP_KEYCODE)
        _warmed_up = True
        log.info(f"按键注入预热完成（F13 -> pid={pid}），战斗内首次 P/Enter 不再付解析与授权开销")
        return True


def warm_up_in_background(host: str, port: int) -> None:
    """后台线程里跑一次预热：启动路径不该为它多等一次 lsof 与隐私检查。"""
    threading.Thread(
        target=warm_up,
        args=(host, port),
        name="keyboard-warmup",
        daemon=True,
    ).start()
