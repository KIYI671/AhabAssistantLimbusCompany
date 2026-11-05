"""Original cadence comparisons and virtual input traces; no physical game I/O."""
from upstream_reference import REFERENCE, original_source

import ast
import inspect
import threading
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


class Clock:
    def __init__(self):
        self.now = 0.0
        self.waits = []

    def __call__(self):
        return self.now

    def sleep(self, duration):
        self.waits.append(duration)
        self.now += duration


def source_class(file, name, methods, namespace):
    tree = ast.parse((ROOT / file).read_text(encoding="utf-8"))
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == name)
    cls.bases, cls.keywords = [], []
    cls.body = [node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name in methods]
    exec(compile(ast.fix_missing_locations(ast.Module(body=[cls], type_ignores=[])), file, "exec"), namespace)
    return namespace[name]


def dispatch_fixture():
    clock = Clock()
    config = SimpleNamespace(mouse_action_interval=.5, screenshot_interval=.85)
    ns = dict(threading=threading, GATE_WAIT_TIMEOUT=30, cfg=config,
              time=SimpleNamespace(time=clock, monotonic=clock, sleep=clock.sleep),
              Image=Image.Image, log=Mock())
    cls = source_class("module/automation/automation.py", "Automation", {
        "_run_business_interaction", "monitor_mouse_click", "mouse_action_with_pos",
        "take_screenshot", "take_monitor_screenshot",
    }, ns)
    auto = cls()
    auto._input_lock = threading.RLock()
    auto._screenshot_lock = threading.RLock()
    auto._interaction_gate = threading.Event()
    auto._interaction_gate.set()
    auto.last_click_time = auto.last_screenshot_time = 0
    events = []
    def click(x, y, times=1, **kwargs):
        events.extend(("click", clock(), (x, y)) for _ in range(times))
        return True
    auto.input_handler = SimpleNamespace(
        mouse_click=click, mouse_click_blank=lambda times=1: click(1,1,times=times),
        mouse_drag=lambda *a, **kw: None, mouse_drag_down=lambda *a, **kw: None, mouse_scroll=lambda: None,
        key_press=lambda key: events.append(("key",clock(),key)),
        mouse_drag_link=lambda *args, **kw: events.append(("chain",clock(),args)),
        mouse_to_blank=lambda: events.append(("move",clock(),None)),
        mouse_hold=lambda *args, duration: (events.append(("hold",clock(),duration)),clock.sleep(duration)),
        mouse_end_hold=lambda: events.append(("release",clock(),None)),
    )
    for method in vars(auto.input_handler):
        setattr(auto,method,auto._run_business_interaction(method))
    auto.calculate_click_position=lambda coordinates, offset:coordinates
    return auto,config,clock,events,ns


@pytest.mark.parametrize("method,args",[("key_press",("enter",)),("mouse_to_blank",()),
                                       ("mouse_drag_link",([(1,2),(3,4)],))])
def test_raw_inputs_have_no_new_global_wait(method,args):
    auto,_,clock,events,_=dispatch_fixture()
    auto.mouse_click(1,2)
    getattr(auto,method)(*args)
    auto.mouse_click(3,4,times=3)
    assert len(events)==5 and clock.waits==[]
    assert all(event[1]==0 for event in events)


def test_high_level_click_keeps_original_gap_and_recognition_offsets_wait():
    auto,_,clock,events,_=dispatch_fixture()
    auto.mouse_action_with_pos((1,2),offset=False)
    clock.now+=.3
    auto.mouse_action_with_pos((3,4),offset=False)
    assert [event[1] for event in events]==pytest.approx([.5,1])
    assert clock.waits==pytest.approx([.5,.2])
    auto.key_press("p")
    auto.mouse_click(5,6)
    assert clock.now==1  # direct calls do not share the high-level limiter


def test_multiple_targets_keep_original_one_second_spacing():
    auto,_,_,events,_=dispatch_fixture()
    auto.mouse_action_with_pos([(1,2),(3,4),(5,6)],offset=False,
                               find_type="image_with_multiple_targets")
    assert [event[1] for event in events]==[1,2,3]


def test_fixed_holds_and_release_are_not_throttled():
    auto,config,clock,events,_=dispatch_fixture()
    config.mouse_action_interval=10
    auto.mouse_click(1,2)
    auto.mouse_hold(1,2,duration=.8)
    auto.mouse_hold(1,2,duration=1.2)
    auto.mouse_end_hold()
    assert clock.waits==[.8,1.2] and events[-1]==("release",2,None)


def test_monitor_capture_and_click_do_not_consume_business_intervals():
    auto,_,clock,events,ns=dispatch_fixture()
    def capture(gray=True):
        events.append(("capture",clock(),gray))
        return Image.new("L" if gray else "RGB",(10,10))
    ns["ScreenShot"]=SimpleNamespace(take_screenshot=capture)
    auto._latest_screenshot=None
    auto._remember_screenshot=lambda frame:None
    clock.now=10
    auto.take_screenshot()
    auto.take_monitor_screenshot()
    auto.take_screenshot()
    assert [event[1] for event in events]==pytest.approx([10,10,10.85])
    auto.monitor_mouse_click(1,2,times=2)
    assert events[-1][1]==pytest.approx(10.85)


@pytest.mark.parametrize("relative,cls,methods",[
    ("module/automation/automation.py","Automation",["_run_business_interaction","monitor_mouse_click",
      "click_element","mouse_action_with_pos","take_screenshot"]),
    ("tasks/battle/battle.py","Battle",["_battle_operation","_defense_this_round"]),
])
def test_original_entry_points_match_published_16_ast(relative,cls,methods):
    import subprocess
    original=original_source(relative)
    def functions(text):
        parent=next(n for n in ast.parse(text).body if isinstance(n,ast.ClassDef) and n.name==cls)
        return {n.name:ast.dump(n) for n in parent.body if isinstance(n,ast.FunctionDef)}
    a,b=functions(original),functions((ROOT/relative).read_text(encoding="utf-8"))
    for name in methods:assert a[name]==b[name],name


@pytest.mark.parametrize("relative",["module/automation/screenshot.py","tasks/teams/team_formation.py"])
def test_restored_whole_modules_match_published_16(relative):
    import subprocess
    original=original_source(relative)
    assert ast.dump(ast.parse(original))==ast.dump(ast.parse((ROOT/relative).read_text(encoding="utf-8")))
