"""RunPlan 与执行期纯逻辑的测试"""

import pytest


@pytest.fixture(scope="module")
def mods(isolated_import):
    return isolated_import("module.config.task_queue"), isolated_import("tasks.base.run_plan")


def test_plan_skips_disabled_and_snapshots(mods):
    tq, rp = mods
    queue = [tq.DailyTask(enabled=True), tq.RewardTask(enabled=False), tq.MirrorTask(enabled=True, count=2)]
    plan = rp.RunPlan.from_queue(queue, source="schedule:autodaily")
    assert [t.type for t in plan.tasks] == ["daily", "mirror"]
    assert plan.after_completion is None
    queue[2].count = 9  # 运行期间界面修改不影响本次运行
    assert plan.tasks[1].count == 2
    assert plan.first(tq.MirrorTask) is plan.tasks[1]
    assert plan.first(tq.RewardTask) is None


def test_plan_keeps_order_and_duplicates(mods):
    tq, rp = mods
    queue = [tq.EnkephalinTask(), tq.DailyTask(exp_count=3), tq.DailyTask(exp_count=0, thread_count=2)]
    plan = rp.RunPlan.from_queue(queue, after_completion=tq.AfterCompletion(power_action="shutdown"))
    assert [t.type for t in plan.tasks] == ["enkephalin", "daily", "daily"]
    assert (plan.tasks[1].exp_count, plan.tasks[2].exp_count) == (3, 0)
    assert plan.after_completion.normalized() == ([], "shutdown")


def test_finished_battle_is_used_once(mods):
    tq, rp = mods
    ctx = rp.RunContext(finished_battle="EXP")
    task = tq.DailyTask(exp_count=2, thread_count=3)
    assert rp.daily_times(task, ctx.take_finished_battle()) == (1, 3)
    assert rp.daily_times(task, ctx.take_finished_battle()) == (2, 3)
    assert rp.daily_times(tq.DailyTask(exp_count=0, thread_count=0), "thread") == (0, 0)


@pytest.mark.parametrize(
    ("times", "max_times", "expected"),
    [(0, 3, []), (2, 3, [2]), (3, 3, [3]), (7, 3, [3, 3, 1]), (6, 3, [3, 3]), (2, 0, [1, 1])],
)
def test_split_combat(mods, times, max_times, expected):
    _, rp = mods
    assert rp.split_combat(times, max_times) == expected


def test_daily_teams(mods):
    tq, rp = mods
    task = tq.DailyTask(team=5, exp_team_3_4=2, thread_team_6=4)
    assert rp.exp_team(task, "3_4") == 5 and rp.thread_team(task, 6) == 5
    task.exp_targeted = task.thread_targeted = True
    assert rp.exp_team(task, "3_4") == 2 and rp.thread_team(task, 6) == 4


def test_hard_mirror_and_times(mods):
    tq, rp = mods
    normal = tq.MirrorTask(count=3)
    hard = tq.MirrorTask(count=3, hard_mirror=2, save_rewards=True)
    assert rp.is_hard_mirror(normal, auto_hard_mirror=False, hard_mirror_chance=3) is False
    assert rp.is_hard_mirror(normal, auto_hard_mirror=True, hard_mirror_chance=1) is True
    assert rp.is_hard_mirror(normal, auto_hard_mirror=True, hard_mirror_chance=0) is False
    assert rp.mirror_times(normal, hard=True) == 3
    assert rp.mirror_times(hard, hard=True) == 1
    assert rp.mirror_times(tq.MirrorTask(infinite=True), hard=False) == 9999


def test_team_usable(mods):
    _, rp = mods
    assert rp.team_usable(False, 0, hard=True)
    assert rp.team_usable(True, 0, hard=True) and not rp.team_usable(True, 0, hard=False)
    assert rp.team_usable(True, 1, hard=False) and not rp.team_usable(True, 1, hard=True)
    assert rp.any_team_usable([(True, 1), (True, 0)], hard=True)
    assert not rp.any_team_usable([(True, 1)], hard=True)
