from types import SimpleNamespace

import pytest

from module.automation.input_handlers.simulator import simulator_control
from utils.adb_endpoint import (
    build_adb_endpoint,
    normalize_adb_host,
)


@pytest.mark.parametrize(
    ("host", "expected"),
    [
        ("127.0.0.1", "127.0.0.1"),
        (" emulator.example.com ", "emulator.example.com"),
        ("[2001:db8::1]", "2001:db8::1"),
    ],
)
def test_normalize_adb_host(host: str, expected: str) -> None:
    assert normalize_adb_host(host) == expected


@pytest.mark.parametrize("host", ["", "http://10.0.0.2", "host:5555", "bad host"])
def test_normalize_adb_host_rejects_invalid_values(host: str) -> None:
    with pytest.raises(ValueError):
        normalize_adb_host(host)


def test_build_adb_endpoint_for_remote_ipv4() -> None:
    assert build_adb_endpoint("10.0.0.25", 5555) == "10.0.0.25:5555"


def test_build_adb_endpoint_for_ipv6() -> None:
    assert build_adb_endpoint("2001:db8::1", 5555) == "[2001:db8::1]:5555"


@pytest.mark.parametrize("port", [0, 65536, "invalid"])
def test_build_adb_endpoint_rejects_invalid_port(port) -> None:
    with pytest.raises(ValueError):
        build_adb_endpoint("127.0.0.1", port)


def test_simulator_control_connects_to_configured_remote_endpoint(monkeypatch) -> None:
    endpoints = []
    fake_adb = SimpleNamespace(
        connect=lambda endpoint, timeout: endpoints.append((endpoint, timeout)) or f"connected to {endpoint}"
    )
    fake_cfg = SimpleNamespace(simulator_host="10.0.0.25", simulator_port=5555)
    monkeypatch.setattr(simulator_control, "adb", fake_adb)
    monkeypatch.setattr(simulator_control, "cfg", fake_cfg)

    control = simulator_control.SimulatorControl.__new__(simulator_control.SimulatorControl)
    control.simulator_port = None
    control.adb_connect()

    assert endpoints == [("10.0.0.25:5555", simulator_control.ADB_CONNECT_TIMEOUT)]
    assert control.simulator_port == "10.0.0.25:5555"


def test_simulator_control_reports_remote_connection_failure(monkeypatch) -> None:
    fake_adb = SimpleNamespace(connect=lambda endpoint, timeout: f"unable to connect to {endpoint}")
    fake_cfg = SimpleNamespace(simulator_host="remote.example.com", simulator_port=5555)
    monkeypatch.setattr(simulator_control, "adb", fake_adb)
    monkeypatch.setattr(simulator_control, "cfg", fake_cfg)
    monkeypatch.setattr(simulator_control, "sleep", lambda _seconds: None)

    control = simulator_control.SimulatorControl.__new__(simulator_control.SimulatorControl)
    control.simulator_port = None

    with pytest.raises(RuntimeError, match=r"remote\.example\.com:5555"):
        control.adb_connect()
