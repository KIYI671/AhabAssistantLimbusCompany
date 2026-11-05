"""Node identities shared by route planning, configuration and the editor."""

DEFAULT_ROUTE_WEIGHTS = {
    "battle": 4, "boss_battle": 6, "event": 1, "focused_encounter": 6,
    "risky_encounter": 7, "shop": 2, "abnormality_focused_encounter": 6,
}
ROUTE_NODE_LABELS = {
    "event": "事件／问号", "shop": "商店", "battle": "普通战斗",
    "focused_encounter": "集中遭遇战", "risky_encounter": "精英战斗",
    "abnormality_focused_encounter": "异想体集中遭遇战", "boss_battle": "首领战斗",
}


def validated_route_weights(value):
    if not isinstance(value, dict) or set(value) - DEFAULT_ROUTE_WEIGHTS.keys():
        raise ValueError("寻路权重必须使用已知的节点类型")
    if any(type(weight) is not int or not 0 <= weight <= 999 for weight in value.values()):
        raise ValueError("寻路权重须为0～999的整数，越低越优先")
    return {**DEFAULT_ROUTE_WEIGHTS, **value}
