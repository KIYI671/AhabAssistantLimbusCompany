"""Exercise actual AST-extracted bodies without Windows/Qt/emulator imports.

Only platform services and timing helpers are mocked; production control flow and
method-to-method calls run unchanged. Timing helper internals have separate tests.
"""

import __future__

import ast
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import Mock

import pytest

ROOT = Path(__file__).resolve().parents[1]
INPUT = "module/automation/input_handlers/input.py"
MUMU = "module/automation/input_handlers/simulator/mumu_control.py"


def _extract(path, owner, names, globals_):
    tree = ast.parse((ROOT / path).read_text(encoding="utf-8"))
    body = tree.body if owner is None else next(
        node.body for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == owner
    )
    functions = [node for node in body
                 if isinstance(node, ast.FunctionDef) and node.name in names]
    assert {node.name for node in functions} == set(names)
    for node in functions:
        node.decorator_list = []
    module = ast.Module(body=functions, type_ignores=[])
    namespace = dict(globals_)
    exec(compile(module, str(ROOT / path), "exec",
                 flags=__future__.annotations.compiler_flag, dont_inherit=True), namespace)
    return {name: namespace[name] for name in names}


def _record(events, name):
    return lambda *args, **kwargs: events.append((name, *args))


def _globals(events):
    return dict(log=Mock(), sleep=_record(events, "fixed"),
                sleep_gameplay=_record(events, "gameplay"),
                sleep_input_hold=_record(events, "hold"))


@pytest.mark.parametrize("branch,failed,pause", [
    ("normal", False, True),
    ("defense", True, True), ("defense", False, False),
    ("avoid", True, True), ("avoid", False, False),
    ("prioritize", True, False),
])
def test_battle_p_enter_timing(branch, failed, pause):
    events = []
    auto = Mock(key_press=_record(events, "key"))
    auto.find_element.side_effect = lambda path, **kw: (
        pause if path == "battle/pause_assets.png" else True
    )
    functions = _extract("tasks/battle/battle.py", "Battle", ["_battle_operation"],
                         dict(_globals(events), auto=auto))
    battle = type("Battle", (), functions)()
    battle.defense_all_time = battle.mouse_click_rate = False
    battle._defense_this_round = Mock(return_value=not failed)
    battle._chain_battle = Mock(return_value=not failed)
    assert battle._battle_operation(
        first_turn=True, defense_first_round=branch == "defense",
        avoid_skill_3=branch == "avoid", prioritize_skill_3=branch == "prioritize",
    ) is False
    pair = [("key", "p"), ("gameplay", 0.5), ("key", "enter")]
    expected = pair + [("fixed", 1)] if branch == "normal" else (
        (pair if failed else []) + [("fixed", 2)] + (pair if not pause else [])
    )
    assert events == expected
    auto.mouse_click_blank.assert_called_once_with()
    if branch in ("avoid", "prioritize"):
        battle._chain_battle.assert_called_once_with(prioritize_skill_3=branch == "prioritize")


@pytest.mark.parametrize("box", [None, (5, 6)])
@pytest.mark.parametrize("found,count", [([(20, 30)], 1), ([None, (20, 30)], 3),
                                        ([None, None], 3)])
def test_daily_readiness_and_repeat_clicks(box, found, count):
    events = []
    auto = Mock(mouse_click=_record(events, "click"))
    auto.click_element.return_value = (5, 6)
    auto.find_element.side_effect = found
    prepare = _extract("tasks/daily/luxcavation.py", None,
                       ["_prepare_continuous_combat_count"],
                       dict(_globals(events), auto=auto))["_prepare_continuous_combat_count"]
    assert prepare(count, "test", box) is bool(found[-1])
    expected = [("click", 5, 6), ("fixed", 0.4)]
    if len(found) == 2:
        expected += [("fixed", 0.2)]
    if found[-1]:
        expected += [("click", 20, 30), ("gameplay", 0.1)] * (count - 1)
    assert events == expected
    if box is None:
        auto.click_element.assert_called_once_with(
            "luxcavation/thread_continuous_combat_show_box.png", threshold=0.85, click=False)
    else:
        auto.click_element.assert_not_called()


def _windows(owner, post, events):
    mode = "PostMessage" if post else "SendMessage"
    api = NS(MAKELONG=lambda x, y: (x, y))
    for dispatch in ("SendMessage", "PostMessage"):
        setattr(api, dispatch, lambda hwnd, msg, wp, lp, dispatch=dispatch:
                events.append((dispatch, msg, lp)))
    handle = NS(hwnd=123, set_window_pos=Mock())
    globals_ = dict(_globals(events), win32api=api,
                    win32con=NS(WM_LBUTTONDOWN="down", WM_LBUTTONUP="up"),
                    screen=NS(handle=handle), cfg=NS(config=NS(mouse_down_duration=0.07)),
                    random=NS(randint=lambda low, high: 0))
    names = ["mouse_click", "mouse_click_blank", "mouse_down", "mouse_up", "mouse_drag"]
    instance = type(owner, (), _extract(INPUT, owner, names, globals_))()
    instance.use_post_message = post
    instance.set_mouse_pos = Mock()
    instance.set_active = Mock()
    instance.wait_pause = Mock()
    instance._set_window_pos = Mock(return_value=(100, 200))
    instance._window_move_to = Mock()
    return instance, handle, mode


@pytest.mark.parametrize("post", [False, True], ids=["SendMessage", "PostMessage"])
@pytest.mark.parametrize("blank", [False, True], ids=["click", "blank"])
def test_background_click_hold_keeps_dispatch_sleeps(post, blank):
    events = []
    instance, _, mode = _windows("BackgroundInput", post, events)
    if blank:
        result = instance.mouse_click_blank((12, 34), times=2, move_back=False)
    else:
        result = instance.mouse_click(12, 34, times=2, move_back=False)
    assert result is True
    down, up = (0.02 + 0.07, 0.02) if post else (0.01, 0.01)
    assert events == [
        (mode, "down", (12, 34)), ("fixed", down), ("hold", 0.03),
        (mode, "up", (12, 34)), ("fixed", up),
    ] * 2
    instance.wait_pause.assert_called_once_with()


@pytest.mark.parametrize("post", [False, True], ids=["SendMessage", "PostMessage"])
@pytest.mark.parametrize("blank", [False, True], ids=["click", "blank-delegate"])
def test_window_move_click_opts_into_variable_hold(post, blank):
    events = []
    instance, handle, mode = _windows("WindowMoveInput", post, events)
    if blank:
        result = instance.mouse_click_blank((12, 34), times=2)
    else:
        result = instance.mouse_click(12, 34, times=2)
    assert result is True
    down, up = (0.02 + 0.07, 0.02) if post else (0.01, 0.01)
    assert events == [
        (mode, "down", (12, 34)), ("hold", down),
        (mode, "up", (12, 34)), ("fixed", up),
    ] * 2
    handle.set_window_pos.assert_called_once_with(100, 200)
    instance.wait_pause.assert_called_once_with()
    events.clear()
    instance.mouse_down(12, 34)  # Gesture callers do not opt in.
    assert events == [(mode, "down", (12, 34)), ("fixed", down)]


@pytest.mark.parametrize("owner", ["BackgroundInput", "WindowMoveInput"])
@pytest.mark.parametrize("post", [False, True])
@pytest.mark.parametrize("duration,settle", [(0.1, 0.5), (2, 0.6)])
def test_drag_retains_fixed_hold_movement_and_settle(owner, post, duration, settle):
    events = []
    instance, _, mode = _windows(owner, post, events)
    instance.mouse_drag(12, 34, drag_time=duration, dx=5, dy=6, move_back=False)
    down, up = (0.02 + 0.07, 0.02) if post else (0.01, 0.01)
    assert events == [
        (mode, "down", (12, 34)), ("fixed", down), ("fixed", settle),
        (mode, "up", (17, 40)), ("fixed", up),
    ]
    movement = instance.set_mouse_pos if owner == "BackgroundInput" else instance._window_move_to
    movement.assert_any_call(17, 40, duration=duration)


@pytest.mark.parametrize("method,args,expected", [
    ("key_press", ("p",), [("key_down", 44), ("hold", 0.015), ("key_up", 44)]),
    ("click", (12, 34), [("down", 12, 34), ("hold", 0.015), ("up",), ("fixed", 0.035)]),
    ("long_click", (12, 34, 0.8),
     [("down", 12, 34), ("hold", 0.8), ("up",), ("fixed", 0.050)]),
])
def test_mumu_holds_and_post_release_sleeps(method, args, expected):
    events = []
    globals_ = dict(_globals(events), time=NS(sleep=_record(events, "fixed")),
                    usual_key_code={"p": 44})
    instance = type("MumuControl", (), _extract(MUMU, "MumuControl", [method], globals_))()
    for name in ("down", "up", "key_down", "key_up"):
        setattr(instance, name, _record(events, name))
    getattr(instance, method)(*args)
    assert events == expected
