"""AALC 启动时先预热一次按键注入，把首次注入的一次性成本提前付掉。

首次注入要现付「反查游戏进程」与「macOS 首次跨进程投递的隐私检查」，实测比后续注入慢一倍
以上；战斗中 P 与 Enter 只隔 0.5s，首次注入变慢会把这一对拆开。这里锁定：预热投一次且只投
一次、用的键不是游戏绑定的键（否则启动瞬间就会误触游戏）、定位不到游戏进程时跳过并在下次
设备初始化时补上。
"""

import pytest

from module.automation.input_handlers.macos import macos_keyboard
from module.automation.input_handlers.macos.macos_keyboard import (
    _WARMUP_KEYCODE,
    KEYCODES,
)


class _FakeQuartz:
    kCGEventSourceStateHIDSystemState = 1

    def __init__(self):
        self.posted: list[tuple[int, int, bool]] = []

    def CGEventSourceCreate(self, _state):
        return "source"

    def CGEventCreateKeyboardEvent(self, _source, keycode, down):
        return keycode, down

    def CGEventPostToPid(self, pid, event):
        self.posted.append((pid, *event))


@pytest.fixture
def warmup_env(monkeypatch):
    quartz = _FakeQuartz()
    monkeypatch.setattr(macos_keyboard, "Quartz", quartz)
    monkeypatch.setattr(macos_keyboard, "AXIsProcessTrusted", lambda: True)
    monkeypatch.setattr(macos_keyboard, "sleep", lambda *_: None)
    monkeypatch.setattr(macos_keyboard, "_warmed_up", False)
    return quartz


def test_预热注入用的键不是游戏绑定的键():
    assert _WARMUP_KEYCODE not in KEYCODES.values()


def test_预热只注入一次(warmup_env, monkeypatch):
    monkeypatch.setattr(macos_keyboard, "game_pid", lambda host, port: 4321)

    assert macos_keyboard.warm_up("127.0.0.1", 1313) is True
    assert warmup_env.posted == [(4321, _WARMUP_KEYCODE, True), (4321, _WARMUP_KEYCODE, False)]

    # 每次 init_game 重建连接都会再调一次，但不该再注入
    assert macos_keyboard.warm_up("127.0.0.1", 1313) is True
    assert len(warmup_env.posted) == 2


def test_定位不到游戏进程时跳过并在下次补上(warmup_env, monkeypatch):
    monkeypatch.setattr(macos_keyboard, "game_pid", lambda host, port: None)
    assert macos_keyboard.warm_up("127.0.0.1", 1313) is False
    assert warmup_env.posted == []

    monkeypatch.setattr(macos_keyboard, "game_pid", lambda host, port: 777)
    assert macos_keyboard.warm_up("127.0.0.1", 1313) is True
    assert len(warmup_env.posted) == 2


def test_未授予辅助功能权限时不注入(warmup_env, monkeypatch):
    monkeypatch.setattr(macos_keyboard, "AXIsProcessTrusted", lambda: False)
    monkeypatch.setattr(macos_keyboard, "game_pid", lambda host, port: 4321)

    assert macos_keyboard.warm_up("127.0.0.1", 1313) is False
    assert warmup_env.posted == []
