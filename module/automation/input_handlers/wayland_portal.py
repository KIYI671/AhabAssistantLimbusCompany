"""Wayland 前台输入，通过 XDG RemoteDesktop portal 获取用户授权。

窗口定位和截图仍由 XWayland 完成。portal 的显示器逻辑尺寸用于换算
X 坐标，不能将物理像素直接传给 NotifyPointerMotionAbsolute。
https://flatpak.github.io/xdg-desktop-portal/docs/doc-org.freedesktop.portal.RemoteDesktop.html
"""

from __future__ import annotations

import asyncio
import atexit
import threading
import time
import uuid
from collections.abc import Coroutine
from concurrent.futures import TimeoutError as FutureTimeoutError
from dataclasses import dataclass
from typing import Any

from dbus_next import Message, MessageType, Variant
from dbus_next.aio import MessageBus
from Xlib import XK

from module.logger import log

_PORTAL = "org.freedesktop.portal.Desktop"
_PATH = "/org/freedesktop/portal/desktop"
_REMOTE = "org.freedesktop.portal.RemoteDesktop"
_SCREENCAST = "org.freedesktop.portal.ScreenCast"
_REQUEST = "org.freedesktop.portal.Request"
_SESSION = "org.freedesktop.portal.Session"
_DBUS = "org.freedesktop.DBus"


class WaylandPortalError(RuntimeError):
    """授权或输入失败，交给任务线程处理，不能静默回退到 XTEST。"""


def _unwrap(value):
    if isinstance(value, Variant):
        return _unwrap(value.value)
    if isinstance(value, dict):
        return {key: _unwrap(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_unwrap(item) for item in value]
    return value


@dataclass(frozen=True)
class MonitorMapping:
    node: int
    rect: tuple[int, int, int, int]
    size: tuple[int, int]

    def contains(self, x: float, y: float) -> bool:
        left, top, right, bottom = self.rect
        return left <= x < right and top <= y < bottom

    def translate(self, x: float, y: float) -> tuple[int, float, float]:
        left, top, right, bottom = self.rect
        return self.node, (x - left) * self.size[0] / (right - left), (y - top) * self.size[1] / (bottom - top)


def map_monitors(streams: list, monitors: list[dict]) -> list[MonitorMapping]:
    """将已授权的屏幕与 XRandR 输出对应，不猜测多屏布局。

    KDE 的 mapping_id 是输出名称；其他后端在单屏或坐标空间相同的
    情况下也可对应。无法确定的多屏组合必须拒绝，以免点到另一块屏幕。
    """
    mappings = []
    used = set()
    for node, raw_properties in streams:
        properties = _unwrap(raw_properties)
        if properties.get("source_type", 1) != 1:
            raise WaylandPortalError("请在 Wayland 授权窗口中选择显示器，而不是单个窗口")
        size = properties.get("size")
        if not size or len(size) != 2 or min(size) <= 0:
            raise WaylandPortalError("桌面 portal 未返回显示器逻辑尺寸，无法准确定位鼠标")
        matching = [monitor for monitor in monitors if monitor["name"] == properties.get("mapping_id")]
        if not matching and len(monitors) == 1 and len(streams) == 1:
            matching = monitors
        if not matching and "position" in properties:
            x, y = properties["position"]
            rect = (x, y, x + size[0], y + size[1])
            matching = [monitor for monitor in monitors if monitor["rect"] == rect]
        if len(matching) != 1:
            raise WaylandPortalError("无法对应 Wayland 与 XWayland 的显示器；请使用单屏，或支持输出映射的 KDE portal")
        rect = tuple(matching[0]["rect"])
        if rect[2] <= rect[0] or rect[3] <= rect[1] or rect in used:
            raise WaylandPortalError("显示器区域无效或重复，无法准确定位鼠标")
        used.add(rect)
        mappings.append(MonitorMapping(int(node), rect, tuple(size)))
    if not mappings:
        raise WaylandPortalError("未授权任何显示器，请选择游戏所在的显示器")
    return mappings


_KEY_NAMES = {
    "enter": "Return",
    "return": "Return",
    "esc": "Escape",
    "escape": "Escape",
    "ctrl": "Control_L",
    "ctrlleft": "Control_L",
    "ctrlright": "Control_R",
    "alt": "Alt_L",
    "altleft": "Alt_L",
    "altright": "Alt_R",
    "shift": "Shift_L",
    "shiftleft": "Shift_L",
    "shiftright": "Shift_R",
    "win": "Super_L",
    "winleft": "Super_L",
    "winright": "Super_R",
    "backspace": "BackSpace",
    "delete": "Delete",
    "del": "Delete",
    "insert": "Insert",
    "tab": "Tab",
    "space": "space",
    "up": "Up",
    "down": "Down",
    "left": "Left",
    "right": "Right",
    "home": "Home",
    "end": "End",
    "pageup": "Page_Up",
    "pgup": "Page_Up",
    "pagedown": "Page_Down",
    "pgdn": "Page_Down",
    "capslock": "Caps_Lock",
    "\n": "Return",
    "\r": "Return",
    "\t": "Tab",
}


def key_to_keysym(key: str) -> int:
    if key in _KEY_NAMES:
        return XK.string_to_keysym(_KEY_NAMES[key])
    if len(key) == 1:
        code = ord(key)
        return code if code <= 0xFF else 0x01000000 | code
    name = key.upper() if key.lower().startswith("f") and key[1:].isdigit() else key
    keysym = XK.string_to_keysym(name)
    if not keysym:
        raise ValueError(f"不支持的键名: {key}")
    return keysym


class PortalInput:
    """将同步业务输入转交给独立 asyncio 线程，避免阻塞 Qt 主线程。"""

    def __init__(self):
        self._loop = None
        self._thread = None
        self._thread_lock = threading.Lock()
        self._operation_lock = None
        self._futures = set()
        self._bus = None
        self._pending = {}
        self._early_responses = {}
        self._session = ""
        self._active = False
        self._streams = []
        self._mappings = []
        self._pressed_keys = set()
        self._pressed_buttons = set()

    async def _serialize(self, coroutine):
        if self._operation_lock is None:
            self._operation_lock = asyncio.Lock()
        try:
            async with self._operation_lock:
                return await coroutine
        finally:
            coroutine.close()

    def _run_loop(self):
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_forever()
        finally:
            self._loop.close()

    def _submit(self, coroutine):
        with self._thread_lock:
            if self._loop is None:
                self._loop = asyncio.new_event_loop()
                self._thread = threading.Thread(target=self._run_loop, name="AALC Wayland portal", daemon=True)
                self._thread.start()
        future = asyncio.run_coroutine_threadsafe(self._serialize(coroutine), self._loop)
        self._futures.add(future)
        future.add_done_callback(self._futures.discard)
        return future

    def _run(self, coroutine: Coroutine[Any, Any, Any], timeout: float = 15):
        future = self._submit(coroutine)
        try:
            return future.result(timeout)
        except FutureTimeoutError as error:
            future.cancel()
            raise WaylandPortalError("Wayland 桌面授权或输入超时，请重试任务") from error

    async def _call(self, interface, member, signature="", body=None, *, path=_PATH, destination=_PORTAL):
        reply = await asyncio.wait_for(
            self._bus.call(
                Message(
                    destination=destination,
                    path=path,
                    interface=interface,
                    member=member,
                    signature=signature,
                    body=body or [],
                )
            ),
            10,
        )
        if reply.message_type == MessageType.ERROR:
            detail = reply.body[0] if reply.body else reply.error_name
            raise WaylandPortalError(f"Wayland portal {member} 失败: {detail}")
        return reply.body

    async def _connect(self):
        if self._bus is not None and self._bus.connected:
            return
        self._active = False
        self._session = ""
        self._bus = await MessageBus().connect()
        self._bus.add_message_handler(self._on_message)
        for interface, member in ((_REQUEST, "Response"), (_SESSION, "Closed")):
            rule = f"type='signal',sender='{_PORTAL}',interface='{interface}',member='{member}'"
            await self._call(_DBUS, "AddMatch", "s", [rule], path="/org/freedesktop/DBus", destination=_DBUS)

    def _on_message(self, message):
        if message.message_type != MessageType.SIGNAL:
            return
        if message.interface == _REQUEST and message.member == "Response":
            future = self._pending.get(message.path)
            if future is not None:
                if not future.done():
                    future.set_result(message.body)
            elif self._pending:
                self._early_responses[message.path] = message.body
        elif message.interface == _SESSION and message.member == "Closed" and message.path == self._session:
            self._active = False
            self._session = ""
            self._mappings = []
            self._pressed_keys.clear()
            self._pressed_buttons.clear()
            for future in self._pending.values():
                if not future.done():
                    future.set_exception(WaylandPortalError("Wayland 桌面授权已撤销，请重新启动任务并授权"))

    async def _request(self, interface, member, signature, body, options=None):
        token = "aalc_" + uuid.uuid4().hex
        options = {**(options or {}), "handle_token": Variant("s", token)}
        sender = self._bus.unique_name[1:].replace(".", "_")
        expected_path = f"{_PATH}/request/{sender}/{token}"
        path = expected_path
        future = asyncio.get_running_loop().create_future()
        self._pending[path] = future
        try:
            result = await self._call(interface, member, signature + "a{sv}", [*body, options])
            path = result[0]
            self._pending[path] = future
            if path in self._early_responses and not future.done():
                future.set_result(self._early_responses.pop(path))
            response, results = await asyncio.wait_for(future, 120)
            if response != 0:
                raise WaylandPortalError("Wayland 桌面授权被取消或拒绝，请重新启动任务并允许键盘、鼠标控制")
            return _unwrap(results)
        except (asyncio.CancelledError, TimeoutError):
            try:
                await self._call(_REQUEST, "Close", path=path)
            except Exception:
                pass
            raise
        finally:
            self._pending.pop(expected_path, None)
            self._pending.pop(path, None)
            self._early_responses.clear()

    async def _prepare(self, monitors):
        await self._connect()
        if self._active:
            await self._release_inputs()
            self._mappings = map_monitors(self._streams, monitors)
            return
        try:
            available = await self._call(
                "org.freedesktop.DBus.Properties", "Get", "ss", [_REMOTE, "AvailableDeviceTypes"]
            )
            if _unwrap(available[0]) & 3 != 3:
                raise WaylandPortalError(
                    "桌面 portal 不支持键盘和鼠标控制，请安装当前桌面对应的 RemoteDesktop portal 后端"
                )
            result = await self._request(
                _REMOTE,
                "CreateSession",
                "",
                [],
                {
                    "session_handle_token": Variant("s", "aalc_" + uuid.uuid4().hex),
                },
            )
            self._session = result["session_handle"]
            await self._request(_REMOTE, "SelectDevices", "o", [self._session], {"types": Variant("u", 3)})
            await self._request(
                _SCREENCAST,
                "SelectSources",
                "o",
                [self._session],
                {
                    "types": Variant("u", 1),
                    "multiple": Variant("b", True),
                },
            )
            log.info("请在系统授权窗口中允许键盘、鼠标控制，并选择游戏所在的显示器")
            result = await self._request(_REMOTE, "Start", "os", [self._session, ""])
            if result.get("devices", 0) & 3 != 3:
                raise WaylandPortalError("未授权键盘和鼠标控制，任务无法继续")
            self._streams = result.get("streams", [])
            self._mappings = map_monitors(self._streams, monitors)
            self._active = True
            log.info("Wayland 桌面输入已授权，使用 portal 控制鼠标和键盘")
        except BaseException:
            await self._close_session()
            raise

    def prepare(self, monitors: list[dict]) -> None:
        try:
            self._run(self._prepare(monitors), timeout=150)
        except WaylandPortalError:
            raise
        except Exception as error:
            raise WaylandPortalError(
                f"无法连接 Wayland 桌面输入服务，请检查 xdg-desktop-portal 及桌面后端: {error}"
            ) from error

    async def _notify(self, member, signature, body):
        if not self._active or self._bus is None or not self._bus.connected:
            raise WaylandPortalError("Wayland 桌面输入未授权或授权已撤销，请重新启动任务并授权")
        pressed = self._pressed_keys if member == "NotifyKeyboardKeysym" else self._pressed_buttons
        if member in ("NotifyKeyboardKeysym", "NotifyPointerButton"):
            code, state = body
            if state:
                # 请求送出后任务可能被强制终止，提前记录以便清理潜在按下状态。
                pressed.add(code)
        await self._call(_REMOTE, member, "oa{sv}" + signature, [self._session, {}, *body])
        if member in ("NotifyKeyboardKeysym", "NotifyPointerButton"):
            if not state:
                pressed.discard(code)

    async def _move(self, x, y):
        if not self._active:
            raise WaylandPortalError("Wayland 桌面输入未授权或授权已撤销，请重新启动任务并授权")
        for mapping in self._mappings:
            if mapping.contains(x, y):
                await self._notify("NotifyPointerMotionAbsolute", "udd", list(mapping.translate(x, y)))
                return
        raise WaylandPortalError("目标位置不在已授权的显示器内；请将游戏移回已授权屏幕，或重新启动任务并选择该屏幕")

    def move(self, x: int, y: int) -> None:
        self._run(self._move(x, y))

    def button(self, pressed: bool) -> None:
        self._run(self._notify("NotifyPointerButton", "iu", [0x110, int(pressed)]))

    def scroll(self, direction: int) -> None:
        if direction:
            self._run(self._notify("NotifyPointerAxisDiscrete", "ui", [0, -int(direction)]))

    def hotkey(self, *keys: str) -> None:
        keysyms = [key_to_keysym(key) for key in keys]
        pressed = []
        try:
            for keysym in keysyms:
                self._run(self._notify("NotifyKeyboardKeysym", "iu", [keysym, 1]))
                pressed.append(keysym)
                time.sleep(0.01)
        finally:
            try:
                for keysym in reversed(pressed):
                    self._run(self._notify("NotifyKeyboardKeysym", "iu", [keysym, 0]))
            finally:
                self.release_inputs()

    def type_text(self, text: str) -> None:
        for character in text:
            self.hotkey(character)

    async def _release_inputs(self):
        if not self._active:
            return
        for member, pressed in (
            ("NotifyPointerButton", self._pressed_buttons),
            ("NotifyKeyboardKeysym", self._pressed_keys),
        ):
            for code in list(pressed):
                try:
                    await self._notify(member, "iu", [code, 0])
                except Exception as error:
                    log.debug(f"释放 Wayland 输入失败: {error}")

    def release_inputs(self) -> None:
        """业务线程被强制终止后，由独立 portal 线程释放残留按钮和修饰键。"""
        if self._loop is not None:
            self._run(self._release_inputs())

    def reset(self) -> None:
        """取消被终止业务线程留下的授权请求，异步清理，避免卡住 GUI。"""
        if self._loop is None:
            return
        for future in list(self._futures):
            future.cancel()
        self._submit(self._close_session())

    async def _close_session(self):
        await self._release_inputs()
        self._active = False
        session, self._session = self._session, ""
        self._mappings = []
        self._streams = []
        self._pressed_keys.clear()
        self._pressed_buttons.clear()
        if session and self._bus is not None and self._bus.connected:
            try:
                await self._call(_SESSION, "Close", path=session)
            except Exception:
                pass

    async def _shutdown(self):
        await self._close_session()
        if self._bus is not None and self._bus.connected:
            # 先断开连接再停止事件循环，让 portal 回收该进程的会话。
            self._bus.disconnect()
            await self._bus.wait_for_disconnect()

    def close(self):
        if self._loop is None or self._loop.is_closed():
            return
        try:
            for future in list(self._futures):
                future.cancel()
            self._run(self._shutdown())
        except Exception:
            pass
        finally:
            self._loop.call_soon_threadsafe(self._loop.stop)
            self._thread.join(timeout=1)


portal_input = PortalInput()
atexit.register(portal_input.close)
