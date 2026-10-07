from __future__ import annotations

import base64
import runpy
import subprocess
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock

import pytest

if not sys.platform.startswith("linux"):
    pytest.skip("Linux desktop integration", allow_module_level=True)

from app import linux_toast, windows_toast
from module import hotkey_listener, platform_compat, system_actions
from module.automation.input_handlers import linux_input
from utils import schedule_helper, utils


@pytest.fixture(autouse=True)
def use_x11_input(monkeypatch):
    monkeypatch.setattr(linux_input, "is_wayland_session", lambda: False)


@pytest.mark.parametrize("failure_at_start", [False, True])
def test_drag_failure_never_leaves_mouse_pressed(monkeypatch, failure_at_start):
    monkeypatch.setattr(linux_input.screen, "handle", SimpleNamespace(rect=lambda _: (100, 200, 1540, 1280)))
    backend = SimpleNamespace(
        moveTo=Mock(side_effect=[RuntimeError("move failed")] if failure_at_start else [None, RuntimeError("move failed")]),
        mouseDown=Mock(), mouseUp=Mock(),
    )
    monkeypatch.setattr(linux_input, "pyautogui", backend)
    handler = object.__new__(linux_input.LinuxInput)
    with pytest.raises(RuntimeError, match="move failed"):
        handler._drag_path([((110, 220), 0), ((210, 220), 0.2)], move_back=False)
    assert backend.mouseDown.call_count == (0 if failure_at_start else 1)
    assert backend.mouseUp.call_count == (0 if failure_at_start else 1)



def test_drag_failed_press_still_attempts_release(monkeypatch):
    monkeypatch.setattr(linux_input.screen, "handle", SimpleNamespace(rect=lambda _: (100, 200, 1540, 1280)))
    backend = SimpleNamespace(moveTo=Mock(), mouseDown=Mock(side_effect=RuntimeError("press failed")), mouseUp=Mock())
    monkeypatch.setattr(linux_input, "pyautogui", backend)
    handler = object.__new__(linux_input.LinuxInput)
    with pytest.raises(RuntimeError, match="press failed"):
        handler._drag_path([((110, 220), 0), ((210, 220), 0.2)], move_back=False)
    backend.mouseUp.assert_called_once()


def test_windows_notification_still_uses_original_template(monkeypatch):
    monkeypatch.setattr(windows_toast, "IS_WINDOWS", True)
    monkeypatch.setattr(windows_toast, "IMPORT_SUCCESS", True)
    windows = Mock(return_value=True)
    linux = Mock()
    monkeypatch.setattr(windows_toast, "_send_template_toast", windows)
    monkeypatch.setattr(linux_toast, "send_linux_toast", linux)
    assert windows_toast.send_toast("title", "body", template=windows_toast.TemplateToast.NormalTemplate)
    windows.assert_called_once()
    linux.assert_not_called()


@pytest.mark.parametrize("action,custom_callback", [("close", False), ("confirm", False), ("close", True)])
def test_linux_notification_buttons_use_original_actions(monkeypatch, action, custom_callback):
    monkeypatch.setattr(linux_toast.shutil, "which", lambda _: "/usr/bin/notify-send")
    monkeypatch.setattr(linux_toast.threading, "Thread", lambda target, **_: SimpleNamespace(start=target))
    run = Mock(return_value=subprocess.CompletedProcess([], 0, action + "\n", ""))
    monkeypatch.setattr(linux_toast.subprocess, "run", run)
    emit, callback = Mock(), Mock()
    monkeypatch.setattr(linux_toast, "mediator", SimpleNamespace(kill_signal=SimpleNamespace(emit=emit)))
    assert linux_toast.send_linux_toast(
        "title", ["line 1", "line 2"], "AALC", "", windows_toast.TemplateToast.NormalTemplate,
        callback if custom_callback else None,
    )
    assert "--wait" in run.call_args.args[0]
    assert run.call_args.args[0][-2:] == ["title", "line 1\nline 2"]
    assert emit.call_count == int(action == "close" and not custom_callback)
    if custom_callback:
        callback.assert_called_once_with(action)


def test_linux_notification_reports_missing_backend(monkeypatch):
    monkeypatch.setattr(linux_toast.shutil, "which", lambda _: None)
    assert not linux_toast.send_linux_toast("title", "body", "AALC", "", windows_toast.TemplateToast.NoneTemplate, None)


def test_hotkey_unavailable_backend_can_start_and_stop(monkeypatch):
    monkeypatch.setitem(sys.modules, "pynput", ModuleType("pynput"))
    module = runpy.run_path(hotkey_listener.__file__)
    listener = module["ExactGlobalHotKeys"]({"<ctrl>+x": Mock()})
    listener.start()
    listener.stop()
    listener.join()


def test_hotkey_requires_exact_modifiers_and_ignores_injected_input(monkeypatch):
    class Listener:
        def __init__(self, **_kwargs):
            pass

        def canonical(self, key):
            return key

    keyboard = SimpleNamespace(
        Key=SimpleNamespace(alt="alt", alt_gr="alt_gr", cmd="cmd", ctrl="ctrl", shift="shift"),
        Listener=Listener,
        HotKey=SimpleNamespace(parse=lambda _: ["ctrl", "x"]),
    )
    pynput = ModuleType("pynput")
    pynput.keyboard = keyboard
    monkeypatch.setitem(sys.modules, "pynput", pynput)
    module = runpy.run_path(hotkey_listener.__file__)
    callback = Mock()
    listener = module["ExactGlobalHotKeys"]({"<ctrl>+x": callback})
    listener._on_press("ctrl")
    listener._on_press("shift")
    listener._on_press("x")
    callback.assert_not_called()
    listener._on_release("shift")
    listener._on_press("x", injected=True)
    callback.assert_not_called()
    listener._on_press("x")
    callback.assert_called_once_with()


def test_linux_secrets_persist_are_randomized_and_detect_tampering(monkeypatch, tmp_path):
    key_file = tmp_path / "key"
    monkeypatch.setattr(utils, "_KEY_FILE", str(key_file))
    monkeypatch.setattr(utils, "IS_WINDOWS", False)
    first = utils.encrypt_string("测试 config")
    assert first != utils.encrypt_string("测试 config")
    assert utils.decrypt_string(first) == "测试 config"
    assert key_file.stat().st_mode & 0o777 == 0o600
    data = bytearray(base64.b64decode(first[5:]))
    data[-1] ^= 1
    modified = "LNX2:" + base64.b64encode(data).decode()
    assert utils.decrypt_string(modified) == modified
    assert utils.decrypt_string(first, entropy=b"other configuration") == first


def test_linux_empty_process_name_does_not_terminate_processes(monkeypatch):
    import psutil

    processes = Mock()
    monkeypatch.setattr(psutil, "process_iter", processes)
    assert not platform_compat.kill_process_by_name(" ")
    processes.assert_not_called()


def test_linux_keep_awake_reuses_and_releases_one_inhibitor(monkeypatch):
    monkeypatch.setattr(system_actions, "_linux_inhibit_depth", 0)
    monkeypatch.setattr(system_actions, "_linux_inhibit_process", None)
    monkeypatch.setattr(system_actions.shutil, "which", lambda _: "/usr/bin/systemd-inhibit")
    process = Mock()
    process.poll.return_value = None
    popen = Mock(return_value=process)
    monkeypatch.setattr(system_actions.subprocess, "Popen", popen)
    system_actions._apply_linux_power_keep_awake(True)
    system_actions._apply_linux_power_keep_awake(True)
    popen.assert_called_once()
    system_actions._apply_linux_power_keep_awake(False)
    process.terminate.assert_not_called()
    system_actions._apply_linux_power_keep_awake(False)
    process.terminate.assert_called_once()


def test_linux_scheduler_preserves_paths_with_spaces(monkeypatch, tmp_path):
    monkeypatch.setattr(schedule_helper, "_SYSTEMD_USER_DIR", str(tmp_path))
    monkeypatch.setattr(schedule_helper, "_AUTOSTART_DIR", str(tmp_path))
    monkeypatch.setattr(schedule_helper, "_app_command_args", lambda _: ["/opt/AALC App/AALC", "start", "preset with spaces"])
    monkeypatch.setattr(schedule_helper, "_app_working_dir", lambda: "/opt/AALC App")
    systemctl = Mock(return_value=True)
    monkeypatch.setattr(schedule_helper, "_run_systemctl", systemctl)
    scheduler = schedule_helper.ScheduleHelper_Linux()
    scheduler.register_daily_task("AALC Daily", "start", 8, 5)
    service = (tmp_path / "aalc-daily-aalc-daily.service").read_text()
    assert 'ExecStart="/opt/AALC App/AALC" "start" "preset with spaces"' in service
    assert 'WorkingDirectory="/opt/AALC App"' in service
    assert "OnCalendar=*-*-* 08:05:00" in (tmp_path / "aalc-daily-aalc-daily.timer").read_text()
    scheduler.register_onstart_task("AALC Autostart", "start")
    assert 'Exec="/opt/AALC App/AALC" "start" "preset with spaces"' in (tmp_path / "aalc-autostart.desktop").read_text()
    scheduler.unregister_task("AALC Autostart")
    assert not (tmp_path / "aalc-autostart.desktop").exists()
    scheduler.unregister_task("AALC Daily")
    assert not (tmp_path / "aalc-daily-aalc-daily.service").exists()



def test_linux_secrets_read_legacy_lnx1_configuration(monkeypatch, tmp_path):
    key_file = tmp_path / "key"
    key_file.write_bytes(b"test-local-key")
    monkeypatch.setattr(utils, "_KEY_FILE", str(key_file))
    monkeypatch.setattr(utils, "IS_WINDOWS", False)
    assert utils.decrypt_string("LNX1:mDllyJCAhNlpmA==") == "legacy cdk"
