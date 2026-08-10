from pathlib import Path
from types import SimpleNamespace

import pytest

from module.automation.input_handlers.simulator import bluestacks_control, simulator_control

BLUESTACKS_CONFIG = """
bst.enable_adb_access="1"
bst.instance.Pie64.display_name="BlueStacks App Player"
bst.instance.Pie64.status.adb_port="5555"
bst.instance.Rvc64.display_name="Android 11"
bst.instance.Rvc64.status.adb_port="5565"
"""


def test_parse_bluestacks_config_reads_instances_and_ports() -> None:
    adb_enabled, instances = bluestacks_control.parse_bluestacks_config(BLUESTACKS_CONFIG)

    assert adb_enabled is True
    assert instances == [
        bluestacks_control.BlueStacksInstance("Pie64", "BlueStacks App Player", 5555),
        bluestacks_control.BlueStacksInstance("Rvc64", "Android 11", 5565),
    ]


def test_select_bluestacks_instance_by_internal_name() -> None:
    _, instances = bluestacks_control.parse_bluestacks_config(BLUESTACKS_CONFIG)

    selected = bluestacks_control.select_bluestacks_instance(instances, "pie64", 0)

    assert selected.name == "Pie64"
    assert selected.adb_port == 5555


def test_select_bluestacks_instance_requires_choice_for_multiple_instances() -> None:
    _, instances = bluestacks_control.parse_bluestacks_config(BLUESTACKS_CONFIG)

    with pytest.raises(bluestacks_control.BlueStacksError, match="多个蓝叠实例"):
        bluestacks_control.select_bluestacks_instance(instances)


def test_bluestacks_launcher_uses_selected_instance(monkeypatch) -> None:
    calls = []
    monkeypatch.setattr(
        bluestacks_control.subprocess,
        "Popen",
        lambda command, **kwargs: calls.append((command, kwargs)),
    )
    launcher = bluestacks_control.BlueStacksLauncher(
        Path(r"C:\Program Files\BlueStacks_nxt\HD-Player.exe"),
        Path(r"D:\ProgramData\BlueStacks_nxt\bluestacks.conf"),
        True,
        [],
    )
    instance = bluestacks_control.BlueStacksInstance("Pie64", "BlueStacks App Player", 5555)
    monkeypatch.setattr(launcher, "_find_instance_processes", lambda selected: [])

    assert launcher.launch(instance) is True

    assert calls[0][0] == [str(launcher.executable), "--instance", "Pie64"]
    assert calls[0][1]["cwd"] == str(launcher.executable.parent)


def test_bluestacks_launcher_waits_for_crashed_process_before_relaunch(monkeypatch) -> None:
    calls = []
    old_process = SimpleNamespace(pid=1001)
    launcher = bluestacks_control.BlueStacksLauncher(
        Path(r"C:\Program Files\BlueStacks_nxt\HD-Player.exe"),
        Path(r"D:\ProgramData\BlueStacks_nxt\bluestacks.conf"),
        True,
        [],
    )
    instance = bluestacks_control.BlueStacksInstance("Pie64", "BlueStacks App Player", 5555)
    monkeypatch.setattr(launcher, "_find_instance_processes", lambda selected: [old_process])
    monkeypatch.setattr(bluestacks_control.psutil, "wait_procs", lambda processes, timeout: (processes, []))
    monkeypatch.setattr(
        bluestacks_control.subprocess,
        "Popen",
        lambda command, **kwargs: calls.append(command),
    )

    assert launcher.launch(instance) is True
    assert calls == [[str(launcher.executable), "--instance", "Pie64"]]


def test_bluestacks_launcher_skips_duplicate_while_instance_is_alive(monkeypatch) -> None:
    old_process = SimpleNamespace(pid=1001)
    launcher = bluestacks_control.BlueStacksLauncher(
        Path(r"C:\Program Files\BlueStacks_nxt\HD-Player.exe"),
        Path(r"D:\ProgramData\BlueStacks_nxt\bluestacks.conf"),
        True,
        [],
    )
    instance = bluestacks_control.BlueStacksInstance("Pie64", "BlueStacks App Player", 5555)
    monkeypatch.setattr(launcher, "_find_instance_processes", lambda selected: [old_process])
    monkeypatch.setattr(bluestacks_control.psutil, "wait_procs", lambda processes, timeout: ([], processes))
    monkeypatch.setattr(
        bluestacks_control.subprocess,
        "Popen",
        lambda *args, **kwargs: pytest.fail("must not start a duplicate instance"),
    )

    assert launcher.launch(instance, stale_process_timeout=0) is False


def test_bluestacks_launcher_closes_only_selected_instance(monkeypatch) -> None:
    commands = []

    class FakeProcess:
        def __init__(self, pid, instance_name):
            self.pid = pid
            self.info = {
                "name": "HD-Player.exe",
                "cmdline": ["HD-Player.exe", "--instance", instance_name],
            }

    selected_process = FakeProcess(1001, "Pie64")
    other_process = FakeProcess(1002, "Rvc64")
    monkeypatch.setattr(bluestacks_control.psutil, "process_iter", lambda attrs: [selected_process, other_process])
    monkeypatch.setattr(bluestacks_control.psutil, "wait_procs", lambda processes, timeout: (processes, []))
    monkeypatch.setattr(
        bluestacks_control.subprocess,
        "run",
        lambda command, **kwargs: commands.append(command),
    )
    launcher = bluestacks_control.BlueStacksLauncher(
        Path(r"C:\Program Files\BlueStacks_nxt\HD-Player.exe"),
        Path(r"D:\ProgramData\BlueStacks_nxt\bluestacks.conf"),
        True,
        [],
    )
    instance = bluestacks_control.BlueStacksInstance("Pie64", "BlueStacks App Player", 5555)

    launcher.close(instance)

    assert commands == [["taskkill", "/PID", "1001", "/T"]]


def test_simulator_control_does_not_launch_running_bluestacks(monkeypatch) -> None:
    launches = []
    instance = bluestacks_control.BlueStacksInstance("Pie64", "BlueStacks App Player", 5555)
    launcher = SimpleNamespace(
        resolve_instance=lambda name, port: instance,
        launch=lambda selected: launches.append(selected),
    )
    fake_cfg = SimpleNamespace(
        simulator_type=bluestacks_control.BLUESTACKS_SIMULATOR_TYPE,
        simulator_host="127.0.0.1",
        simulator_port=0,
        start_emulator_timeout=120,
        get_value=lambda name, default=None: "Pie64" if name == "bluestacks_instance_name" else default,
    )
    monkeypatch.setattr(simulator_control, "cfg", fake_cfg)
    monkeypatch.setattr(
        simulator_control.BlueStacksLauncher,
        "discover",
        classmethod(lambda cls: launcher),
    )
    monkeypatch.setattr(
        simulator_control,
        "adb",
        SimpleNamespace(connect=lambda endpoint, timeout: f"already connected to {endpoint}"),
    )
    control = simulator_control.SimulatorControl.__new__(simulator_control.SimulatorControl)
    control.simulator_port = None
    control.bluestacks_launcher = None
    control.bluestacks_instance = None

    control.adb_connect()

    assert control.simulator_port == "127.0.0.1:5555"
    assert launches == []


def test_simulator_control_launches_stopped_bluestacks(monkeypatch) -> None:
    launches = []
    responses = iter(["unable to connect", "connected to 127.0.0.1:5555"])
    instance = bluestacks_control.BlueStacksInstance("Pie64", "BlueStacks App Player", 5555)
    launcher = SimpleNamespace(
        resolve_instance=lambda name, port: instance,
        launch=lambda selected: launches.append(selected),
    )
    fake_cfg = SimpleNamespace(
        simulator_type=bluestacks_control.BLUESTACKS_SIMULATOR_TYPE,
        simulator_host="127.0.0.1",
        simulator_port=5555,
        start_emulator_timeout=120,
        get_value=lambda name, default=None: "" if name == "bluestacks_instance_name" else default,
    )
    monkeypatch.setattr(simulator_control, "cfg", fake_cfg)
    monkeypatch.setattr(
        simulator_control.BlueStacksLauncher,
        "discover",
        classmethod(lambda cls: launcher),
    )
    monkeypatch.setattr(
        simulator_control,
        "adb",
        SimpleNamespace(connect=lambda endpoint, timeout: next(responses)),
    )
    monkeypatch.setattr(simulator_control, "sleep", lambda _seconds: None)
    monkeypatch.setattr(simulator_control, "time", lambda: 0)
    control = simulator_control.SimulatorControl.__new__(simulator_control.SimulatorControl)
    control.simulator_port = None
    control.bluestacks_launcher = None
    control.bluestacks_instance = None

    control.adb_connect()

    assert launches == [instance]
    assert control.simulator_port == "127.0.0.1:5555"


def test_remote_bluestacks_does_not_start_local_instance(monkeypatch) -> None:
    fake_cfg = SimpleNamespace(
        simulator_type=bluestacks_control.BLUESTACKS_SIMULATOR_TYPE,
        simulator_host="192.0.2.10",
        simulator_port=5555,
    )
    monkeypatch.setattr(simulator_control, "cfg", fake_cfg)
    monkeypatch.setattr(
        simulator_control.BlueStacksLauncher,
        "discover",
        classmethod(lambda cls: pytest.fail("remote endpoint must not discover local BlueStacks")),
    )
    monkeypatch.setattr(
        simulator_control,
        "adb",
        SimpleNamespace(connect=lambda endpoint, timeout: f"connected to {endpoint}"),
    )
    control = simulator_control.SimulatorControl.__new__(simulator_control.SimulatorControl)
    control.simulator_port = None
    control.bluestacks_launcher = None
    control.bluestacks_instance = None

    control.adb_connect()

    assert control.simulator_port == "192.0.2.10:5555"
    assert control.bluestacks_launcher is None
