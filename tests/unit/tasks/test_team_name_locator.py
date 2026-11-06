from tasks.teams.team_name_locator import locate_named_team

# 实际 OCR 结果（英文客户端）：列表在顶部，当前选中的 1 号队伍被读成 "TEAMS"，6 号被误读成 "TEAMS8"
TOP = [("Rien/Sora", (193.5, 377.5)), ("TEAMS", (196.5, 466.0)), ("TEAMS#2", (196.0, 521.0)),
       ("TEAMS#3", (195.0, 575.0)), ("TEAMS#4", (195.0, 629.5)), ("TEAMS#5", (195.5, 684.0)),
       ("TEAMS8", (195.5, 738.0)), ("TEALSE7", (196.5, 792.0))]
# 向下翻一页后：旧的子串匹配会把 "TEAMS#1" 命中到 "TEAMS#13"
PAGE2 = [("Rien/Sora", (193.5, 377.5)), ("TEAMS", (194.0, 427.5)), ("TEAMS#13", (195.5, 465.5)),
         ("TEAMS14", (196.0, 519.0)), ("TEAMS#15", (196.0, 574.5)), ("TEAMSW16", (195.5, 628.5)),
         ("TEAMS#17", (196.5, 682.5)), ("TEAMS#18", (196.0, 737.5))]


def test_unlabelled_selected_row_is_team_one():
    assert locate_named_team(1, TOP) == ("found", (196.5, 466.0))


def test_misread_label_does_not_move_target():
    assert locate_named_team(6, TOP) == ("found", (195.5, 738.0))
    assert locate_named_team(8, TOP) == ("down", None)


def test_team_one_never_matches_team_thirteen():
    assert locate_named_team(1, PAGE2) == ("up", None)
    assert locate_named_team(16, PAGE2) == ("found", (195.5, 628.5))


def test_too_little_evidence_is_unknown():
    assert locate_named_team(1, [("TEAMS", (0, 466.0)), ("TEAMS#2", (0, 521.0))]) == ("unknown", None)
    assert locate_named_team(1, []) == ("unknown", None)


def test_chinese_labels():
    rows = [("编队", (0, 100)), ("编队#2", (0, 154)), ("编队#3", (0, 208))]
    assert locate_named_team(1, rows) == ("found", (0, 100))
