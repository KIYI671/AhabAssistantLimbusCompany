from __future__ import annotations

from tasks.teams.team_formation import find_named_team_position


def test_find_named_team_position_rejects_prefix_match() -> None:
    ocr_positions = {
        "编队#10": [150, 156],
        "编队 #11": [150, 202],
    }

    assert find_named_team_position(1, ocr_positions) is False


def test_find_named_team_position_returns_only_the_exact_chinese_number() -> None:
    ocr_positions = {
        "编队#10": [150, 156],
        "编队 #1": [150, 202],
        "编队 #11": [150, 248],
    }

    assert find_named_team_position(1, ocr_positions) == [150, 202]
    assert find_named_team_position(10, ocr_positions) == [150, 156]


def test_find_named_team_position_supports_english_and_ocr_fallback_names() -> None:
    assert find_named_team_position(2, {"TEAMS #2": [100, 200]}) == [100, 200]
    assert find_named_team_position(2, {"TFAMS#2": [100, 200]}) == [100, 200]
    assert find_named_team_position(2, {"TEAMS #20": [100, 200]}) is False


def test_find_named_team_position_uses_the_exact_number_when_custom_font_garbles_the_prefix() -> None:
    text_positions = {
        "���#10": [155, 586],
        "Ԥ��#1": [154, 221],
        "���#11": [155, 631],
    }

    assert find_named_team_position(1, text_positions) == [154, 221]
    assert find_named_team_position(10, text_positions) == [155, 586]
