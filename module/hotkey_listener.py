from __future__ import annotations

import itertools
import threading
from collections.abc import Callable

from pynput import keyboard

from module.logger import log

_MODIFIER_KEYS = {
    keyboard.Key.alt,
    keyboard.Key.alt_gr,
    keyboard.Key.cmd,
    keyboard.Key.ctrl,
    keyboard.Key.shift,
}

#: 快捷键映射提供者：重建监听时现取，保证调用方能读到最新的 cfg 值。
HotkeyProvider = Callable[[], dict[str, Callable[[], None]]]


class _ExactHotKey:
    def __init__(self, keys: list[keyboard.Key | keyboard.KeyCode], on_activate: Callable[[], None]):
        self._keys = set(keys)
        self._state: set[keyboard.Key | keyboard.KeyCode] = set()
        self._required_modifiers = {key for key in self._keys if key in _MODIFIER_KEYS}
        self._is_active = False
        self._on_activate = on_activate

    def press(
        self,
        key: keyboard.Key | keyboard.KeyCode,
        pressed_modifiers: set[keyboard.Key],
    ) -> None:
        if key in self._keys:
            self._state.add(key)

        should_activate = self._state == self._keys and pressed_modifiers == self._required_modifiers
        if should_activate and not self._is_active:
            self._is_active = True
            self._on_activate()
        elif not should_activate:
            self._is_active = False

    def release(self, key: keyboard.Key | keyboard.KeyCode) -> None:
        self._state.discard(key)
        self._is_active = False


class GlobalHotKeys:
    """进程内唯一的全局快捷键监听，各组件按需注册自己的快捷键映射。

    macOS 上 pynput 的键盘监听要走 Carbon TIS：监听线程在 TSMGetInputSourceProperty
    里会撞上 dispatch_assert_queue 断言。只要进程里出现过第二个存活的监听线程
    （两个监听重叠，或者旧监听还没退干净就新建一个），就会直接以 SIGTRAP 终止整个
    进程——这正是自动战斗小工具曾经的崩溃原因。因此底层 Listener 全进程只创建一次，
    注册/注销/暂停都只改快捷键表，绝不重建监听。

    同一个快捷键被多个组件注册时，后注册者优先；关闭/销毁的组件必须
    :meth:`unregister`，否则它的回调会一直占据该快捷键。
    """

    def __init__(self):
        self._lock = threading.RLock()
        self._listener: keyboard.Listener | None = None
        self._registrations: dict[int, HotkeyProvider] = {}
        self._tokens = itertools.count()
        self._suspended = False
        # 监听线程只读、改动时整体替换，避免回调与改动互相看到半成品状态
        self._hotkeys: list[_ExactHotKey] = []
        self._pressed_keys: set[keyboard.Key | keyboard.KeyCode] = set()
        # canonical 是平台相关的实例方法（Windows 依赖监听器自身的键盘布局翻译器），
        # 只能取自那个唯一的监听器
        self._canonicalize: Callable[[keyboard.Key | keyboard.KeyCode], keyboard.Key | keyboard.KeyCode] = (
            lambda key: key
        )

    def register(self, provider: HotkeyProvider) -> int:
        """注册一组快捷键映射，返回可用于注销的 token。"""
        with self._lock:
            token = next(self._tokens)
            self._registrations[token] = provider
            self._refresh()
            return token

    def unregister(self, token: int) -> None:
        """注销 token 对应的快捷键映射；token 不存在时忽略。"""
        with self._lock:
            if self._registrations.pop(token, None) is not None:
                self._refresh()

    def stop(self) -> None:
        """暂停快捷键派发（录入新快捷键时用，避免旧快捷键被触发），保留注册。"""
        with self._lock:
            self._suspended = True
            self._refresh()

    def start(self) -> None:
        """恢复派发，并按当前注册重取快捷键（可读到最新的 cfg 值）。"""
        with self._lock:
            self._suspended = False
            self._refresh()

    def _refresh(self) -> None:
        self._hotkeys = [] if self._suspended else self._collect_hotkeys()
        if self._listener is not None or not self._hotkeys:
            return
        listener = keyboard.Listener(on_press=self._on_press, on_release=self._on_release)
        try:
            listener.start()
        except Exception as e:
            log.error(f"快捷键监听启动失败: {e}")
            return
        self._canonicalize = listener.canonical
        self._listener = listener

    def _collect_hotkeys(self) -> list[_ExactHotKey]:
        resolved: dict[str, Callable[[], None]] = {}
        for provider in self._registrations.values():
            try:
                hotkeys = provider()
            except Exception as e:
                log.error(f"读取快捷键配置失败: {e}")
                continue
            resolved.update(hotkeys)  # 后注册者覆盖先注册者

        collected = []
        for hotkey, callback in resolved.items():
            try:
                keys = keyboard.HotKey.parse(hotkey)
            except ValueError:
                log.error(f"快捷键 {hotkey} 格式无效，请确认设置的快捷键格式有效")
                continue
            collected.append(_ExactHotKey(keys, callback))
        return collected

    def _on_press(self, key, injected=False):
        if injected:
            return

        canonical_key = self._canonicalize(key)
        self._pressed_keys.add(canonical_key)
        pressed_modifiers = {key for key in self._pressed_keys if key in _MODIFIER_KEYS}
        for hotkey in self._hotkeys:
            hotkey.press(canonical_key, pressed_modifiers)

    def _on_release(self, key, injected=False):
        if injected:
            return

        canonical_key = self._canonicalize(key)
        for hotkey in self._hotkeys:
            hotkey.release(canonical_key)
        self._pressed_keys.discard(canonical_key)


#: 进程内唯一的全局快捷键监听。
global_hotkeys = GlobalHotKeys()
