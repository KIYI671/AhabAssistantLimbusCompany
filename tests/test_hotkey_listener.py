"""全局快捷键必须复用进程内唯一的 pynput 键盘监听。

macOS 上 pynput 的键盘监听要走 Carbon TIS：一旦进程里出现第二个存活的监听线程
（新建监听时旧监听还没退干净就算），监听线程会在 TSMGetInputSourceProperty 里撞上
dispatch_assert_queue 断言，以 SIGTRAP 直接杀掉整个进程——这正是自动战斗小工具
曾经的崩溃原因。这里用假监听锁定：注册/注销/暂停/恢复都只改快捷键表，绝不重建监听，
并且派发、后注册者优先、暂停期间不触发这些行为都正确。
"""

import types

from pynput import keyboard

from module import hotkey_listener


class _FakeListener:
    """假监听：只记录创建/启动，不建立任何真实监听线程。"""

    instances: list["_FakeListener"] = []

    def __init__(self, on_press=None, on_release=None):
        self.on_press = on_press
        self.on_release = on_release
        self.started = False
        _FakeListener.instances.append(self)

    def canonical(self, key):
        return key

    def start(self):
        self.started = True

    def stop(self):
        self.started = False


def _make_hotkeys(monkeypatch) -> hotkey_listener.GlobalHotKeys:
    _FakeListener.instances = []
    monkeypatch.setattr(
        hotkey_listener,
        "keyboard",
        types.SimpleNamespace(
            Key=keyboard.Key,
            KeyCode=keyboard.KeyCode,
            HotKey=keyboard.HotKey,
            Listener=_FakeListener,
        ),
    )
    manager = hotkey_listener.GlobalHotKeys()
    return manager


def _press(listener: _FakeListener, *keys) -> None:
    for key in keys:
        listener.on_press(key)
    for key in reversed(keys):
        listener.on_release(key)


def _shortcut(char: str):
    return keyboard.Key.ctrl, keyboard.KeyCode.from_char(char)


def test_所有注册共用同一个监听(monkeypatch):
    manager = _make_hotkeys(monkeypatch)
    calls = []

    manager.register(lambda: {"<ctrl>+q": lambda: calls.append("q")})
    manager.register(lambda: {"<ctrl>+a": lambda: calls.append("a")})

    assert len(_FakeListener.instances) == 1
    listener = _FakeListener.instances[0]
    assert listener.started

    _press(listener, *_shortcut("q"))
    _press(listener, *_shortcut("a"))

    assert calls == ["q", "a"]


def test_后注册者占用同一快捷键(monkeypatch):
    manager = _make_hotkeys(monkeypatch)
    first, second = [], []

    manager.register(lambda: {"<ctrl>+q": lambda: first.append(1)})
    manager.register(lambda: {"<ctrl>+q": lambda: second.append(1)})

    _press(_FakeListener.instances[0], *_shortcut("q"))

    assert second == [1]
    assert first == []


def test_注销后快捷键回到先注册者(monkeypatch):
    manager = _make_hotkeys(monkeypatch)
    first, second = [], []

    manager.register(lambda: {"<ctrl>+q": lambda: first.append(1)})
    token = manager.register(lambda: {"<ctrl>+q": lambda: second.append(1)})
    manager.unregister(token)

    listener = _FakeListener.instances[0]
    _press(listener, *_shortcut("q"))

    assert first == [1]
    assert second == []
    assert len(_FakeListener.instances) == 1


def test_暂停期间不派发且恢复时重读快捷键(monkeypatch):
    manager = _make_hotkeys(monkeypatch)
    calls = []
    hotkey = {"name": "<ctrl>+q"}

    manager.register(lambda: {hotkey["name"]: lambda: calls.append(1)})
    listener = _FakeListener.instances[0]

    manager.stop()
    _press(listener, *_shortcut("q"))
    assert calls == []

    hotkey["name"] = "<ctrl>+w"  # 相当于用户刚在设置里改了快捷键
    manager.start()
    _press(listener, *_shortcut("q"))
    _press(listener, *_shortcut("w"))

    assert calls == [1]
    assert len(_FakeListener.instances) == 1
