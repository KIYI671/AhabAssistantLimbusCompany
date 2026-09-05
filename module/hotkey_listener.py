from __future__ import annotations

from collections.abc import Callable

from module.logger import log

try:
    from pynput import keyboard
except ImportError:
    log.warning("pynput 不可用（无 X11 会话或缺少依赖），全局热键已禁用")
    keyboard = None

if keyboard is not None:

    _MODIFIER_KEYS = {
        keyboard.Key.alt,
        keyboard.Key.alt_gr,
        keyboard.Key.cmd,
        keyboard.Key.ctrl,
        keyboard.Key.shift,
    }

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

    class ExactGlobalHotKeys(keyboard.Listener):
        def __init__(self, hotkeys: dict[str, Callable[[], None]], *args, **kwargs):
            self._pressed_keys: set[keyboard.Key | keyboard.KeyCode] = set()
            self._hotkeys = [
                _ExactHotKey(keyboard.HotKey.parse(hotkey), callback) for hotkey, callback in hotkeys.items()
            ]
            super().__init__(
                on_press=self._on_press,
                on_release=self._on_release,
                *args,
                **kwargs,
            )
            self.daemon = True

        def _on_press(self, key, injected=False):
            if injected:
                return

            canonical_key = self.canonical(key)
            self._pressed_keys.add(canonical_key)
            pressed_modifiers = {key for key in self._pressed_keys if key in _MODIFIER_KEYS}
            for hotkey in self._hotkeys:
                hotkey.press(canonical_key, pressed_modifiers)

        def _on_release(self, key, injected=False):
            if injected:
                return

            canonical_key = self.canonical(key)
            for hotkey in self._hotkeys:
                hotkey.release(canonical_key)
            self._pressed_keys.discard(canonical_key)

else:

    class ExactGlobalHotKeys:  # type: ignore[no-redef]
        """pynput 不可用时的空实现：保持调用方接口（构造/start/stop）可用"""

        def __init__(self, hotkeys: dict, *args, **kwargs):
            log.warning("全局热键不可用：pynput 未加载")

        def start(self) -> None:
            pass

        def stop(self) -> None:
            pass

        def join(self, *args, **kwargs) -> None:
            pass
