"""基于 python-xlib / EWMH 的窗口管理实现，接口与 Windows 版 `Handle` 保持一致。

适用于 X11 会话或 XWayland（游戏经 Steam/Proton 运行时默认以 X11 窗口出现）。
不支持的能力（如 Win32 分层窗口的透明/鼠标穿透）以 no-op 方式降级。
"""

import time

from Xlib import XK, X, display
from Xlib.error import XError
from Xlib.ext import randr, xtest
from Xlib.protocol import event as xevent

from module.game_and_screen.screen import Handle
from module.logger import log

# WM_STATE 状态码
NormalState = 1
IconicState = 3

_MOTIF_WM_HINTS = "_MOTIF_WM_HINTS"
# Motif hints: MWM_HINTS_DECORATIONS
MWM_HINTS_DECORATIONS = 0x2


def _net_wm_state_atoms(disp):
    return [
        disp.intern_atom("_NET_WM_STATE", True),
        disp.intern_atom("_NET_WM_STATE_MAXIMIZED_VERT", True),
        disp.intern_atom("_NET_WM_STATE_MAXIMIZED_HORZ", True),
        disp.intern_atom("_NET_WM_STATE_HIDDEN", True),
        disp.intern_atom("_NET_WM_STATE_ABOVE", True),
        disp.intern_atom("_NET_WM_STATE_FULLSCREEN", True),
    ]


class X11Handle(Handle):
    """提供统一的获取窗口信息的接口（X11 实现）

    说明:
        - `hwnd` 在 X11 下是 X 窗口 XID，保持同名属性以复用上层逻辑。
        - `rect(client=True)` 返回游戏窗口自身几何在屏幕上的投影；
          `rect(client=False)` 额外包含由 `_NET_FRAME_EXTENTS` 报告的窗口装饰边框。
        - `width/height/monitor_size/mouse_pos_to_client_mouse/client_to_window/
          bring_window_into_view` 等纯几何方法直接继承自 `Handle` 基类。
    """

    def __init__(self):
        super().__init__()
        self._hwnd: int = 0
        self._transparent = False
        self._disp: display.Display | None = None
        try:
            self._disp = display.Display()
        except Exception as e:
            log.error(f"无法连接 X 显示服务器（请确认 X11/XWayland 会话）: {e}")
        self._enum_windows_list: list[str] = []

    # ------------------------------------------------------------------ 基础
    @property
    def _dpy(self) -> display.Display:
        if self._disp is None:
            self._disp = display.Display()
        return self._disp

    @property
    def _root(self):
        return self._dpy.screen().root

    def _window_obj(self, wid: int | None = None):
        """按 XID 取窗口对象，窗口已销毁时抛出 XError"""
        wid = self._hwnd if wid is None else wid
        return self._dpy.create_resource_object("window", wid)

    def _get_atom_value(self, win, atom_name: str):
        atom = self._dpy.intern_atom(atom_name, True)
        prop = win.get_full_property(atom, X.AnyPropertyType)
        if prop is None or prop.value is None or len(prop.value) == 0:
            return None
        return prop.value

    # ------------------------------------------------------------------ 查找
    def init_handle(self, title: str = "LimbusCompany", class_name: str = "UnityWndClass") -> int:
        """获取窗口句柄。优先精确匹配标题，其次模糊匹配 Limbus 相关类名/标题。"""
        self._hwnd = 0
        self._enum_windows_list.clear()
        try:
            candidates = self._enum_windows()
        except Exception as e:
            log.error(f"枚举窗口时发生错误: {e}")
            candidates = []

        title_l = (title or "").strip().lower()
        # 精确标题匹配
        for info in candidates:
            if title_l and info["title"].strip().lower() == title_l:
                self._hwnd = info["wid"]
                break
        # 模糊匹配：类名或标题含 limbus
        if self._hwnd == 0:
            for info in candidates:
                if "limbus" in info["cls"].lower() or "limbus" in info["title"].lower():
                    self._hwnd = info["wid"]
                    break

        if self._hwnd:
            info = next((c for c in candidates if c["wid"] == self._hwnd), None)
            log.debug(
                f"找到游戏窗口: wid={self._hwnd}, class={info['cls'] if info else '?'}, title={info['title'] if info else '?'}",
                stacklevel=3,
            )
        else:
            log.error("未能获取到游戏窗口", stacklevel=3)
            log.debug(f"枚举窗口列表: {self._enum_windows_list}", stacklevel=3)
        return self._hwnd

    def _enum_windows(self) -> list[dict]:
        results: list[dict] = []
        children = self._root.query_tree().children
        for win in children:
            wid = win.id
            try:
                cls = ""
                wm_class = win.get_wm_class()
                if wm_class:
                    cls = f"{wm_class[0]}.{wm_class[1]}"
                title = self._window_title(win)
                if not title and not cls:
                    continue
            except XError:
                continue
            results.append({"wid": wid, "cls": cls, "title": title or ""})
            if title:
                self._enum_windows_list.append(f"wid: {wid}, class_name: {cls}, window_text: {title}")
        return results

    def _window_title(self, win) -> str:
        value = self._get_atom_value(win, "_NET_WM_NAME")
        if value:
            try:
                return value.decode("utf-8", errors="replace")
            except Exception:
                pass
        try:
            name = win.get_wm_name()
            if isinstance(name, bytes):
                return name.decode("utf-8", errors="replace")
            return name or ""
        except Exception:
            return ""

    # ------------------------------------------------------------------ 状态
    @property
    def hwnd(self) -> int:
        """获取窗口句柄"""
        if self._hwnd == 0:
            if self._is_simulator_mode():
                log.debug("模拟器模式下无法获取窗口句柄", stacklevel=3)
            else:
                self.init_handle()
        else:
            try:
                self._window_obj(self._hwnd).get_attributes()
            except XError:
                log.warning(
                    f"窗口句柄无效，可能窗口已关闭，重新获取, 当前句柄为 {self._hwnd}", stacklevel=3
                )
                self.init_handle()
                if self._hwnd:
                    log.info(f"重新获取窗口句柄成功, 新句柄为 {self._hwnd}", stacklevel=3)
        return self._hwnd

    @staticmethod
    def _is_simulator_mode() -> bool:
        try:
            from module.config import cfg

            return bool(cfg.config.simulator)
        except Exception:
            return False

    @property
    def isTransparent(self) -> bool:
        """判断窗口是否透明（X11 不支持，仅返回内部标记）"""
        return self._transparent

    @property
    def pid(self) -> int:
        """游戏窗口所属进程 PID（用于结束游戏进程）"""
        if self.hwnd == 0:
            return 0
        try:
            value = self._get_atom_value(self._window_obj(), "_NET_WM_PID")
            return int(value[0]) if value else 0
        except Exception:
            return 0

    @property
    def isMinimized(self) -> bool:
        """判断窗口是否最小化"""
        if self.hwnd == 0:
            return False
        try:
            state = self._window_obj().get_wm_state()
            if state and "state" in state:
                return state["state"] == IconicState
        except Exception:
            pass
        return False

    @property
    def isActive(self) -> bool:
        """判断窗口是否为活动窗口"""
        if self.hwnd == 0:
            return False
        try:
            value = self._get_atom_value(self._root, "_NET_ACTIVE_WINDOW")
            return value and int(value[0]) == self._hwnd
        except Exception:
            return False

    # ------------------------------------------------------------------ 几何
    def _frame_extents(self, win) -> tuple[int, int, int, int]:
        """窗口装饰边框 (left, right, top, bottom)"""
        value = self._get_atom_value(win, "_NET_FRAME_EXTENTS")
        if value and len(value) >= 4:
            return int(value[0]), int(value[1]), int(value[2]), int(value[3])
        return 0, 0, 0, 0

    def rect(self, client: bool = False) -> tuple[int, int, int, int]:
        """获取窗口位置和大小

        Parameters
        ---
        client: bool
            是否获取客户区大小，默认为`False`
        """
        if self.hwnd == 0:
            return (0, 0, 0, 0)
        try:
            win = self._window_obj()
            geo = win.get_geometry()
            pos_x, pos_y = self._root_position(win)
            if client:
                return (pos_x, pos_y, pos_x + geo.width, pos_y + geo.height)
            left, right, top, bottom = self._frame_extents(win)
            return (
                pos_x - left,
                pos_y - top,
                pos_x + geo.width + right,
                pos_y + geo.height + bottom,
            )
        except XError as e:
            log.debug(f"获取窗口几何失败: {e}")
            return (0, 0, 0, 0)

    def _root_position(self, win) -> tuple[int, int]:
        """计算窗口原点在根窗口坐标系下的位置。

        通过父子层级几何偏移累加实现：部分合成器（如 KWin 的 XWayland 缩放）下
        TranslateCoordinates 应答不可靠，逐级累加更稳定。
        """
        x = y = 0
        current = win
        while True:
            geo = current.get_geometry()
            x += geo.x
            y += geo.y
            parent = current.query_tree().parent
            if parent is None or parent.id == self._root.id:
                break
            current = parent
        return x, y

    @property
    def monitor_info(self) -> dict:
        """获取窗口所在显示器的信息"""
        if self.hwnd == 0:
            return {
                "Monitor": (0, 0, 0, 0),
                "Work": (0, 0, 0, 0),
                "Flags": 0,
                "Device": "Unknown",
            }
        monitors = self._enumerate_monitors()
        rect = self.rect(False)
        cx, cy = (rect[0] + rect[2]) // 2, (rect[1] + rect[3]) // 2
        target = None
        for mon in monitors:
            if mon[0] <= cx < mon[2] and mon[1] <= cy < mon[3]:
                target = mon
                break
        if target is None and monitors:
            target = monitors[0]
        if target is None:
            target = (0, 0, self._root.get_geometry().width, self._root.get_geometry().height)
        return {
            "Monitor": target,
            "Work": target,
            "Flags": 0,
            "Device": f"Monitor {monitors.index(target) + 1}" if target in monitors else "Unknown",
        }

    def _enumerate_monitors(self) -> list[tuple[int, int, int, int]]:
        monitors: list[tuple[int, int, int, int]] = []
        try:
            res = randr.get_screen_resources(self._root)
            for crtc in res.crtcs:
                try:
                    info = randr.get_crtc_info(self._root, crtc, res.config_timestamp)
                except XError:
                    continue
                if info.width > 0 and info.height > 0:
                    mon = (info.x, info.y, info.x + info.width, info.y + info.height)
                    if mon not in monitors:
                        monitors.append(mon)
        except Exception as e:
            log.debug(f"RandR 枚举显示器失败，退回根窗口尺寸: {e}")
        if not monitors:
            geo = self._root.get_geometry()
            monitors = [(0, 0, geo.width, geo.height)]
        return monitors

    # ------------------------------------------------------------------ 操作
    def _send_net_wm_state(self, action: int, atoms: list) -> None:
        state_atom = self._dpy.intern_atom("_NET_WM_STATE", True)
        data = [action, atoms[0], atoms[1] if len(atoms) > 1 else 0, 0, 0]
        ev = xevent.ClientMessage(
            window=self._hwnd,
            client_type=state_atom,
            data=(32, data),
            event_mask=X.SubstructureRedirectMask | X.SubstructureNotifyMask,
        )
        self._root.send_event(ev, event_mask=X.SubstructureRedirectMask | X.SubstructureNotifyMask)
        self._dpy.flush()

    def _send_net_active(self) -> None:
        active_atom = self._dpy.intern_atom("_NET_ACTIVE_WINDOW", True)
        ev = xevent.ClientMessage(
            window=self._hwnd,
            client_type=active_atom,
            data=(32, [0, int(time.time() * 1000) & 0xFFFFFFFF, 0, 0, 0]),
            event_mask=X.SubstructureRedirectMask | X.SubstructureNotifyMask,
        )
        self._root.send_event(ev, event_mask=X.SubstructureRedirectMask | X.SubstructureNotifyMask)
        self._dpy.flush()

    def setForeground(self) -> None:
        """将窗口设为前台窗口"""
        if self.hwnd == 0:
            return
        try:
            self._send_net_active()
            self._window_obj().configure(stack_mode=X.Above)
            self._dpy.flush()
        except Exception as e:
            log.debug(f"窗口置前失败: {e}")

    def setMaximized(self, value: bool = True) -> None:
        """最大化窗口"""
        if self.hwnd == 0:
            return
        state = _net_wm_state_atoms(self._dpy)
        vert, horz = state[1], state[2]
        self._send_net_wm_state(1 if value else 0, [vert, horz])

    def switchFullScreenMode(self) -> bool:
        """切换全屏模式 (模拟 Alt+Enter，与 Windows 版行为一致)"""
        if self.hwnd == 0:
            return False
        if self.isMinimized:
            self.restore()
            time.sleep(0.5)
        try:
            # 确保窗口聚焦，XTEST 注入的按键才会送达游戏
            self.setForeground()
            time.sleep(0.2)
            alt_kc = self._dpy.keysym_to_keycode(XK.string_to_keysym("Alt_L"))
            enter_kc = self._dpy.keysym_to_keycode(XK.string_to_keysym("Return"))
            xtest.fake_input(self._dpy, X.KeyPress, alt_kc)
            self._dpy.flush()
            time.sleep(0.05)
            xtest.fake_input(self._dpy, X.KeyPress, enter_kc)
            self._dpy.flush()
            time.sleep(0.05)
            xtest.fake_input(self._dpy, X.KeyRelease, enter_kc)
            self._dpy.flush()
            xtest.fake_input(self._dpy, X.KeyRelease, alt_kc)
            self._dpy.flush()
            return True
        except Exception as e:
            log.error(f"切换全屏模式失败: {e}")
            return False

    def restore(self, activate: bool = False) -> None:
        """恢复窗口（取消最小化）"""
        if self.hwnd == 0:
            return
        try:
            if self.isMinimized:
                if activate:
                    self._send_net_active()
                else:
                    # EWMH 无“仅取消最小化不聚焦”的标准方式，退而发送状态移除 HIDDEN
                    hidden = _net_wm_state_atoms(self._dpy)[3]
                    self._send_net_wm_state(0, [hidden])
                    self._window_obj().configure(stack_mode=X.Above)
                    self._dpy.flush()
                time.sleep(0.1)
        except Exception as e:
            log.debug(f"恢复窗口失败: {e}")

    def set_window_pos(self, x: int, y: int) -> None:
        """将窗口移动到屏幕坐标 (x, y)"""
        if self.hwnd == 0:
            return
        x = int(x)
        y = int(y)
        try:
            win = self._window_obj()
            geo = win.get_geometry()
            pos_x, pos_y = self._root_position(win)
            parent_x = pos_x - geo.x
            parent_y = pos_y - geo.y
            win.configure(x=x - parent_x, y=y - parent_y)
            self._dpy.flush()
        except XError as e:
            log.debug(f"移动窗口失败: {e}")

    def set_window_size(self, width: int, height: int) -> None:
        """设置窗口（外框）大小"""
        if self.hwnd == 0:
            return
        try:
            self._window_obj().configure(width=int(width), height=int(height))
            self._dpy.flush()
        except XError as e:
            log.debug(f"设置窗口大小失败: {e}")

    def set_topmost(self, topmost: bool) -> None:
        """设置窗口是否始终置顶"""
        if self.hwnd == 0:
            return
        above = _net_wm_state_atoms(self._dpy)[4]
        self._send_net_wm_state(1 if topmost else 0, [above])

    def set_decorated(self, keep_caption: bool = True) -> None:
        """去除窗口装饰（边框/标题栏/最大化按钮），keep_caption 决定是否保留标题栏。

        通过设置 _MOTIF_WM_HINTS 实现，主流窗口管理器（Mutter/KWin/XFWM）均支持。
        """
        if self.hwnd == 0:
            return
        try:
            win = self._window_obj()
            # MWM_HINTS_DECORATIONS 生效时 decorations=1(MWM_DECOR_ALL) 保留装饰, 0 全部去除
            decorations = 1 if keep_caption else 0
            hints = (MWM_HINTS_DECORATIONS, 0, decorations, 0, 0)
            prop = self._dpy.intern_atom(_MOTIF_WM_HINTS, False)
            from Xlib import Xatom

            win.change_property(prop, Xatom.CARDINAL, 32, hints)
            self._dpy.flush()
        except Exception as e:
            log.debug(f"设置窗口装饰失败: {e}")

    def set_window_transparent(self, transparent: bool = True) -> None:
        """设置窗口透明（X11 下无 Win32 分层窗口等价物，仅记录状态）"""
        if self.hwnd == 0:
            return
        if not self._transparent and transparent:
            log.debug("Linux 下不支持窗口透明/鼠标穿透，已跳过")
        self._transparent = transparent

    def capture_window_image(self):
        """直接从 X 服务器读取窗口内容（对被遮挡的窗口通常也有效）。

        Returns:
            PIL.Image 或 None
        """
        if self.hwnd == 0:
            return None
        try:
            from PIL import Image

            win = self._window_obj()
            geo = win.get_geometry()
            img = win.get_image(0, 0, geo.width, geo.height, X.ZPixmap, 0xFFFFFFFF)
            if geo.depth in (24, 32):
                return Image.frombytes("RGB", (geo.width, geo.height), img.data, "raw", "BGRX")
            if geo.depth == 16:
                return Image.frombytes("RGB", (geo.width, geo.height), img.data, "raw", "BGR;16")
            log.debug(f"不支持的窗口颜色深度: {geo.depth}")
            return None
        except Exception as e:
            log.debug(f"读取窗口图像失败: {e}")
            return None
