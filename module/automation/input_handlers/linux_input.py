"""Linux 前台输入实现，接口与 Windows 版 `Input` 一致。

Linux 的 X11 协议没有 Win32 PostMessage 后台消息通道的可靠等价物
（XSendEvent 会被 Unity/Proton 游戏忽略），因此 Linux 下统一使用前台输入。

X11 会话沿用 pyautogui 的鼠标路径，保证“移动到目标”和“点击目标”使用
同一条 X11 输入连接；只有 Wayland 会话才使用下面的 uinput/XTEST 兼容路径。
"""

import fcntl
import os
import random
import struct
import time
from typing import overload

import pyautogui
import pyperclip
from Xlib import X
from Xlib import display as xdisplay
from Xlib.ext import xtest

from module.config import cfg
from module.logger import log
from utils.singletonmeta import SingletonMeta

from ...game_and_screen import screen
from . import AbstractInput
from .scroll_swipe import build_windows_scroll_swipe_plan

pyautogui.FAILSAFE = False


def _use_pyautogui_mouse() -> bool:
    """X11 下沿用稳定的 pyautogui 鼠标路径；Wayland 才使用特殊注入。"""
    session_type = os.environ.get("XDG_SESSION_TYPE", "").lower()
    if not os.environ.get("DISPLAY"):
        return False
    if session_type == "wayland":
        return False
    return session_type == "x11" or not os.environ.get("WAYLAND_DISPLAY")

# ---------------------------------------------------------------- Xlib 注入

_DISPLAY = None


def _dpy() -> xdisplay.Display:
    global _DISPLAY
    if _DISPLAY is None:
        _DISPLAY = xdisplay.Display()
    return _DISPLAY


def _warp(x: int, y: int) -> None:
    """XWarpPointer 定位（仅回退路径使用）"""
    _dpy().screen().root.warp_pointer(int(x), int(y))
    _dpy().flush()


def _button_press(button: int = 1) -> None:
    xtest.fake_input(_dpy(), X.ButtonPress, button)
    _dpy().flush()


def _button_release(button: int = 1) -> None:
    xtest.fake_input(_dpy(), X.ButtonRelease, button)
    _dpy().flush()


def _query_pointer() -> tuple[int, int]:
    p = _dpy().screen().root.query_pointer()
    _dpy().sync()
    return int(p.root_x), int(p.root_y)


# ---------------------------------------------------------------- uinput 注入

UI_SET_EVBIT = 0x40045564
UI_SET_KEYBIT = 0x40045565
UI_SET_RELBIT = 0x40045566
UI_DEV_CREATE = 0x5501

_EV_SYN, _EV_KEY, _EV_REL = 0, 1, 2
_REL_X, _REL_Y, _REL_WHEEL = 0x00, 0x01, 0x08
_BTN_LEFT, _BTN_RIGHT, _BTN_MIDDLE = 0x110, 0x111, 0x112

_UI_FD = None
_UINPUT_UNAVAILABLE = False
_XTEST_MOTION_OK: bool | None = None
"""None=未探测；True=XTEST 仿真移动有效（X11 会话）；False=无效（KDE Wayland）"""
_KWIN_CURSOR_OK: bool | None = None
"""None=未探测；True=KWin 脚本读光标可用；False=不可用（已回退）"""
_KWIN_SCALE: float | None = None

_KWIN_QUERY_JS = 'console.info("AALC_CURSOR:", workspace.cursorPos.x, workspace.cursorPos.y, workspace.virtualScreenSize.width, workspace.virtualScreenSize.height);\n'
_KWIN_MARKER = f"AALC_CURSOR_{os.getpid()}_"


def _real_cursor_pos() -> tuple[int, int] | None:
    """读取真实光标位置（KDE Wayland 逻辑坐标）。

    KDE Wayland 下 X 指针与真实光标会脱钩（XWarpPointer 只动 X 侧光标、
    XTEST 仿真移动被合成器按逻辑坐标解释），因此通过 KWin 脚本读取
    workspace.cursorPos（kdotool 同款技术）；非 KDE 环境回退到 X 指针。
    """
    global _KWIN_CURSOR_OK
    if _KWIN_CURSOR_OK is not False:
        state = _kwin_cursor_state()
        if state is not None:
            _KWIN_CURSOR_OK = True
            return state[0], state[1]
        if _KWIN_CURSOR_OK is None:
            _KWIN_CURSOR_OK = False
            log.debug("KWin 脚本读取光标位置失败，绝对定位回退 X 指针")
    return _query_pointer()


def _cursor_scale() -> float:
    """X 坐标 ÷ 该系数 = KDE 逻辑坐标（virtualScreenSize / X 屏幕尺寸）"""
    global _KWIN_SCALE
    if _KWIN_SCALE is None:
        state = _kwin_cursor_state()
        try:
            xw = _dpy().screen().root.get_geometry().width
        except Exception:
            xw = 0
        if state and state[2] and xw:
            _KWIN_SCALE = state[2] / xw
        else:
            _KWIN_SCALE = 1.0
    return _KWIN_SCALE


def _kwin_cursor_state() -> tuple[int, int, int, int] | None:
    """加载临时 KWin 脚本读取真实光标位置与虚拟屏幕尺寸，经 journal 取回"""
    import subprocess
    import tempfile

    bus = os.environ.get("DBUS_SESSION_BUS_ADDRESS", f"unix:path=/run/user/{os.getuid()}/bus")
    env = {**os.environ, "DBUS_SESSION_BUS_ADDRESS": bus}
    marker = _KWIN_MARKER + str(time.monotonic_ns())
    fd, path = tempfile.mkstemp(suffix=".js", prefix="aalc_")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(_KWIN_QUERY_JS.replace("AALC_CURSOR", marker))
        def busctl(*args):
            return subprocess.run(
                ["busctl", "--user", "call", "org.kde.KWin", "/Scripting",
                 "org.kde.kwin.Scripting", *args],
                capture_output=True, text=True, timeout=5, env=env,
            )
        loaded = busctl("loadScript", "s", path)
        sid = loaded.stdout.split()[-1] if loaded.returncode == 0 else None
        if sid is None:
            return None
        subprocess.run(
            ["busctl", "--user", "call", "org.kde.KWin", f"/Scripting/Script{sid}",
             "org.kde.kwin.Script", "run"],
            capture_output=True, text=True, timeout=5, env=env,
        )
        busctl("unloadScript", "s", path)
        time.sleep(0.5)
        j = subprocess.run(
            ["journalctl", "--user", "--since", "-15s"],
            capture_output=True, text=True, timeout=5, env=env,
        )
        for line in j.stdout.splitlines():
            if marker in line:
                part = line.split(marker + ":")[1].split()
                return int(part[0]), int(part[1]), int(part[2]), int(part[3])
        return None
    except Exception as e:
        log.debug(f"KWin 脚本读取光标位置失败: {e}")
        return None
    finally:
        try:
            os.remove(path)
        except OSError:
            pass


def _open_uinput() -> int:
    """创建 uinput 虚拟鼠标设备，返回文件描述符"""
    fd = os.open("/dev/uinput", os.O_WRONLY | os.O_NONBLOCK)
    try:
        fcntl.ioctl(fd, UI_SET_EVBIT, _EV_KEY)
        fcntl.ioctl(fd, UI_SET_EVBIT, _EV_REL)
        fcntl.ioctl(fd, UI_SET_EVBIT, _EV_SYN)
        for code in (_BTN_LEFT, _BTN_RIGHT, _BTN_MIDDLE):
            fcntl.ioctl(fd, UI_SET_KEYBIT, code)
        for code in (_REL_X, _REL_Y, _REL_WHEEL):
            fcntl.ioctl(fd, UI_SET_RELBIT, code)
        # struct uinput_user_dev: name[80] + input_id(4xu16) + ff_effects_max
        # + absmax/absmin/absfuzz/absflat(各64个int)，纯相对设备全部填 0
        name = b"AALC Virtual Mouse"
        buf = name + b"\x00" * (80 - len(name))
        buf += struct.pack("HHHH", 0x06, 0x01, 0x01, 0x01)
        buf += struct.pack("i", 0)
        buf += b"\x00" * (4 * 64 * 4)
        os.write(fd, buf)
        fcntl.ioctl(fd, UI_DEV_CREATE)
        # libinput 打开新设备需要一点时间，立即发出的事件会丢失
        time.sleep(0.8)
        return fd
    except Exception:
        os.close(fd)
        raise


def _uinput_fd() -> int | None:
    global _UI_FD, _UINPUT_UNAVAILABLE
    if _UI_FD is not None:
        return _UI_FD
    if _UINPUT_UNAVAILABLE:
        return None
    try:
        _UI_FD = _open_uinput()
        log.info("已创建 uinput 虚拟鼠标，鼠标输入走内核级注入")
        return _UI_FD
    except Exception as e:
        _UINPUT_UNAVAILABLE = True
        log.warning(
            f"无法创建 uinput 虚拟鼠标（{e}），鼠标回退到 XTEST 注入；"
            "若点击位置不准，请将当前用户加入 input 组后重新登录："
            "sudo gpasswd -a $USER input"
        )
        return None


_INPUT_EVENT = struct.Struct("=QQHHi")
"""struct input_event（64 位：timeval 16 字节 + type/code/value），长度必须精确，
否则 uinput 的 write 会返回 EINVAL"""


def _emit(*events: tuple[int, int, int]) -> None:
    for type_, code, value in events:
        os.write(_UI_FD, _INPUT_EVENT.pack(0, 0, type_, code, value))
    os.write(_UI_FD, _INPUT_EVENT.pack(0, 0, _EV_SYN, _EV_SYN, 0))


def _abs_move(x: int, y: int) -> bool:
    """移动真实光标到屏幕坐标 (x, y)。

    KDE Wayland 下 XTEST 仿真移动无效、XWarpPointer 只动 X 侧光标，
    两者都无法移动真实光标，因此依次尝试：
    1. XTEST 移动（X11 会话下可靠），用 KWin 读回验证是否生效；
    2. uinput 相对位移（需用户在 input 组，KWin 才能读取虚拟设备）。
    """
    global _XTEST_MOTION_OK, _UINPUT_UNAVAILABLE
    cur = _real_cursor_pos()
    if cur is None:
        return False

    if _XTEST_MOTION_OK is not False:
        _xtest_motion(x, y)
        time.sleep(0.15)
        cur2 = _real_cursor_pos()
        if cur2 is not None and abs(cur2[0] - x) <= 2 and abs(cur2[1] - y) <= 2:
            _XTEST_MOTION_OK = True
            return True
        if _XTEST_MOTION_OK is None:
            _XTEST_MOTION_OK = False
            log.debug("XTEST 移动在此合成器上无效，改用 uinput")

    if _uinput_fd() is None or _UINPUT_UNAVAILABLE:
        _warp(x, y)
        return False

    tlx, tly = x / _cursor_scale(), y / _cursor_scale()
    for _ in range(3):
        cur = _real_cursor_pos()
        if cur is None:
            return False
        dx, dy = int(tlx - cur[0]), int(tly - cur[1])
        if abs(dx) <= 1 and abs(dy) <= 1:
            return True
        _emit((_EV_REL, _REL_X, dx), (_EV_REL, _REL_Y, dy))
        time.sleep(0.15)
    return False


def _xtest_motion(x: int, y: int) -> None:
    """XTEST 仿真移动（仅部分合成器支持；KWin Wayland 下无效）"""
    scale = _cursor_scale() if _KWIN_CURSOR_OK else 1.0
    lx, ly = int(x / scale), int(y / scale)
    xtest.fake_input(_dpy(), X.MotionNotify, x=lx, y=ly)
    _dpy().flush()


def _left_press() -> None:
    # 按键统一走 XTEST：在真实光标位置触发按下（uinput 按键在部分
    # KDE Wayland 上不投递给游戏窗口，实测 XTEST 按键可靠）
    _button_press()


def _left_release() -> None:
    time.sleep(0.02)
    _button_release()


def _left_click() -> None:
    _left_press()
    _left_release()


# ---------------------------------------------------------------- 输入类


class LinuxInput(AbstractInput, metaclass=SingletonMeta):
    """基于 Xlib/uinput 的输入类, 仅支持前台操作"""

    @overload
    def pos_offset(self, x: int, y: int) -> tuple[int, int]: ...
    @overload
    def pos_offset(self, pos: tuple[int, int]) -> tuple[int, int]: ...

    def pos_offset(self, *args) -> tuple[int, int]:  # type: ignore
        """根据当前窗口位置偏移点击位置"""
        if len(args) == 2:
            x, y = args
        elif isinstance(args[0], tuple):
            x, y = args[0]
        else:
            raise ValueError("pos_offset 接受两个整数参数或一个包含两个整数的元组")
        real_x, real_y, _, _ = screen.handle.rect(True)
        return x + real_x, y + real_y

    def get_mouse_position(self) -> tuple[int, int]:
        """获取鼠标当前位置（X11 异常时返回 (0, 0)）"""
        try:
            if _use_pyautogui_mouse():
                pos = pyautogui.position()
                return int(pos.x), int(pos.y)
            return _query_pointer()
        except Exception:
            log.debug("获取鼠标位置失败，返回 (0, 0)")
            return (0, 0)

    def mouse_click(self, x, y, times=1, move_back=False) -> bool:
        if move_back:
            current_mouse_position = self.get_mouse_position()

        msg = f"点击位置:({x},{y})"
        log.debug(msg, stacklevel=2)
        x, y = self.pos_offset(x, y)
        for i in range(times):
            if _use_pyautogui_mouse():
                pyautogui.click(x, y)
            else:
                _abs_move(x, y)
                time.sleep(0.05)
                _left_click()
                time.sleep(0.05)

        if move_back and current_mouse_position:
            self.mouse_move(current_mouse_position)

        self.wait_pause()

        return True

    def mouse_drag_down(self, x, y, reverse=1, move_back=True) -> None:
        if move_back:
            current_mouse_position = self.get_mouse_position()

        scale = cfg.set_win_size / 1080
        x, y = self.pos_offset(x, y)
        if _use_pyautogui_mouse():
            pyautogui.moveTo(x, y)
            pyautogui.mouseDown()
            pyautogui.moveTo(x, y + int(300 * scale * reverse), duration=0.4)
            pyautogui.mouseUp()
        else:
            _abs_move(x, y)
            time.sleep(0.1)
            _left_press()
            time.sleep(0.1)
            _abs_move(x, y + int(300 * scale * reverse))
            time.sleep(0.4)
            _left_release()

        if move_back and current_mouse_position:
            self.mouse_move(current_mouse_position)

    def mouse_drag(self, x, y, drag_time=0.1, dx=0, dy=0, move_back=True) -> None:
        if move_back:
            current_mouse_position = self.get_mouse_position()
        x, y = self.pos_offset(x, y)
        if _use_pyautogui_mouse():
            pyautogui.moveTo(x, y)
            pyautogui.mouseDown()
            pyautogui.moveTo(x + dx, y + dy, duration=drag_time)
            if drag_time * 0.3 > 0.5:
                time.sleep(drag_time * 0.3)
            else:
                time.sleep(0.5)
            pyautogui.mouseUp()
        else:
            _abs_move(x, y)
            time.sleep(0.1)
            _left_press()
            time.sleep(0.1)
            _abs_move(x + dx, y + dy)
            if drag_time * 0.3 > 0.5:
                time.sleep(drag_time * 0.3)
            else:
                time.sleep(0.5)
            _left_release()

        if move_back and current_mouse_position:
            self.mouse_move(current_mouse_position)

    def mouse_swipe_for_scroll(self, x, y, duration=0.3, dx=0, dy=0, move_back=True) -> None:
        if move_back:
            current_mouse_position = self.get_mouse_position()

        raw_plan, settle_duration = build_windows_scroll_swipe_plan(
            x, y, dx, dy, duration
        )
        plan = [
            (self.pos_offset(*point), move_duration)
            for point, move_duration in raw_plan
        ]
        if _use_pyautogui_mouse():
            pyautogui.moveTo(*plan[0][0])
            pyautogui.mouseDown()
            for point, move_duration in plan[1:]:
                pyautogui.moveTo(*point, duration=move_duration)
            if settle_duration:
                time.sleep(settle_duration)
            pyautogui.mouseUp()
        else:
            _abs_move(*plan[0][0])
            time.sleep(0.1)
            _left_press()
            for point, move_duration in plan[1:]:
                _abs_move(*point)
                time.sleep(move_duration)
            if settle_duration:
                time.sleep(settle_duration)
            _left_release()

        if move_back and current_mouse_position:
            self.mouse_move(current_mouse_position)

    def mouse_scroll(self, direction: int = -3) -> bool:
        if direction <= 0:
            msg = "鼠标滚动滚轮，远离界面"
        else:
            msg = "鼠标滚动滚轮，拉近界面"
        log.debug(msg, stacklevel=2)
        if _use_pyautogui_mouse():
            pyautogui.scroll(direction)
        else:
            button = 4 if direction > 0 else 5
            for _ in range(abs(direction) or 1):
                _button_press(button)
                _button_release(button)
                time.sleep(0.05)
        return True

    def mouse_click_blank(self, coordinate=(1, 1), times=1, move_back=False) -> bool:
        if move_back:
            current_mouse_position = self.get_mouse_position()

        msg = "点击（1，1）空白位置"
        log.debug(msg, stacklevel=2)
        x = coordinate[0] + random.randint(0, 10)
        y = coordinate[1] + random.randint(0, 10)
        x, y = self.pos_offset(x, y)
        for i in range(times):
            if _use_pyautogui_mouse():
                pyautogui.click(x, y)
            else:
                _abs_move(x, y)
                time.sleep(0.05)
                _left_click()

        if move_back and current_mouse_position:
            self.mouse_move(current_mouse_position)

        self.wait_pause()
        return True

    def mouse_to_blank(self, coordinate=(1, 1), move_back=False) -> None:
        if move_back:
            current_mouse_position = self.get_mouse_position()

        msg = "鼠标移动到空白，避免遮挡"
        log.debug(msg, stacklevel=2)
        # 移动到游戏窗口内的空白角，而不是屏幕 (1,1)
        x, y = self.pos_offset(*coordinate)
        if _use_pyautogui_mouse():
            pyautogui.moveTo(x, y)
        else:
            _abs_move(x, y)

        if move_back and current_mouse_position:
            self.mouse_move(current_mouse_position)
        self.wait_pause()

    def mouse_move(self, coordinate=(1, 1)) -> None:
        """鼠标移动到指定坐标（屏幕绝对坐标）

        Args:
            coordinate (tuple): 坐标元组 (x, y)
        """
        if _use_pyautogui_mouse():
            pyautogui.moveTo(int(coordinate[0]), int(coordinate[1]))
        else:
            _abs_move(int(coordinate[0]), int(coordinate[1]))
        self.wait_pause()

    def mouse_drag_link(self, position: list, drag_time=0.1, move_back=False) -> None:
        if move_back:
            current_mouse_position = self.get_mouse_position()

        x, y = self.pos_offset(position[0][0], position[0][1])
        if _use_pyautogui_mouse():
            pyautogui.moveTo(x, y)
            pyautogui.mouseDown()
            for pos in position:
                x, y = self.pos_offset(pos[0], pos[1])
                pyautogui.moveTo(x, y, duration=drag_time)
            pyautogui.mouseUp()
        else:
            _abs_move(x, y)
            time.sleep(0.1)
            _left_press()
            for pos in position:
                x, y = self.pos_offset(pos[0], pos[1])
                _abs_move(x, y)
                time.sleep(drag_time)
            _left_release()

        if move_back and current_mouse_position:
            self.mouse_move(current_mouse_position)

    def key_press(self, key):
        return pyautogui.press(key)

    def input_text(self, text: str):
        """将 `text` 粘贴到前台窗口。仅用于前台操作，内部使用 `pyperclip.copy` + Ctrl+V，
        在 `pyperclip.copy` 失败时回退到直接打字。"""
        if not text:
            log.warning("未提供要粘贴的文本")
            return
        try:
            pyperclip.copy(text)
        except Exception:
            try:
                pyautogui.typewrite(text)
                return
            except Exception:
                log.error("pyautogui 直接输入失败")
                return
        pyautogui.hotkey("ctrl", "v")
