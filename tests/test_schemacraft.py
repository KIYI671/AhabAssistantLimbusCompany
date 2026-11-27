from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from PIL import Image

from module.automation import auto
from tasks.base import script_task_scheme
from tasks.tools import schemacraft
from tasks.tools.schemacraft import (
    MAP_SETTINGS,
    SCAN_MAP,
    SCAN_MAP_UP,
    SchemacraftFrame,
    SchemacraftRun,
)


def test_simulator_run_uses_guest_coordinates_and_touch_without_a_windows_handle(monkeypatch):
    touch = Mock(is_pause=False)
    connect = Mock()
    monkeypatch.setattr(schemacraft, "cfg", SimpleNamespace(simulator=True))
    monkeypatch.setattr(schemacraft, "screen", object())
    monkeypatch.setattr(script_task_scheme, "init_game", connect)
    monkeypatch.setattr(auto, "input_handler", touch)
    monkeypatch.setattr(schemacraft.ScreenShot, "take_screenshot", Mock(return_value=Image.new("RGB", (1920, 1080))))
    run = SchemacraftRun()
    monkeypatch.setattr(run.stop_requested, "wait", Mock())
    now = 0
    actions = iter([("进入节点", (1280, 720)), ("查看地图", SCAN_MAP), None, ("结束", None)])

    def next_action(_frame):
        nonlocal now
        action = next(actions)
        if action is None:
            run.round_exp = 66
            now += 30  # 模拟结算后慢于普通操作上限的加载。
        return action

    monkeypatch.setattr(schemacraft, "monotonic", lambda: now)
    monkeypatch.setattr(run, "next_action", next_action)

    run._play()

    connect.assert_called_once_with()
    touch.mouse_click.assert_called_once_with(960, 540)
    touch.mouse_drag.assert_called_once_with(900, 555, 0.3, 0, -360)


def test_map_prefers_reachable_regular_encounters():
    frame = Mock(spec=SchemacraftFrame)
    visible = {"map_info": True, "roll": (2200, 1120)}
    frame.find.side_effect = lambda name, *args, **kwargs: visible.get(name)
    frame.schema_number.return_value = 1
    nodes = {"regular": (1608, 716), "respite_node": (952, 720), "danger_node": (624, 720)}
    frame.reachable_node.side_effect = nodes.get
    run = SchemacraftRun()

    assert run.next_action(frame)[1] == nodes.pop("regular")
    assert run.next_action(frame)[1] == nodes.pop("respite_node")
    run.entering_encounter = True
    visible = {"respite": True, "bonus_roll": (1600, 540)}
    assert run.next_action(frame)[1] == (1600, 540)
    assert not run.entering_encounter
    visible = {"map_info": True, "roll": True}
    assert run.next_action(frame)[1] == nodes["danger_node"]


def test_settles_after_first_floor_and_restarts_until_pass_cap():
    frame = Mock(spec=SchemacraftFrame)
    frame.find.side_effect = lambda name, *args, **kwargs: visible.get(name)
    frame.bright_fraction.return_value = 0.5
    frame.schema_number.return_value = 1
    frame.read_text.return_value = ""
    frame.reachable_node.side_effect = {"regular": (1608, 716), "danger_node": (624, 720)}.get
    run = SchemacraftRun()

    visible = {"encounter": (2250, 1284)}
    assert run.next_action(frame)[1] == (2250, 1284)
    visible = {"map_info": True, "roll": True}
    assert run.next_action(frame) is None
    visible = {"report": True}
    assert run.next_action(frame)[1] == (2302, 1309)
    visible = {"pack_choice": True, "open_pack": True}
    assert run.next_action(frame)[1] == (2330, 1319)
    assert run.next_action(frame)[1] == (2330, 1319)
    assert run.regular_wins == 1
    visible = {"encounter": (2250, 1284)}
    assert run.next_action(frame)[1] == (2250, 1284)
    visible = {"report": True}
    run.next_action(frame)
    visible = {"pack_choice": True, "open_pack": True}
    run.next_action(frame)
    visible = {"map_info": True, "roll": True}
    assert run.next_action(frame)[1] == (1608, 716)
    run.regular_wins = 4
    assert run.next_action(frame)[1] == (624, 720)
    frame.schema_number.return_value = 2
    assert run.next_action(frame)[1] == MAP_SETTINGS
    visible = {"forfeit_menu": True}
    assert run.next_action(frame)[1] == (1280, 780)
    visible = {"forfeit_dialog": True}
    assert run.next_action(frame)[1] == (1480, 916)
    visible = {"map_info": True, "roll": True}
    assert run.next_action(frame) is None
    visible = {"final_results": True}
    frame.read_text.side_effect = ["Schemacraft Pass EXP +3", "63/1000"]
    assert run.next_action(frame)[0] == "本局获得 3 点通行证经验"
    visible = {"pass_popup": True, "final_results": True}
    assert run.next_action(frame)[1] == (1280, 1024)
    visible = {"lobby": True}
    frame.read_text.side_effect = None
    frame.read_text.return_value = "63/1000"
    assert run.next_action(frame)[1] == (2173, 1216)
    assert not run.settle_at_map

    visible = {"final_results": True}
    frame.read_text.side_effect = ["Schemacraft Pass EXP +1", "1000/1000"]
    assert run.next_action(frame)[0] == "本局获得 1 点通行证经验"
    visible = {"lobby": True}
    assert run.next_action(frame) == ("本周图式构筑通行证经验已达上限", None)


@pytest.mark.parametrize("floor", [2, 3])
def test_resuming_a_later_floor_closes_encounter_and_settles(floor):
    frame = Mock(spec=SchemacraftFrame)
    visible = {"encounter": (2250, 1284), "visited_encounter": True}
    frame.find.side_effect = lambda name, *args, **kwargs: visible.get(name)
    frame.schema_number.return_value = floor
    run = SchemacraftRun()

    assert run.next_action(frame) == ("关闭遭遇面板，准备结算", (720, 430))
    visible = {"map_info": True, "roll": True}
    assert run.next_action(frame)[1] == MAP_SETTINGS
    frame.reachable_node.assert_not_called()


def test_finishes_first_floor_boss_rewards_before_settling(monkeypatch):
    frame = Mock(spec=SchemacraftFrame)
    visible = {"map_info": True, "roll": True}
    frame.find.side_effect = lambda name, *args, **kwargs: visible.get(name)
    frame.reachable_node.side_effect = {"danger_node": (624, 720)}.get
    frame.schema_number.return_value = 1
    frame.bright_fraction.return_value = 0.5
    run = SchemacraftRun()
    info = Mock()
    now = 0
    monkeypatch.setattr(schemacraft, "monotonic", lambda: now)
    monkeypatch.setattr(schemacraft.log, "info", info)

    assert run.next_action(frame)[1] == (624, 720)
    now = 2
    visible = {"encounter": (2250, 1284), "boss_encounter": True}
    assert run.next_action(frame)[1] == (2250, 1284)
    now = 6
    visible = {"battle": True}
    assert run.next_action(frame) is None
    now = 15
    visible = {"report": True}
    run.next_action(frame)
    now = 16
    run.next_action(frame)
    visible = {"schema_rewards": True, "schema_confirm": True}
    assert run.next_action(frame)[1] == (2293, 1317)
    visible = {"sinner_packs": True, "schema_confirm": True}
    assert run.next_action(frame)[1] == (2293, 1317)
    now = 20
    frame.schema_number.return_value = None
    visible = {"map_info": True, "roll": True}
    assert run.next_action(frame)[1] == MAP_SETTINGS
    frame.schema_number.return_value = 2
    assert run.next_action(frame)[1] == MAP_SETTINGS
    node_rows = [
        call.args[0] % call.args[1:] for call in info.call_args_list if call.args[0].startswith("图式构筑节点")
    ]
    assert node_rows == [
        f"图式构筑节点 运行={run.run_id} 局=1 层=1 节点=1 类型=首领战 结果=胜利 "
        "选路秒=2.00 节点秒=18.00 战斗秒=9.00 战后秒=5.00 前台等待秒=0.00"
    ]


def test_uses_reachable_event_when_dice_marker_is_missed(monkeypatch):
    frame = Mock(spec=SchemacraftFrame)
    visible = {"map_info": True, "roll": True}
    frame.find.side_effect = lambda name, *args, **kwargs: visible.get(name)
    frame.reachable_node.side_effect = {"event_node": (1608, 1046)}.get
    frame.schema_number.return_value = 1
    frame.blue_fraction.return_value = 0.8
    frame.bright_fraction.return_value = 0.5
    run = SchemacraftRun()
    info = Mock()
    monkeypatch.setattr(schemacraft.log, "info", info)

    assert run.next_action(frame)[1] == (1608, 1046)
    assert run.entering_event
    visible = {"encounter": (2250, 1284)}
    run.next_action(frame)
    visible = {}
    frame.text_positions.return_value = [("Decline", (1940, 700))]
    assert run.next_action(frame)[1] == (1940, 700)
    frame.text_positions.return_value = [("Confirm", (2310, 827))]
    assert run.next_action(frame)[1] == (2310, 827)
    visible = {"map_info": True, "roll": True}
    frame.reachable_node.side_effect = {"respite_node": (952, 720)}.get
    frame.text_positions.return_value = []
    assert run.next_action(frame)[1] == (952, 720)
    visible = {"encounter": (2250, 1284)}
    run.next_action(frame)
    visible = {"respite": True, "bonus_roll": (1600, 540), "respite_select": True}
    assert run.next_action(frame)[1] == (2293, 1317)
    visible = {"map_info": True, "roll": True}
    run.next_action(frame)
    node_rows = [call.args for call in info.call_args_list if call.args[0].startswith("图式构筑节点")]
    assert [row[3:7] for row in node_rows] == [(1, 1, "事件", "跳过"), (1, 2, "休整", "完成")]


def test_keeps_the_run_when_no_node_is_recognized(monkeypatch):
    frame = Mock(spec=SchemacraftFrame)
    frame.find.side_effect = lambda name, *args, **kwargs: name in {"map_info", "roll"}
    frame.schema_number.return_value = 1
    frame.reachable_node.return_value = None
    frame.highlighted_map_node.return_value = None
    frame.player_position.return_value = None
    frame.read_text.return_value = "0"
    run = SchemacraftRun()
    run.rolled_at = 1
    run.recovery_rerolls = 2
    monkeypatch.setattr(schemacraft, "monotonic", lambda: 12)

    frame.map_route_above.return_value = True
    assert run.next_action(frame) == ("搜索地图上可达的节点", SCAN_MAP_UP)
    run.map_recovery = 5
    frame.reachable_cleared_node.return_value = (1120, 720)
    assert run.next_action(frame) == ("移动到已通关节点", (1120, 720))
    frame.reachable_cleared_node.return_value = None
    assert run.next_action(frame) == ("反向搜索地图上可达的节点", SCAN_MAP)
    run.map_recovery = 5
    with pytest.raises(RuntimeError, match="已保留当前局"):
        run.next_action(frame)
    assert not run.settle_at_map

    visible = {"encounter": (2250, 1284), "visited_encounter": True}
    frame.find.side_effect = lambda name, *args, **kwargs: visible.get(name)
    assert run.next_action(frame) == ("确认移动到已通关节点", (2250, 1284))
    assert run.node_timing is None
    assert not run.entering_encounter
    del visible["visited_encounter"]
    run.cleared_node_selected = True
    assert run.next_action(frame) == ("确认移动到已通关节点", (2250, 1284))
    assert run.node_timing is None
    run.cleared_node_selected = False
    run.map_since = None
    frame.read_text.return_value = "Respite · Already Visited"
    assert run.next_action(frame) == ("确认移动到已通关节点", (2250, 1284))
    assert run.node_timing is None


def test_cleared_node_prefers_a_route_that_was_not_just_used():
    frame = Mock(spec=SchemacraftFrame)
    frame.find.return_value = [(700, 650), (950, 850)]
    frame.blue_fraction.return_value = 0.5

    assert SchemacraftFrame.reachable_cleared_node(frame, [(698, 654)]) == (950, 850)
    assert SchemacraftFrame.reachable_cleared_node(frame, target=(980, 950)) == (950, 850)


def test_reward_pack_with_two_identities_uses_both_picks():
    frame = Mock(spec=SchemacraftFrame)
    frame.find.side_effect = lambda name, *args, **kwargs: [(550, 384), (880, 384)] if name == "reward_team" else []
    frame.has_empty_counter.return_value = False
    frame.read_text.side_effect = ["ID 0/2", "ID 0/2", "ID 1/2"]
    run = SchemacraftRun()

    assert run.choose_reward(frame)[1] == (633, 600)
    assert run.choose_reward(frame)[1] == (633, 600)
    assert run.choose_reward(frame)[1] == (963, 600)


def test_unacknowledged_recruit_can_fall_back_to_sliver_on_same_card(monkeypatch):
    frame = Mock(spec=SchemacraftFrame)
    locations = {"reward_team": [(550, 384)], "reward_sliver": [(716, 384)]}
    frame.find.side_effect = lambda name, *args, **kwargs: locations.get(name, [])
    frame.read_text.return_value = "ID 0/2"
    frame.has_empty_counter.return_value = False
    frame.selected_tab.return_value = False
    run = SchemacraftRun()
    now = 0
    monkeypatch.setattr(schemacraft, "monotonic", lambda: now)

    assert run.choose_reward(frame) == ("招募新的人格", (633, 600))
    now = 9
    assert run.choose_reward(frame) == ("切换到碎片奖励", (716, 384))
    frame.selected_tab.return_value = True
    assert run.choose_reward(frame) == ("选取人格碎片", (633, 600))


def test_elite_tutorial_and_rewards_can_return_to_map():
    frame = Mock(spec=SchemacraftFrame)
    visible = {"tutorial_back": (190, 94)}
    frame.find.side_effect = lambda name, *args, **kwargs: visible.get(name)
    run = SchemacraftRun()
    run.schema = 1
    run.begin_node()
    run.end_node_battle("胜利")

    assert run.next_action(frame) == ("关闭图式构筑教程", (190, 94))
    frame.read_text.assert_not_called()
    visible = {"elite_reward": True, "elite_decline": (2240, 408), "elite_confirm": (2250, 1382)}
    frame.bright_fraction.return_value = 0.05
    assert run.next_action(frame) == ("跳过精英奖励", (2240, 408))
    assert run.node_timing.kind == "精英战"
    frame.bright_fraction.return_value = 0.5
    assert run.next_action(frame) == ("确认精英奖励", (2250, 1382))
    visible["elite_unclaimed"] = True
    assert run.next_action(frame) == ("确认放弃精英奖励", (1480, 916))


def test_battle_closes_ego_details():
    frame = Mock(spec=SchemacraftFrame)
    visible = {"ego_details": True, "battle": True}
    frame.find.side_effect = lambda name, *args, **kwargs: visible.get(name)
    run = SchemacraftRun()

    assert run.next_action(frame) == ("关闭 E.G.O. 详情，继续战斗", (690, 280))
    del visible["ego_details"]
    assert run.next_action(frame) is None
    assert run.waiting_for_battle


def test_defeat_after_report_corrects_node_result():
    frame = Mock(spec=SchemacraftFrame)
    visible = {"report": True}
    frame.find.side_effect = lambda name, *args, **kwargs: visible.get(name)
    run = SchemacraftRun()
    run.schema = 1
    run.boss_encounter = True
    run.begin_node()

    run.next_action(frame)
    battle_ended_at = run.node_timing.battle_ended_at
    assert run.node_timing.outcome == "胜利"
    visible = {"battle_retry": True}
    assert run.next_action(frame)[0] == "战斗失利，返回地图结算本局"
    assert run.node_timing.outcome == "失败"
    assert run.node_timing.battle_ended_at == battle_ended_at
