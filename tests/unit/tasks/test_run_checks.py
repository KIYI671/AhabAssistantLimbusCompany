"""启动前检查（plan_problem）和启动请求对应哪份任务列表（plan_for_request）"""

from types import SimpleNamespace

import pytest


@pytest.fixture(scope="module")
def mods(isolated_import):
    return (
        isolated_import("module.config.task_queue"),
        isolated_import("tasks.base.run_plan"),
        isolated_import("module.start_command"),
    )


def team(sinners=1, fixed=False, select=0):
    return SimpleNamespace(sinners_be_select=sinners, fixed_team_use=fixed, fixed_team_use_select=select)


def check(rp, plan, teams, auto=False, chance=0):
    return rp.plan_problem(plan, teams, auto_hard_mirror=auto, hard_mirror_chance=chance)


# ---------------------------------------------------------------- plan_problem


def test_empty_plan(mods):
    tq, rp, _ = mods
    plan = rp.RunPlan.from_queue([tq.DailyTask(enabled=False)])
    assert check(rp, plan, {}) == rp.Problem("no_tasks")


def test_no_mirror_ignores_teams(mods):
    tq, rp, _ = mods
    plan = rp.RunPlan.from_queue([tq.DailyTask()])
    assert check(rp, plan, {}) is None


def test_mirror_without_selected_team(mods):
    tq, rp, _ = mods
    plan = rp.RunPlan.from_queue([tq.MirrorTask()])
    assert check(rp, plan, {}) == rp.Problem("no_team")


def test_mirror_team_without_sinners(mods):
    tq, rp, _ = mods
    plan = rp.RunPlan.from_queue([tq.MirrorTask()])
    assert check(rp, plan, {1: team(), 3: team(sinners=0)}) == rp.Problem("team_without_sinners", 3)


def test_mirror_hard_needs_hard_team(mods):
    tq, rp, _ = mods
    normal_only = {1: team(fixed=True, select=1)}
    hard = rp.RunPlan.from_queue([tq.MirrorTask(hard_mirror=2)])
    assert check(rp, hard, normal_only) == rp.Problem("no_team_for_hard")
    # 自动困牢还有次数时也按困牢检查
    auto = rp.RunPlan.from_queue([tq.MirrorTask()])
    assert check(rp, auto, normal_only, auto=True, chance=1) == rp.Problem("no_team_for_hard")
    assert check(rp, auto, normal_only, auto=True, chance=0) is None


def test_mirror_normal_needs_normal_team(mods):
    tq, rp, _ = mods
    hard_only = {1: team(fixed=True, select=0)}
    plan = rp.RunPlan.from_queue([tq.MirrorTask()])
    assert check(rp, plan, hard_only) == rp.Problem("no_team_for_normal")
    assert check(rp, plan, {**hard_only, 2: team()}) is None


def test_each_mirror_task_checked_with_own_difficulty(mods):
    tq, rp, _ = mods
    normal_only = {1: team(fixed=True, select=1)}
    plan = rp.RunPlan.from_queue([tq.MirrorTask(), tq.MirrorTask(hard_mirror=1)])
    assert check(rp, plan, normal_only) == rp.Problem("no_team_for_hard")


# ------------------------------------------------------------ plan_for_request


def queue_and_schedules(tq):
    queue = [tq.DailyTask(), tq.RewardTask(enabled=False)]
    schedule = tq.Schedule(
        id="autodaily2", tasks=[tq.MirrorTask()], after_completion=tq.AfterCompletion(power_action="shutdown")
    )
    return queue, [schedule]


def test_schedule_request_uses_schedule_queue(mods):
    tq, rp, sc = mods
    queue, schedules = queue_and_schedules(tq)
    request = sc.StartRequest(start=True, schedule_id="autodaily2")
    plan, schedule = rp.plan_for_request(request, queue, schedules, once=None)
    assert schedule is schedules[0]
    assert [t.type for t in plan.tasks] == ["mirror"]
    assert plan.after_completion.normalized() == ([], "shutdown")
    assert plan.source == "schedule:autodaily2"


def test_missing_schedule_gives_no_plan(mods):
    tq, rp, sc = mods
    queue, schedules = queue_and_schedules(tq)
    request = sc.StartRequest(start=True, schedule_id="autodaily_gone")
    assert rp.plan_for_request(request, queue, schedules, once=None) == (None, None)


def test_cli_after_completion_beats_once(mods):
    tq, rp, sc = mods
    queue, schedules = queue_and_schedules(tq)
    cli = tq.AfterCompletion(actions=["exit_game"])
    once = tq.AfterCompletion(power_action="sleep")
    plan, schedule = rp.plan_for_request(sc.StartRequest(start=True, after_completion=cli), queue, schedules, once)
    assert schedule is None
    assert [t.type for t in plan.tasks] == ["daily"]
    assert plan.after_completion.normalized() == (["exit_game"], "none")
    assert plan.source == "cli"


def test_plain_start_uses_once_then_default(mods):
    tq, rp, sc = mods
    queue, schedules = queue_and_schedules(tq)
    once = tq.AfterCompletion(power_action="sleep")
    plan, _ = rp.plan_for_request(sc.StartRequest(start=True), queue, schedules, once)
    assert plan.after_completion.normalized() == ([], "sleep")
    plan, _ = rp.plan_for_request(None, queue, schedules, None)
    assert plan.after_completion is None
