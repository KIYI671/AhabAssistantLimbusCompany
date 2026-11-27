"""任务列表的增删改移（TaskQueue），不依赖 Qt。"""

import pytest

NAMES = {"daily": "日常任务", "reward": "领取奖励", "enkephalin": "狂气换体", "mirror": "镜牢"}


@pytest.fixture(scope="module")
def tq(isolated_import):
    return isolated_import("module.task_queue.operations")


@pytest.fixture
def queue(tq, isolated_import):
    config = isolated_import("module.config.task_queue")
    tasks = [config.new_task("daily"), config.new_task("mirror"), config.new_task("reward")]
    return tq.TaskQueue(tasks, NAMES.__getitem__)


def ids(queue):
    return [t.id for t in queue.tasks]


def types(queue):
    return [t.type for t in queue.tasks]


def test_edits_the_given_list_in_place(tq):
    tasks = []
    queue = tq.TaskQueue(tasks, NAMES.__getitem__)
    queue.add("mirror")
    assert [t.type for t in tasks] == ["mirror"]


def test_title_uses_custom_name_then_type_name(queue):
    mirror = queue.tasks[1]
    assert queue.title(mirror) == "镜牢"
    mirror.name = "困牢"
    assert queue.title(mirror) == "困牢"


def test_add_appends_new_task(queue):
    task = queue.add("enkephalin")
    assert types(queue) == ["daily", "mirror", "reward", "enkephalin"]
    assert queue.tasks[-1] is task


def test_duplicate_inserts_independent_copy_after_source(queue):
    source = queue.tasks[1]
    clone = queue.duplicate(source.id)
    assert types(queue) == ["daily", "mirror", "mirror", "reward"]
    assert queue.tasks[2] is clone
    assert clone.id != source.id
    assert clone.name == "镜牢 (2)"
    clone.count = 9
    assert source.count != 9


def test_duplicate_picks_unused_copy_number(queue):
    source = queue.tasks[1]
    queue.duplicate(source.id)
    third = queue.duplicate(source.id)
    assert third.name == "镜牢 (3)"


def test_duplicate_unknown_id_does_nothing(queue):
    before = ids(queue)
    assert queue.duplicate("nope") is None
    assert ids(queue) == before


def test_remove_returns_task_to_select_next(queue):
    first, middle, last = ids(queue)
    assert queue.remove(middle) == last
    assert queue.remove(last) == first
    assert queue.remove(first) == ""
    assert queue.tasks == []


def test_remove_unknown_id_returns_none(queue):
    assert queue.remove("nope") is None
    assert len(queue.tasks) == 3


def test_move_up_and_down_within_bounds(queue):
    first, middle, last = ids(queue)
    assert queue.move(last, -1) is True
    assert ids(queue) == [first, last, middle]
    assert queue.move(first, -1) is False
    assert queue.move(middle, 1) is False
    assert ids(queue) == [first, last, middle]


def test_reorder_follows_ids(queue):
    first, middle, last = ids(queue)
    assert queue.reorder([last, first, middle]) is True
    assert ids(queue) == [last, first, middle]
    assert queue.reorder([last, first, middle]) is False


def test_reorder_rejects_a_different_set(queue):
    first, middle, _ = ids(queue)
    before = ids(queue)
    assert queue.reorder([first, middle]) is False
    assert ids(queue) == before


def test_rename_sets_and_clears_custom_name(queue):
    mirror = queue.tasks[1]
    assert queue.rename(mirror.id, "  困牢 ") is True
    assert mirror.name == "困牢"
    assert queue.rename(mirror.id, "困牢") is False
    # 清空或改回类型名，都恢复成默认名称
    assert queue.rename(mirror.id, "") is True
    assert mirror.name is None
    mirror.name = "x"
    assert queue.rename(mirror.id, "镜牢") is True
    assert mirror.name is None


def test_toggle_flips_enabled(queue):
    task = queue.tasks[0]
    before = task.enabled
    assert queue.toggle(task.id) is True
    assert task.enabled is not before
    assert queue.toggle("nope") is False


def test_set_all_enabled(queue):
    queue.set_all_enabled(False)
    assert [t.enabled for t in queue.tasks] == [False, False, False]
    queue.set_all_enabled(True)
    assert [t.enabled for t in queue.tasks] == [True, True, True]
