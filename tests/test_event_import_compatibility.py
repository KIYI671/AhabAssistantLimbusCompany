from __future__ import annotations

import importlib
import sys

import pytest


def _clear_event_package_modules(monkeypatch: pytest.MonkeyPatch) -> None:
    import tasks

    for module_name in tuple(sys.modules):
        if module_name == "tasks.event" or module_name.startswith("tasks.event."):
            monkeypatch.delitem(sys.modules, module_name, raising=False)
    monkeypatch.delattr(tasks, "event", raising=False)


def test_event_package_keeps_singleton_api_after_direct_submodule_import(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_event_package_modules(monkeypatch)

    direct_module = importlib.import_module("tasks.event.event_handling")
    from tasks.event import event_handling

    assert isinstance(event_handling, direct_module.EventHandling)
    assert callable(event_handling.decision_event_handling)


def test_event_package_keeps_singleton_api_before_direct_submodule_import(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_event_package_modules(monkeypatch)

    from tasks.event import event_handling

    direct_module = importlib.import_module("tasks.event.event_handling")

    assert isinstance(event_handling, direct_module.EventHandling)
    assert callable(event_handling.decision_event_handling)
