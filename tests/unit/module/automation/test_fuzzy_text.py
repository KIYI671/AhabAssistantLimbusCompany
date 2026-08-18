from module.automation.automation import Automation


def test_theme_pack_fuzzy_matching_repairs_common_ocr_errors():
    automation = object.__new__(Automation)
    targets = {"nsignif": -6, "warp": -6, "tearful": -6}

    for ocr_text, expected in (
        ("significant Envy", "nsignif"),
        ("IVARPEXPRESS", "warp"),
        ("earful Things", "tearful"),
    ):
        result = automation._find_fuzzy_target_in_ocr_dict(targets, {ocr_text: [0, 0]})
        assert result is not None
        assert result.text == expected


def test_non_dict_language_text_keeps_false_on_miss():
    automation = object.__new__(Automation)
    automation._run_ocr_for_text = lambda **_: {"other": [0, 0]}

    assert automation.find_language_text("dead", "dead") is False
