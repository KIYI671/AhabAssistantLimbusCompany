"""定时任务的增删和 Windows 计划任务同步（用假的计划任务对象，不碰系统）"""

import pytest


class FakeScheduler:
    def __init__(self, fail=False):
        self.tasks: dict[str, tuple[str, int, int]] = {}
        self.fail = fail

    def register_daily_task(self, name, args, hour, minute):
        if self.fail:
            raise OSError("denied")
        self.tasks[name] = (args, hour, minute)

    def unregister_task(self, name):
        self.tasks.pop(name, None)


@pytest.fixture(scope="module")
def mods(isolated_import):
    return isolated_import("module.config.task_queue"), isolated_import("module.schedules")


def test_task_name_keeps_legacy_names(mods):
    tq, sc = mods
    assert sc.scheduler_task_name(tq.Schedule(id="autodaily")) == "AALC Daily Task"
    assert sc.scheduler_task_name(tq.Schedule(id="autodaily3")) == "AALC Daily Task3"
    assert sc.scheduler_task_name(tq.Schedule(id="autodaily_ab12cd34")) == "AALC Schedule ab12cd34"


def test_enable_registers_and_disable_unregisters(mods):
    tq, sc = mods
    fake = FakeScheduler()
    schedule = tq.Schedule(id="autodaily2", time="07:05")
    assert sc.set_enabled(schedule, True, fake) is True
    assert fake.tasks == {"AALC Daily Task2": ("start --exit autodaily2", 7, 5)}
    sc.set_enabled(schedule, False, fake)
    assert schedule.enabled is False
    assert fake.tasks == {}


def test_sync_is_idempotent(mods):
    tq, sc = mods
    fake = FakeScheduler()
    schedule = tq.Schedule(id="autodaily", enabled=True, time="01:00")
    sc.sync(schedule, fake)
    sc.sync(schedule, fake)
    assert fake.tasks == {"AALC Daily Task": ("start --exit autodaily", 1, 0)}


def test_time_change_reregisters_only_when_enabled(mods):
    tq, sc = mods
    fake = FakeScheduler()
    schedule = tq.Schedule(id="autodaily", enabled=False)
    sc.set_time(schedule, "23:30", fake)
    assert schedule.time == "23:30"
    assert fake.tasks == {}
    schedule.enabled = True
    sc.set_time(schedule, "06:45", fake)
    assert fake.tasks["AALC Daily Task"] == ("start --exit autodaily", 6, 45)


def test_bad_time_is_ignored(mods):
    tq, sc = mods
    schedule = tq.Schedule(time="08:00")
    sc.set_time(schedule, "25:99", FakeScheduler())
    assert schedule.time == "08:00"


def test_register_failure_reports_false(mods):
    tq, sc = mods
    schedule = tq.Schedule(id="autodaily")
    assert sc.set_enabled(schedule, True, FakeScheduler(fail=True)) is False
    assert schedule.enabled is True  # 设置照样保存，只是系统里没注册上


def test_add_and_remove(mods):
    tq, sc = mods
    fake = FakeScheduler()
    schedules = []
    schedule = sc.add(schedules)
    assert schedules == [schedule]
    assert [t.type for t in schedule.tasks] == ["daily", "reward", "enkephalin", "mirror"]
    assert not any(t.enabled for t in schedule.tasks)
    sc.set_enabled(schedule, True, fake)
    assert sc.remove(schedules, schedule, fake) is True
    assert schedules == [] and fake.tasks == {}
    assert sc.remove(schedules, schedule, fake) is False


def test_number_follows_position_or_legacy_id(mods):
    tq, sc = mods
    first, second = tq.Schedule(), tq.Schedule()
    assert sc.number(second, [first, second]) == 2
    assert sc.number(tq.Schedule(id="autodaily4"), []) == 4
    assert sc.number(tq.Schedule(id="autodaily_x"), []) == 1
