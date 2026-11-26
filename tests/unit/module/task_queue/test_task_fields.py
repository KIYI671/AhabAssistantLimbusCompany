"""按字段名读写任务参数（module.task_queue.fields），不依赖 Qt。"""

import pytest


@pytest.fixture(scope="module")
def config(isolated_import):
    return isolated_import("module.config.task_queue")


@pytest.fixture(scope="module")
def fields(isolated_import):
    return isolated_import("module.task_queue.fields")


def test_field_nested_read_and_write(config, fields):
    task = config.MirrorTask()
    assert fields.get_field(task, "re_claim.mail") is True
    assert fields.set_field(task, "re_claim.mail", False) is True
    assert task.re_claim.mail is False
    assert fields.get_field(task, "no_such_field", "默认") == "默认"


def test_field_bool_into_int_field_becomes_int(config, fields):
    task = config.MirrorTask()
    fields.set_field(task, "hard_mirror", True)
    assert task.hard_mirror == 1 and type(task.hard_mirror) is int
    fields.set_field(task, "hard_mirror", 2)
    assert task.hard_mirror == 2
    fields.set_field(task, "hard_mirror", False)
    assert task.hard_mirror == 0 and type(task.hard_mirror) is int


def test_field_bool_field_stays_bool(config, fields):
    task = config.MirrorTask()
    fields.set_field(task, "infinite", True)
    assert task.infinite is True


def test_field_same_value_reports_no_change(config, fields):
    task = config.MirrorTask(infinite=True)
    assert fields.set_field(task, "infinite", True) is False
    assert fields.set_field(task, "hard_mirror", 0) is False
