from unittest.mock import Mock

from tasks.tools.schemacraft import SchemacraftFrame, SchemacraftRun


def test_map_prefers_reachable_regular_encounters():
    frame = Mock(spec=SchemacraftFrame)
    gear = (2442, 98)
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
    assert run.next_action(frame)[1] == gear


def test_settles_after_two_wins_and_restarts_until_pass_cap():
    frame = Mock(spec=SchemacraftFrame)
    frame.find.side_effect = lambda name, *args, **kwargs: visible.get(name)
    frame.bright_fraction.return_value = 0.5
    frame.schema_number.return_value = 1
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
    assert run.next_action(frame)[1] == (2442, 98)
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


def test_second_floor_mode_only_fights_boss_on_first_floor():
    frame = Mock(spec=SchemacraftFrame)
    visible = {"map_info": True, "roll": True}
    frame.find.side_effect = lambda name, *args, **kwargs: visible.get(name)
    frame.reachable_node.side_effect = {"danger_node": (624, 720)}.get
    frame.schema_number.return_value = 1
    run = SchemacraftRun(second_floor_wins=1)

    assert run.next_action(frame)[1] == (624, 720)
    visible = {"encounter": (2250, 1284), "boss_encounter": True}
    assert run.next_action(frame)[1] == (2250, 1284)
    frame.schema_number.return_value = 2
    run.entering_encounter = False
    visible = {"map_info": True, "roll": True}
    assert run.next_action(frame)[1] == (2442, 98)

    assert SchemacraftRun(second_floor_wins=0).next_action(frame)[1] == (2442, 98)

    run = SchemacraftRun(second_floor_wins=1)
    frame.reachable_node.side_effect = {"regular": (1608, 716), "danger_node": (624, 720)}.get
    assert run.next_action(frame)[1] == (1608, 716)
    visible = {"encounter": (2250, 1284)}
    assert run.next_action(frame)[1] == (2250, 1284)
    visible = {"report": True}
    run.next_action(frame)
    visible = {"pack_choice": True}
    frame.bright_fraction.return_value = 0
    run.next_action(frame)
    assert run.regular_wins == 1
    visible = {"map_info": True, "roll": True}
    assert run.next_action(frame)[1] == (2442, 98)


def test_reward_pack_with_two_identities_uses_both_picks():
    frame = Mock(spec=SchemacraftFrame)
    frame.find.side_effect = lambda name, *args, **kwargs: [(550, 384), (880, 384)] if name == "reward_team" else []
    frame.has_empty_counter.return_value = False
    frame.read_text.side_effect = ["ID 0/2", "ID 1/2"]
    run = SchemacraftRun()

    assert run.choose_reward(frame)[1] == (633, 600)
    assert run.choose_reward(frame)[1] == (963, 600)
