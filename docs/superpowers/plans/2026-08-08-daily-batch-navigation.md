# 日常本批次导航 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让经验本与纽本各自的重复场次之间直接切换，并在每个日常项目完成后只换饼一次，同时阻止预设项误选和选队失败后的空编队开战。

**Architecture:** 单场经验本/纽本流程只负责进入副本、选队和战斗结算；日常调度器将经验本和纽本作为两个项目组，在每组的全部配置次数完成后执行一次既有主页导航与换饼。队伍名称匹配继续容忍字体乱码的编号，但明确排除“预设/Preset”条目；日常调用方必须检查 `select_battle_team()` 的布尔结果后才能进入 `Battle.to_battle()`。

**Tech Stack:** Python、pytest、pytest monkeypatch、现有任务调度与 Automation 接口。

## Global Constraints

- 每个日常项目组完成全部配置次数后只执行一次 `back_init_menu()` 和一次 `make_enkephalin_module()`；次数为零的项目不执行这两项操作。
- 成功的单场经验本/纽本不执行主页导航或换饼；同项目的下一场复用现有采光导航。
- 不改变经验本后纽本的现有执行顺序、次数计算、连续战斗拆分、领奖/镜牢调度或配置字段。
- `find_named_team_position()` 必须拒绝已被 OCR 正常识别为“预设/Preset”的条目，但仍允许无法识别前缀时以精确编号作兜底。
- `select_battle_team()` 返回 `False` 时，经验本与纽本流程必须立即返回 `False`，不可调用 `battle.to_battle()`。
- 不新增依赖；遵循项目既有 ruff 规则。生产代码改动必须先有对应失败测试。

---

## 文件职责

| 文件 | 修改目的 |
| --- | --- |
| `tests/test_team_name_selection.py` | 锁定“预设 #1”不能冒充目标编队，且真实编队的精确编号仍可匹配。 |
| `tests/test_daily_team_selection.py` | 锁定选队失败不会进入开始战斗，以及每个日常项目只在完成全部次数后执行一次主页导航与换饼。 |
| `tasks/teams/team_formation.py` | 在编号兜底匹配前过滤可辨认的预设项。 |
| `tasks/base/script_task_scheme.py` | 在选队失败时中止；将主页导航和换饼从单场流程收敛到经验本/纽本项目组结束点。 |

### Task 1: 防止预设误选和空编队开战

**Files:**
- Modify: `tests/test_team_name_selection.py:32-41`
- Create: `tests/test_daily_team_selection.py`
- Modify: `tasks/teams/team_formation.py:84-93`
- Modify: `tasks/base/script_task_scheme.py:53-84`

**Interfaces:**
- Consumes: `find_named_team_position(num: int, text_positions: dict[str, list[float]]) -> list[float] | bool`。
- Consumes: `select_battle_team(team: int) -> bool`。
- Produces: `onetime_EXP_process()` 与 `onetime_thread_process()` 在选队失败时返回 `False`，且不调用 `battle.to_battle()`。

- [ ] **Step 1: 写入“预设 #1 不能匹配队伍 #1”的失败测试**

在 `tests/test_team_name_selection.py` 追加：

```python
def test_find_named_team_position_rejects_preset_with_the_requested_number() -> None:
    text_positions = {
        "预设#1": [162.5, 220.5],
        "编队#2": [163.0, 434.0],
        "编队#10": [155.0, 586.0],
    }

    assert find_named_team_position(1, text_positions) is False
    assert find_named_team_position(2, text_positions) == [163.0, 434.0]
    assert find_named_team_position(10, text_positions) == [155.0, 586.0]
```

- [ ] **Step 2: 写入经验本与纽本的选队失败防护测试**

创建 `tests/test_daily_team_selection.py`：

```python
from __future__ import annotations

import importlib
from types import SimpleNamespace

import pytest


@pytest.mark.parametrize(
    ("process_name", "entrypoint_name"),
    [
        ("onetime_EXP_process", "EXP_luxcavation"),
        ("onetime_thread_process", "thread_luxcavation"),
    ],
)
def test_daily_process_does_not_start_battle_when_team_selection_fails(
    monkeypatch,
    process_name: str,
    entrypoint_name: str,
) -> None:
    scheme = importlib.import_module("tasks.base.script_task_scheme")
    calls: list[object] = []
    monkeypatch.setattr(
        scheme,
        "cfg",
        SimpleNamespace(
            targeted_teaming_EXP=False,
            targeted_teaming_thread=False,
            daily_teams=1,
        ),
    )
    monkeypatch.setattr(scheme, entrypoint_name, lambda count: calls.append((entrypoint_name, count)))
    monkeypatch.setattr(scheme, "select_battle_team", lambda team: False)
    monkeypatch.setattr(
        scheme.battle,
        "to_battle",
        lambda: pytest.fail("选队失败后不应尝试开始战斗"),
    )

    assert getattr(scheme, process_name)() is False
    assert calls == [(entrypoint_name, 1)]
```

- [ ] **Step 3: 运行测试并确认红灯**

Run:

```bash
.venv/Scripts/python.exe -m pytest tests/test_team_name_selection.py::test_find_named_team_position_rejects_preset_with_the_requested_number tests/test_daily_team_selection.py -q
```

Expected: 3 项失败。旧匹配器把“预设#1”当作队伍 #1；两条日常流程在 `select_battle_team()` 返回 `False` 后仍调用 `battle.to_battle()`。

- [ ] **Step 4: 最小化实现预设过滤和选队失败中断**

将 `tasks/teams/team_formation.py` 的匹配循环替换为：

```python
for text, position in text_positions.items():
    normalized = text.replace(" ", "")
    if re.search(r"预设|preset", normalized, flags=re.IGNORECASE):
        continue
    if re.search(pattern, normalized, flags=re.IGNORECASE):
        return position
```

在 `onetime_EXP_process()` 中将：

```python
EXP_luxcavation(combat_count)
select_battle_team(team)
if battle.to_battle() is False:
```

替换为：

```python
EXP_luxcavation(combat_count)
if select_battle_team(team) is False:
    log.error(f"经验本未能选择队伍 # {team}，取消开始战斗")
    return False
if battle.to_battle() is False:
```

在 `onetime_thread_process()` 中相同位置替换为：

```python
thread_luxcavation(combat_count)
if select_battle_team(team) is False:
    log.error(f"纽本未能选择队伍 # {team}，取消开始战斗")
    return False
if battle.to_battle() is False:
```

- [ ] **Step 5: 运行任务测试并提交前置防护**

Run:

```bash
.venv/Scripts/python.exe -m pytest tests/test_team_name_selection.py tests/test_daily_team_selection.py tests/test_server_error_recovery.py -q
git diff --check
git add tasks/teams/team_formation.py tasks/base/script_task_scheme.py tests/test_team_name_selection.py tests/test_daily_team_selection.py
git commit -m "fix: guard daily team selection failures"
```

Expected: 所有三组测试通过，且提交仅包含预设过滤、选队失败中断及其测试。

### Task 2: 将主页初始化和换饼收敛到每个日常项目结束点

**Files:**
- Modify: `tests/test_daily_team_selection.py`
- Modify: `tasks/base/script_task_scheme.py:53-84,270-287`

**Interfaces:**
- Consumes: `Daily_task_wrapper(get_reward=None) -> Callable[[], None]`。
- Consumes: `_single_combat_run(exp_times, thread_times)` 与 `_batch_combat(process_fn, times, max_times)`。
- Produces: 成功的单场流程不调用主页导航或换饼；经验本组和纽本组各自在完成全部次数后调用一次 `back_init_menu()` 与 `make_enkephalin_module()`。

- [ ] **Step 1: 写入每个日常项目结束后只初始化一次的失败测试**

追加到 `tests/test_daily_team_selection.py`：

```python
def test_daily_groups_initialize_after_each_enabled_group(monkeypatch) -> None:
    scheme = importlib.import_module("tasks.base.script_task_scheme")
    calls: list[str] = []
    monkeypatch.setattr(
        scheme,
        "cfg",
        SimpleNamespace(
            set_EXP_count=2,
            set_thread_count=1,
            config=SimpleNamespace(use_continuous_combat=False),
            use_continuous_combat_select=1,
        ),
    )
    monkeypatch.setattr(scheme, "back_init_menu", lambda: calls.append("home"))
    monkeypatch.setattr(scheme, "make_enkephalin_module", lambda: calls.append("enkephalin"))
    monkeypatch.setattr(scheme, "onetime_EXP_process", lambda: calls.append("exp"))
    monkeypatch.setattr(scheme, "onetime_thread_process", lambda: calls.append("thread"))

    scheme.Daily_task_wrapper()()

    assert calls == ["exp", "exp", "home", "enkephalin", "thread", "home", "enkephalin"]
```

追加单场流程的成功路径参数化测试：

```python
@pytest.mark.parametrize(
    ("process_name", "entrypoint_name"),
    [
        ("onetime_EXP_process", "EXP_luxcavation"),
        ("onetime_thread_process", "thread_luxcavation"),
    ],
)
def test_successful_daily_process_keeps_current_navigation(
    monkeypatch,
    process_name: str,
    entrypoint_name: str,
) -> None:
    scheme = importlib.import_module("tasks.base.script_task_scheme")
    calls: list[str] = []
    monkeypatch.setattr(
        scheme,
        "cfg",
        SimpleNamespace(
            targeted_teaming_EXP=False,
            targeted_teaming_thread=False,
            daily_teams=1,
        ),
    )
    monkeypatch.setattr(scheme, entrypoint_name, lambda count: calls.append(entrypoint_name))
    monkeypatch.setattr(scheme, "select_battle_team", lambda team: True)
    monkeypatch.setattr(scheme.battle, "to_battle", lambda: None)
    monkeypatch.setattr(scheme.battle, "fight", lambda **kwargs: calls.append("fight"))
    monkeypatch.setattr(scheme, "back_init_menu", lambda: pytest.fail("单场完成后不应返回主界面"))
    monkeypatch.setattr(scheme, "make_enkephalin_module", lambda: pytest.fail("单场完成后不应重复换饼"))

    getattr(scheme, process_name)()

    assert calls == [entrypoint_name, "fight"]
```

- [ ] **Step 2: 运行导航测试并确认旧实现红灯**

Run:

```bash
.venv/Scripts/python.exe -m pytest tests/test_daily_team_selection.py -q
```

Expected: 新增 3 项失败。项目组测试会在每个单场后出现 `home`、`enkephalin`；单场测试会调用被替换为 `pytest.fail()` 的主页导航或换饼函数。

- [ ] **Step 3: 从两个单场流程移除重复导航，并在项目组结束后恢复一次既有导航**

在 `onetime_EXP_process()` 与 `onetime_thread_process()` 的成功结算末尾，删除：

```python
back_init_menu()
make_enkephalin_module()
```

新增内部帮助函数：

```python
def _complete_daily_group(process_fn, times, max_times, use_continuous_combat):
    if times <= 0:
        return
    if use_continuous_combat:
        _batch_combat(process_fn, times, max_times)
    else:
        for _ in range(times):
            process_fn()
    back_init_menu()
    make_enkephalin_module()
```

将 `Daily_task_wrapper()` 内的日常调用替换为：

```python
use_continuous_combat = cfg.config.use_continuous_combat and cfg.use_continuous_combat_select > 0
max_times = cfg.use_continuous_combat_select
_complete_daily_group(onetime_EXP_process, exp_times, max_times, use_continuous_combat)
_complete_daily_group(onetime_thread_process, thread_times, max_times, use_continuous_combat)
```

不调整 `_batch_combat()`、副本入口函数或后续任务调度。

- [ ] **Step 4: 运行相关测试并确认绿灯**

Run:

```bash
.venv/Scripts/python.exe -m pytest tests/test_daily_team_selection.py tests/test_team_name_selection.py tests/test_server_error_recovery.py -q
```

Expected: 每个项目组只记录一次初始化；成功单场流程保留当前导航；选队失败仍不进战斗。

- [ ] **Step 5: 运行完整验证并提交导航优化**

Run:

```bash
.venv/Scripts/python.exe -m pytest -q
.venv/Scripts/python.exe -m ruff check --ignore E722 tasks/base/script_task_scheme.py tasks/teams/team_formation.py tests/test_daily_team_selection.py tests/test_team_name_selection.py
git diff --check
git add tasks/base/script_task_scheme.py tests/test_daily_team_selection.py
git commit -m "fix: group daily navigation between runs"
```

Expected: 完整 pytest 为零失败；范围 ruff 通过；提交仅包含项目组内导航和换饼收敛及其回归测试。

### Task 3: 用本地 Steam 环境复测已配置日常任务

**Files:**
- Verify: `config.yaml`
- Verify: `logs/debugLog.log`
- Verify: `tasks/base/script_task_scheme.py`

**Interfaces:**
- Consumes: 当前配置的 `select_team_by_order: true`、`daily_teams: 1`、经验本/纽本次数。
- Produces: 一次人工驱动的日志证据，证明启动阶段只初始化一次，副本间无主页/换饼记录。

- [ ] **Step 1: 确认 GUI 已重启并加载当前源码和按顺序选队设置**

Run:

```bash
grep -n 'select_team_by_order\|daily_task\|daily_teams' config.yaml
tasklist.exe | grep -Ei 'LimbusCompany|python'
```

Expected: `select_team_by_order: true`，游戏和源码版 Python GUI 均在运行。

- [ ] **Step 2: 人工在 GUI 启动日常任务并读取日志**

用户点击开始后运行：

```bash
rg -n -C 2 '开始执行 返回主界面|开始执行 体力换饼|开始执行 一次经验本|开始执行 一次纽本|结束执行 一次经验本|结束执行 一次纽本' logs/debugLog.log | tail -160
```

Expected: 批次开头各出现一次“返回主界面”和“体力换饼”；在经验本与纽本之间不出现两项日志；出现按顺序选队成功与对应副本入口日志。

- [ ] **Step 3: 检查最终提交与工作区**

Run:

```bash
git status --short
git log --oneline main..HEAD
git diff --check main...HEAD
```

Expected: 工作区干净；分支只包含规格、队伍防护和日常导航优化的提交；无空白错误。
