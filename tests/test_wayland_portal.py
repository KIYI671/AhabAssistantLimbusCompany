from __future__ import annotations

import asyncio
import sys
import threading
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

if not sys.platform.startswith("linux"):
    pytest.skip("Wayland portal requires a Linux desktop", allow_module_level=True)

from dbus_next import Message, MessageType, Variant

from module import platform_compat
from module.automation import screenshot as screenshot_module
from module.automation.input_handlers import linux_input, wayland_backend
from module.automation.input_handlers.wayland_portal import (
    PortalInput,
    WaylandPortalError,
    key_to_keysym,
    map_monitors,
)


@pytest.mark.parametrize(
    "session,display,expected",
    [
        ("wayland", "wayland-0", True),
        ("wayland", "", True),
        ("", "wayland-0", True),
        ("x11", "wayland-0", False),
        ("x11", "", False),
    ],
)
def test_wayland_detection_with_xwayland(monkeypatch, session, display, expected):
    monkeypatch.setattr(platform_compat, "IS_LINUX", True)
    monkeypatch.setenv("XDG_SESSION_TYPE", session)
    monkeypatch.setenv("WAYLAND_DISPLAY", display)
    monkeypatch.setenv("DISPLAY", ":1")
    assert platform_compat.is_wayland_session() is expected
    x11 = Mock()
    monkeypatch.setattr(linux_input, "pyautogui", x11)
    handler = object.__new__(linux_input.LinuxInput)
    assert (handler.backend is wayland_backend.portal_backend) is expected


def _stream(node=123, name="eDP-1", size=(1707, 1067)):
    return [
        node,
        {
            "mapping_id": Variant("s", name),
            "size": Variant("(ii)", list(size)),
            "source_type": Variant("u", 1),
        },
    ]


def test_fractional_scaling_uses_stream_dimensions():
    mappings = map_monitors([_stream()], [{"name": "eDP-1", "rect": (0, 0, 3072, 1920)}])
    assert mappings[0].translate(1536, 960) == (123, 853.5, 533.5)


def test_mixed_scale_monitors_use_independent_origins_and_sizes():
    mappings = map_monitors(
        [_stream(1, "DP-1", (1920, 1080)), _stream(2, "eDP-1")],
        [
            {"name": "eDP-1", "rect": (1920, 100, 4992, 2020)},
            {"name": "DP-1", "rect": (0, 0, 1920, 1080)},
        ],
    )
    second = mappings[1]
    assert second.contains(1920, 100)
    assert not second.contains(4992, 2020)
    assert second.translate(3456, 1060) == (2, 853.5, 533.5)


def test_negative_monitor_origin():
    mapping = map_monitors([_stream()], [{"name": "eDP-1", "rect": (-3072, -1920, 0, 0)}])[0]
    assert mapping.translate(-1536, -960) == (123, 853.5, 533.5)


def test_ambiguous_multimonitor_mapping_is_rejected():
    with pytest.raises(WaylandPortalError, match="无法对应"):
        map_monitors(
            [_stream(name="opaque-id")],
            [
                {"name": "DP-1", "rect": (0, 0, 1920, 1080)},
                {"name": "DP-2", "rect": (1920, 0, 3840, 1080)},
            ],
        )


@pytest.mark.parametrize("streams", [[], [[1, {}]], [[1, {"size": [0, 1080]}]], [[1, {"source_type": 2}]]])
def test_invalid_streams_are_rejected(streams):
    with pytest.raises(WaylandPortalError):
        map_monitors(streams, [{"name": "eDP-1", "rect": (0, 0, 3072, 1920)}])


class _FakeBus:
    connected = True
    unique_name = ":1.321"

    def __init__(self, portal, *, response=0, devices=3, alternate_path=False):
        self.portal = portal
        self.response = response
        self.devices = devices
        self.alternate_path = alternate_path
        self.calls = []
        self.session = "/org/freedesktop/portal/desktop/session/1_321/test"

    async def call(self, message):
        # Validate actual D-Bus signatures and nested variants as well as call order.
        message.serial = len(self.calls) + 1
        message._marshall()
        self.calls.append(message)
        if message.member == "Get":
            return SimpleNamespace(message_type=MessageType.METHOD_RETURN, body=[Variant("u", 3)])
        if message.member in ("CreateSession", "SelectDevices", "SelectSources", "Start"):
            token = message.body[-1]["handle_token"].value
            path = f"/org/freedesktop/portal/desktop/request/1_321/{token}"
            if self.alternate_path:
                path += "_alternate"
            results = {}
            response = 0
            if message.member == "CreateSession":
                results = {"session_handle": Variant("s", self.session)}
            if message.member == "Start":
                response = self.response
                results = {"devices": Variant("u", self.devices), "streams": Variant("a(ua{sv})", [_stream()])}
            # Deliver Response before the method reply to cover a common portal race.
            self.portal._on_message(
                Message(
                    message_type=MessageType.SIGNAL,
                    path=path,
                    interface="org.freedesktop.portal.Request",
                    member="Response",
                    signature="ua{sv}",
                    body=[response, results],
                )
            )
            return SimpleNamespace(message_type=MessageType.METHOD_RETURN, body=[path])
        return SimpleNamespace(message_type=MessageType.METHOD_RETURN, body=[])

    def disconnect(self):
        self.connected = False

    async def wait_for_disconnect(self):
        pass


@pytest.mark.parametrize("alternate_path", [False, True])
def test_portal_authorization_and_native_input(alternate_path):
    async def scenario():
        portal = PortalInput()
        portal._bus = bus = _FakeBus(portal, alternate_path=alternate_path)
        await portal._prepare([{"name": "eDP-1", "rect": (0, 0, 3072, 1920)}])
        assert [call.member for call in bus.calls] == [
            "Get",
            "CreateSession",
            "SelectDevices",
            "SelectSources",
            "Start",
        ]
        await portal._move(1536, 960)
        assert bus.calls[-1].member == "NotifyPointerMotionAbsolute"
        assert bus.calls[-1].body == [bus.session, {}, 123, 853.5, 533.5]
        await portal._notify("NotifyPointerButton", "iu", [0x110, 1])
        await portal._notify("NotifyKeyboardKeysym", "iu", [key_to_keysym("ctrl"), 1])
        await portal._release_inputs()
        assert not portal._pressed_buttons
        assert not portal._pressed_keys
        # Repeated tasks reuse the same permission session.
        await portal._prepare([{"name": "eDP-1", "rect": (0, 0, 3072, 1920)}])
        assert sum(call.member == "Start" for call in bus.calls) == 1
        await portal._close_session()
        assert bus.calls[-1].member == "Close"

    asyncio.run(scenario())


@pytest.mark.parametrize("response,devices", [(1, 3), (2, 3), (0, 2)])
def test_denied_authorization_closes_session_and_sends_no_input(response, devices):
    async def scenario():
        portal = PortalInput()
        portal._bus = bus = _FakeBus(portal, response=response, devices=devices)
        with pytest.raises(WaylandPortalError):
            await portal._prepare([{"name": "eDP-1", "rect": (0, 0, 3072, 1920)}])
        assert not portal._active
        assert bus.calls[-1].member == "Close"
        assert not any(call.member.startswith("Notify") for call in bus.calls)

    asyncio.run(scenario())


def test_revoked_session_and_unshared_monitor_block_input():
    async def scenario():
        portal = PortalInput()
        portal._bus = bus = _FakeBus(portal)
        await portal._prepare([{"name": "eDP-1", "rect": (0, 0, 3072, 1920)}])
        with pytest.raises(WaylandPortalError, match="已授权的显示器"):
            await portal._move(4000, 960)
        portal._on_message(
            Message(
                message_type=MessageType.SIGNAL,
                path=bus.session,
                interface="org.freedesktop.portal.Session",
                member="Closed",
            )
        )
        with pytest.raises(WaylandPortalError, match="撤销"):
            await portal._move(10, 10)
        with pytest.raises(WaylandPortalError, match="撤销"):
            await portal._notify("NotifyPointerButton", "iu", [0x110, 1])
        assert not any(call.member.startswith("Notify") for call in bus.calls)

    asyncio.run(scenario())


def test_forced_stop_cancels_open_authorization_request():
    portal = PortalInput()
    ready = threading.Event()

    class WaitingBus(_FakeBus):
        async def call(self, message):
            if message.member == "Start":
                self.calls.append(message)
                token = message.body[-1]["handle_token"].value
                path = f"/org/freedesktop/portal/desktop/request/1_321/{token}"
                ready.set()
                return SimpleNamespace(message_type=MessageType.METHOD_RETURN, body=[path])
            return await super().call(message)

    portal._bus = bus = WaitingBus(portal)
    pending = portal._submit(portal._prepare([{"name": "eDP-1", "rect": (0, 0, 3072, 1920)}]))

    async def after_reset():
        assert not portal._active
        assert not portal._session
        assert not portal._pending

    try:
        assert ready.wait(2)
        portal.reset()
        # Queued after reset cleanup, without polling or contacting the real desktop.
        portal._run(after_reset())
        assert pending.cancelled()
        assert sum(call.member == "Close" for call in bus.calls) == 2
        assert not any(call.member.startswith("Notify") for call in bus.calls)
    finally:
        portal.close()


def _use_wayland_backend(monkeypatch):
    portal = SimpleNamespace(move=Mock(), button=Mock(), scroll=Mock(), hotkey=Mock(), type_text=Mock(), prepare=Mock())
    monkeypatch.setattr(wayland_backend, "portal_input", portal)
    monkeypatch.setattr(wayland_backend, "portal_backend", wayland_backend.PortalBackend())
    monkeypatch.setattr(wayland_backend.time, "sleep", lambda _: None)
    monkeypatch.setattr(linux_input, "is_wayland_session", lambda: True)
    return portal


@pytest.mark.parametrize(
    "gesture", ["mouse_drag", "mouse_drag_down", "mouse_swipe_for_scroll", "mouse_swipe_for_team_scroll", "mouse_drag_link", "mouse_click_blank"]
)
def test_wayland_gesture_does_not_press_if_initial_move_fails(monkeypatch, gesture):
    portal = _use_wayland_backend(monkeypatch)
    portal.move.side_effect = WaylandPortalError("move failed")
    handler = object.__new__(linux_input.LinuxInput)
    monkeypatch.setattr(handler, "_window_is_ready", lambda: True)
    monkeypatch.setattr(handler, "pos_offset", lambda *point: point)
    monkeypatch.setattr(handler, "get_mouse_position", lambda: (0, 0))
    args = ([[1, 1], [20, 20]],) if gesture == "mouse_drag_link" else (1, 1)
    if gesture == "mouse_click_blank":
        args = ()
    with pytest.raises(WaylandPortalError, match="move failed"):
        getattr(handler, gesture)(*args)
    portal.button.assert_not_called()


def test_wayland_drag_releases_button_on_later_move_failure(monkeypatch):
    portal = _use_wayland_backend(monkeypatch)
    portal.move.side_effect = [None, WaylandPortalError("revoked")]
    handler = object.__new__(linux_input.LinuxInput)
    monkeypatch.setattr(handler, "_window_is_ready", lambda: True)
    monkeypatch.setattr(handler, "pos_offset", lambda *point: point)
    with pytest.raises(WaylandPortalError, match="revoked"):
        handler.mouse_drag(1, 1, dx=10, dy=10, move_back=False)
    assert [call.args for call in portal.button.call_args_list] == [(True,), (False,)]


def test_wayland_keyboard_and_clipboard_avoid_x11_injection(monkeypatch):
    portal = _use_wayland_backend(monkeypatch)
    handler = object.__new__(linux_input.LinuxInput)
    monkeypatch.setattr(handler, "_window_is_ready", lambda: True)
    monkeypatch.setattr(linux_input.pyperclip, "copy", Mock())
    x11 = SimpleNamespace(press=Mock(), hotkey=Mock(), typewrite=Mock())
    monkeypatch.setattr(linux_input, "pyautogui", x11)
    handler.key_press("esc")
    handler.input_text("team-code")
    assert [call.args for call in portal.hotkey.call_args_list] == [("esc",), ("ctrl", "v")]
    monkeypatch.setattr(linux_input.pyperclip, "copy", Mock(side_effect=RuntimeError("clipboard unavailable")))
    handler.input_text("team-code")
    portal.type_text.assert_called_once_with("team-code")
    x11.press.assert_not_called()
    x11.hotkey.assert_not_called()
    x11.typewrite.assert_not_called()


@pytest.mark.parametrize("denied", [False, True])
def test_wayland_prepare_requests_authorization_after_window_is_ready(monkeypatch, denied):
    portal = _use_wayland_backend(monkeypatch)
    monitors = [{"name": "eDP-1", "rect": (0, 0, 3072, 1920)}]
    handle = SimpleNamespace(input_monitors=Mock(return_value=monitors), setForeground=Mock())
    monkeypatch.setattr(linux_input.screen, "handle", handle)
    handler = object.__new__(linux_input.LinuxInput)
    if denied:
        portal.prepare.side_effect = WaylandPortalError("denied")
        with pytest.raises(WaylandPortalError, match="denied"):
            handler.prepare()
        handle.setForeground.assert_not_called()
    else:
        handler.prepare()
        handle.setForeground.assert_called_once()
    portal.prepare.assert_called_once_with(monitors)


def test_wayland_screenshot_failure_does_not_capture_xwayland_root(monkeypatch):
    handle = SimpleNamespace(rect=lambda _client: (100, 100, 1540, 1180), bring_window_into_view=Mock())
    monkeypatch.setattr(screenshot_module.screen, "handle", handle)
    monkeypatch.setattr(screenshot_module, "is_wayland_session", lambda: True)
    monkeypatch.setattr(screenshot_module, "IS_WINDOWS", False)
    monkeypatch.setattr(screenshot_module.ScreenShot, "take_screenshot_x11", Mock(side_effect=RuntimeError("empty")))
    fallback = Mock()
    monkeypatch.setattr(screenshot_module.ScreenShot, "take_screenshot_mss", fallback)
    assert screenshot_module.ScreenShot.take_screenshot() is None
    fallback.assert_not_called()


@pytest.mark.parametrize("key", ["esc", "enter", "ctrl", "f1", "f12", "a", "中"])
def test_supported_keyboard_symbols(key):
    assert key_to_keysym(key) > 0
