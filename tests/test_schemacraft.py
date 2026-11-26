from unittest.mock import Mock

from tasks.tools.schemacraft import SchemacraftFrame, SchemacraftRun


def test_map_prefers_reachable_regular_encounters():
    frame = Mock(spec=SchemacraftFrame)
    frame.find.side_effect = lambda name, *args, **kwargs: name == "roll"
    nodes = {"regular_translucent": (1608, 716), "respite_node": (952, 720), "danger_node": (624, 720)}
    frame.reachable_node.side_effect = nodes.get
    run = SchemacraftRun()

    assert run.next_action(frame)[1] == nodes.pop("regular_translucent")
    assert run.next_action(frame)[1] == nodes.pop("respite_node")
    assert run.next_action(frame)[1] == nodes.pop("danger_node")
