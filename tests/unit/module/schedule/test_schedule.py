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
    return (
        isolated_import("module.config.task_queue"),
        isolated_import("module.schedule.system_task"),
        isolated_import("module.schedule.book"),
    )


def test_task_name_keeps_legacy_names(mods):
    tq, system_task, book_mod = mods
    assert system_task.scheduler_task_name(tq.Schedule(id="autodaily")) == "AALC Daily Task"
    assert system_task.scheduler_task_name(tq.Schedule(id="autodaily3")) == "AALC Daily Task3"
    assert system_task.scheduler_task_name(tq.Schedule(id="autodaily_ab12cd34")) == "AALC Schedule ab12cd34"


def test_enable_registers_and_disable_unregisters(mods):
    tq, system_task, book_mod = mods
    fake = FakeScheduler()
    schedule = tq.Schedule(id="autodaily2", time="07:05")
    assert system_task.set_enabled(schedule, True, fake) is True
    assert fake.tasks == {"AALC Daily Task2": ("start --exit autodaily2", 7, 5)}
    system_task.set_enabled(schedule, False, fake)
    assert schedule.enabled is False
    assert fake.tasks == {}


def test_sync_is_idempotent(mods):
    tq, system_task, book_mod = mods
    fake = FakeScheduler()
    schedule = tq.Schedule(id="autodaily", enabled=True, time="01:00")
    system_task.sync(schedule, fake)
    system_task.sync(schedule, fake)
    assert fake.tasks == {"AALC Daily Task": ("start --exit autodaily", 1, 0)}


def test_time_change_reregisters_only_when_enabled(mods):
    tq, system_task, book_mod = mods
    fake = FakeScheduler()
    schedule = tq.Schedule(id="autodaily", enabled=False)
    system_task.set_time(schedule, "23:30", fake)
    assert schedule.time == "23:30"
    assert fake.tasks == {}
    schedule.enabled = True
    system_task.set_time(schedule, "06:45", fake)
    assert fake.tasks["AALC Daily Task"] == ("start --exit autodaily", 6, 45)


def test_bad_time_is_ignored(mods):
    tq, system_task, book_mod = mods
    schedule = tq.Schedule(time="08:00")
    system_task.set_time(schedule, "25:99", FakeScheduler())
    assert schedule.time == "08:00"


def test_register_failure_reports_false(mods):
    tq, system_task, book_mod = mods
    schedule = tq.Schedule(id="autodaily")
    assert system_task.set_enabled(schedule, True, FakeScheduler(fail=True)) is False
    assert schedule.enabled is True  # 设置照样保存，只是系统里没注册上


def test_add_and_remove(mods):
    tq, system_task, book_mod = mods
    fake = FakeScheduler()
    schedules = []
    schedule = book_mod.add(schedules)
    assert schedules == [schedule]
    assert [t.type for t in schedule.tasks] == ["daily", "reward", "enkephalin", "mirror"]
    assert not any(t.enabled for t in schedule.tasks)
    system_task.set_enabled(schedule, True, fake)
    assert book_mod.remove(schedules, schedule, fake) is True
    assert schedules == [] and fake.tasks == {}
    assert book_mod.remove(schedules, schedule, fake) is False


def test_number_follows_position_or_legacy_id(mods):
    tq, system_task, book_mod = mods
    first, second = tq.Schedule(), tq.Schedule()
    assert book_mod.number(second, [first, second]) == 2
    assert book_mod.number(tq.Schedule(id="autodaily4"), []) == 4
    assert book_mod.number(tq.Schedule(id="autodaily_x"), []) == 1


class Counter:
    def __init__(self):
        self.calls = 0

    def __call__(self):
        self.calls += 1


def make_book(book_module, schedules=None, main_tasks=None):
    fake, save = FakeScheduler(), Counter()
    schedules = [] if schedules is None else schedules
    book = book_module.ScheduleBook(schedules, main_tasks or [], lambda: fake, save)
    return book, fake, save


def test_book_add_appends_to_given_list_and_saves(mods):
    _, system_task, book_mod = mods
    schedules = []
    book, _, save = make_book(book_mod, schedules)
    schedule = book.add()
    assert schedules == [schedule] and book.schedules is schedules
    assert save.calls == 1


def test_book_set_enabled_syncs_and_saves(mods):
    tq, system_task, book_mod = mods
    schedule = tq.Schedule(id="autodaily_ab12cd34", time="07:05")
    book, fake, save = make_book(book_mod, [schedule])
    book.set_enabled(schedule, True)
    assert fake.tasks == {"AALC Schedule ab12cd34": ("start --exit autodaily_ab12cd34", 7, 5)}
    book.set_enabled(schedule, False)
    assert fake.tasks == {}
    assert save.calls == 2


def test_book_set_time_reregisters_and_saves(mods):
    tq, system_task, book_mod = mods
    schedule = tq.Schedule(id="autodaily", enabled=True, time="01:00")
    book, fake, save = make_book(book_mod, [schedule])
    book.set_time(schedule, "06:45")
    assert fake.tasks == {"AALC Daily Task": ("start --exit autodaily", 6, 45)}
    assert save.calls == 1


def test_book_remove_unregisters_and_saves_only_when_removed(mods):
    tq, system_task, book_mod = mods
    schedule = tq.Schedule(id="autodaily", enabled=True)
    schedules = [schedule]
    book, fake, save = make_book(book_mod, schedules)
    fake.tasks["AALC Daily Task"] = ("start --exit autodaily", 0, 0)
    assert book.remove(schedule) is True
    assert schedules == [] and fake.tasks == {}
    assert save.calls == 1
    assert book.remove(tq.Schedule(id="autodaily9")) is False
    assert save.calls == 1


def test_book_apply_edit_writes_fields_and_saves(mods):
    tq, system_task, book_mod = mods
    schedule = tq.Schedule(name="old")
    book, _, save = make_book(book_mod, [schedule])
    tasks = [tq.DailyTask()]
    after = tq.AfterCompletion(actions=["exit_game"], power_action="sleep")
    book.apply_edit(schedule, "  早上  ", tasks, after)
    assert schedule.name == "早上"
    assert schedule.tasks == tasks and schedule.after_completion == after
    book.apply_edit(schedule, "   ", tasks, after)
    assert schedule.name is None
    assert save.calls == 2


def test_book_copy_main_tasks_gives_independent_copies(mods):
    tq, system_task, book_mod = mods
    main = [tq.DailyTask(enabled=False), tq.MirrorTask(name="镜牢 A")]
    book, _, _ = make_book(book_mod, main_tasks=main)
    copies = book.copy_main_tasks()
    assert [t.model_dump(exclude={"id"}) for t in copies] == [t.model_dump(exclude={"id"}) for t in main]
    assert not {t.id for t in copies} & {t.id for t in main}
    copies[1].name = "改过"
    assert main[1].name == "镜牢 A"
