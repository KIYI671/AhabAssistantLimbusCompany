from unittest.mock import Mock

from tasks.tools.schemacraft import SchemacraftFrame, SchemacraftRun


def test_map_prefers_reachable_regular_encounters():
    frame = Mock(spec=SchemacraftFrame)
    gear = (2442, 98)
    visible = {"map_info": True, "roll": (2200, 1120)}
    frame.find.side_effect = lambda name, *args, **kwargs: visible.get(name)
    frame.first_schema_score.return_value = 0.75
    nodes = {"regular_translucent": (1608, 716), "respite_node": (952, 720), "danger_node": (624, 720)}
    frame.reachable_node.side_effect = nodes.get
    run = SchemacraftRun()

    assert run.next_action(frame)[1] == nodes.pop("regular_translucent")
    assert run.next_action(frame)[1] == nodes.pop("respite_node")
    assert run.next_action(frame)[1] == gear


def test_settles_after_one_win_and_restarts_until_pass_cap():
    frame = Mock(spec=SchemacraftFrame)
    frame.find.side_effect = lambda name, *args, **kwargs: visible.get(name)
    frame.bright_fraction.return_value = 0.5
    frame.first_schema_score.return_value = 0.75
    run = SchemacraftRun()

    visible = {"encounter": (2250, 1284)}
    assert run.next_action(frame)[1] == (2250, 1284)
    visible = {"map_info": True, "roll": True, "cleared_node": [(952, 718)]}
    assert run.next_action(frame) is None
    visible = {"report": True}
    assert run.next_action(frame)[1] == (2302, 1309)
    visible = {"pack_choice": True, "open_pack": True}
    assert run.next_action(frame)[1] == (2330, 1319)
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
