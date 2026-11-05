"""Observation tab geometry and strict final-selection checks."""

import re

KNOWN_OBSERVATION_NAMES = {
    "general_3_1_7": ("盛情款待", "Grand Welcome", "Grand Hospitality"),
    "general_3_3_3": ("锐利的针与线", "Sharp Needle & Thread", "Sharp Needle and Thread", "Sharp Thread and Needle"),
}


def tab_positions(burn, bleed, scale):
    """Measure the live tab pitch rather than assuming the old 110px pitch."""
    if not burn or not bleed:
        raise RuntimeError("观测饰品：无法同时识别烧伤和流血分类，停止选择")
    step = bleed[0] - burn[0]
    if not 80 * scale <= step <= 150 * scale or abs(bleed[1] - burn[1]) > 35 * scale:
        raise RuntimeError("观测饰品：分类按钮位置异常，停止选择")
    return [(burn[0] + step * i, burn[1]) for i in range(11)]


def reset_tab_indices(index):
    if not 0 <= index <= 10:
        raise ValueError("Invalid observation system index")
    return (1 if index == 0 else 0), index


def selected_count(words):
    text = " ".join(words or [])
    matches = re.findall(r"(\d+)\s*[/／]\s*(\d+)", text)
    if len(matches) != 1:
        raise RuntimeError("观测饰品：无法读出已选数量，停止确认")
    count, limit = map(int, matches[0])
    if not 0 <= count <= limit <= 3:
        raise RuntimeError("观测饰品：已选数量异常，停止确认")
    return count


def verify_count(words, expected):
    actual = selected_count(words)
    if actual != expected:
        raise RuntimeError(f"观测饰品：计划选择 {expected} 件，实际仅 {actual} 件，停止确认")


def verify_known_name(gift_id, words):
    names = KNOWN_OBSERVATION_NAMES.get(gift_id)
    if names is None:
        return
    text = "".join("".join(words or []).split()).casefold()
    if not any("".join(name.split()).casefold() in text for name in names):
        raise RuntimeError(f"观测饰品：未在已选列表核实 {names[0]}，请检查行列位置")
