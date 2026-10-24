"""Regression tests for the optional, independently removable run journal."""

import builtins
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

SOURCE = Path(__file__).resolve().parents[1] / "mirror_run_log.py"


def load_module():
    module = ModuleType("mirror_run_log_test")
    module.__file__ = str(SOURCE)
    exec(compile(SOURCE.read_text(encoding="utf-8-sig"), str(SOURCE), "exec"), module.__dict__)
    return module


@pytest.fixture

def journal(tmp_path, monkeypatch):
    module = load_module()
    monkeypatch.setattr(module, "LOG_PATH", tmp_path / "mirror_run_log.md")
    monkeypatch.setattr(module.time, "time", lambda: 4000.0)
    return module


def adventure(**changes):
    values = dict(start_time=3400.0, floor=3, team_order=2, team_number="浮士德单通",
                  floor_limit_exit=False, mirror_floor_limit=3, bequest_from_the_previous_game=False)
    values.update(changes)
    return SimpleNamespace(**values)


def rows(journal):
    return [line for line in journal.LOG_PATH.read_text(encoding="utf-8").splitlines()
            if line.startswith("| ") and "结束时间" not in line and "---" not in line]


def test_import_is_passive_and_has_no_qt_import(monkeypatch, tmp_path):
    original = builtins.__import__

    def guarded(name, *args, **kwargs):
        if name.startswith("PySide6"):
            raise AssertionError("Qt imported before opening the tool")
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded)
    module = load_module()
    assert module.ROOT == SOURCE.parent
    assert callable(module.create_window)
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "AALC.exe"))
    frozen_module = load_module()
    assert frozen_module.ROOT == tmp_path
    assert not (tmp_path / "mirror_run_log.md").exists()


def test_disabled_by_default_does_not_create_file(journal):
    assert not journal.is_enabled()
    assert not journal.record_result(adventure(), True)
    assert journal.set_enabled(False)
    assert not journal.LOG_PATH.exists()
    assert "尚无日志" in journal.read_log()


def test_enabled_record_and_duration_reuse_original_start(journal):
    assert journal.set_enabled(True)
    assert journal.is_enabled()
    assert journal.record_result(adventure(), True, "completed")
    line, = rows(journal)
    assert "浮士德单通" in line
    assert "00:10:00" in line
    assert "完成 3 层" in line
    assert "| 是 | 完成镜牢 |" in line
    assert journal.LAST_ERROR == ""


def test_disabling_and_reenabling_preserves_existing_rows(journal):
    journal.set_enabled(True)
    journal.record_result(adventure(), True, "completed")
    old_rows = rows(journal)
    assert journal.set_enabled(False)
    assert not journal.is_enabled()
    assert not journal.record_result(adventure(start_time=3500), False, "bad")
    assert journal.set_enabled(True)
    assert rows(journal) == old_rows
    assert journal.LOG_PATH.read_text(encoding="utf-8").startswith("<!-- AALC_MIRROR_RUN_LOG enabled=1 -->\n")
    assert list(journal.LOG_PATH.parent.iterdir()) == [journal.LOG_PATH]


def test_deleting_markdown_stops_recording_without_recreation(journal):
    journal.set_enabled(True)
    journal.LOG_PATH.unlink()
    assert not journal.record_result(adventure(), True)
    assert not journal.LOG_PATH.exists()
    assert not journal.is_enabled()


def test_deletion_between_check_and_append_does_not_recreate(journal, monkeypatch):
    journal.set_enabled(True)
    original = journal._enabled_unlocked

    def disappearing():
        enabled = original()
        journal.LOG_PATH.unlink()
        return enabled

    monkeypatch.setattr(journal, "_enabled_unlocked", disappearing)
    assert not journal.record_result(adventure(), True)
    assert not journal.LOG_PATH.exists()


def test_duplicate_end_is_ignored_but_new_run_start_is_recorded(journal):
    journal.set_enabled(True)
    instance = adventure()
    assert journal.record_result(instance, False, "battle_failures")
    assert not journal.record_result(instance, False, "battle_failures")
    instance.start_time = 3700
    assert journal.record_result(instance, True, "completed")
    assert len(rows(journal)) == 2
    assert "00:05:00" in rows(journal)[1]


def test_cell_escape_prevents_extra_markdown_rows(journal):
    journal.set_enabled(True)
    assert journal.record_result(adventure(team_number="A|B\nC"), False, "错误|原因\r\n下一行\\路径")
    line, = rows(journal)
    assert "A\\|B<br>C" in line
    assert "错误\\|原因<br>下一行\\\\路径" in line
    assert len(rows(journal)) == 1


@pytest.mark.parametrize("floor", [None, 0, -1, float("nan"), True, "3"])
def test_unknown_floor_is_not_invented(journal, floor):
    journal.set_enabled(True)
    assert journal.record_result(adventure(floor=floor), False)
    assert "| 未知 | 否 |" in rows(journal)[0]


def test_floor_limit_uses_completed_target_not_next_floor(journal):
    journal.set_enabled(True)
    assert journal.record_result(adventure(floor=4, floor_limit_exit=True), True, "floor_limit")
    assert "完成 3 层" in rows(journal)[0]
    assert "完成 4 层" not in rows(journal)[0]


def test_failure_floor_is_reached_not_completed(journal):
    journal.set_enabled(True)
    assert journal.record_result(adventure(floor=3), False, "attempts_exhausted")
    assert "到达第 3 层" in rows(journal)[0]
    assert "关卡尝试次数耗尽" in rows(journal)[0]


def test_resumed_settlement_is_marked_incomplete(journal):
    journal.set_enabled(True)
    assert journal.record_result(adventure(bequest_from_the_previous_game=True, floor=0), None, "previous_settlement")
    assert "| 未知 | 未确认 |" in rows(journal)[0]
    assert "接续结算，计时不完整" in rows(journal)[0]


def test_unicode_tail_without_newline_is_appended_safely(journal):
    journal.set_enabled(True)
    with journal.LOG_PATH.open("a", encoding="utf-8") as stream:
        stream.write("用户备注：中文")
    assert journal.record_result(adventure(), True)
    assert "用户备注：中文\n| " in journal.LOG_PATH.read_text(encoding="utf-8")


def test_write_failure_does_not_mark_run_recorded_and_retry_works(journal, monkeypatch):
    journal.set_enabled(True)
    instance = adventure()
    original = Path.open

    def denied(path, mode="r", *args, **kwargs):
        if path == journal.LOG_PATH and mode == "r+b":
            raise PermissionError("test journal is read-only")
        return original(path, mode, *args, **kwargs)

    with monkeypatch.context() as context:
        context.setattr(Path, "open", denied)
        assert not journal.record_result(instance, True)
    assert "PermissionError" in journal.LAST_ERROR
    assert not hasattr(instance, journal._RECORDED_ATTRIBUTE)
    assert journal.record_result(instance, True)
    assert len(rows(journal)) == 1
    assert journal.LAST_ERROR == ""


def test_toggle_failure_preserves_log_and_cleans_temporary_file(journal, monkeypatch):
    journal.set_enabled(True)
    journal.record_result(adventure(), True)
    previous = journal.LOG_PATH.read_bytes()

    def denied(*args):
        raise PermissionError("cannot replace journal")

    monkeypatch.setattr(journal.os, "replace", denied)
    assert not journal.set_enabled(False)
    assert journal.LOG_PATH.read_bytes() == previous
    assert "PermissionError" in journal.LAST_ERROR
    assert list(journal.LOG_PATH.parent.iterdir()) == [journal.LOG_PATH]


def test_preview_is_bounded_without_truncating_disk(journal):
    journal.set_enabled(True)
    for start in range(210):
        journal.record_result(adventure(start_time=start), True)
    assert len(journal.read_log().splitlines()) == 200
    assert len(rows(journal)) == 210


def test_removed_python_tool_disables_cached_recording(journal, tmp_path, monkeypatch):
    tool = tmp_path / "mirror_run_log.py"
    tool.write_text("# removable tool", encoding="utf-8")
    monkeypatch.setattr(journal, "ROOT", tmp_path)
    journal.set_enabled(True)
    assert journal.tool_available()
    tool.unlink()
    assert not journal.tool_available()
    assert not journal.record_result(adventure(), True)
    assert not rows(journal)


def test_parallel_end_notifications_write_only_one_row(journal):
    from concurrent.futures import ThreadPoolExecutor

    journal.set_enabled(True)
    instance = adventure()
    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(lambda _: journal.record_result(instance, True), range(32)))
    assert sum(results) == 1
    assert len(rows(journal)) == 1
