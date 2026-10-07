"""按队伍名称在编队列表中定位队伍（纯函数，便于单元测试）。

原先用子串匹配 "TEAMS#1"：当前选中的 1 号队伍常被 OCR 读成不带编号的 "TEAMS"，
找不到后向下翻页，"TEAMS#1" 又命中了 "TEAMS#13"，结果选错队伍。

这里改为按行推算：从 OCR 读到的各行编号（容忍 "#" 被读成 "W" 或丢失）按多数一致
确定列表偏移和行距，即使目标行自身编号没读出来，也能按位置找到；
目标在可见范围上方时提示向上翻页，而不是继续向下。
"""

import re
from collections import Counter
from statistics import median

_TEAM_ROW = re.compile(r"^(?:T[EF][AL]\w{0,2}S|编队)")


def locate_named_team(num, rows):
    """在 OCR 行 [(text, (x, y)), ...] 中查找第 num 号队伍。

    返回 ("found", (x, y))、("up", None)、("down", None) 或 ("unknown", None)。
    """
    rows = sorted(
        ((t.upper().replace(" ", ""), p) for t, p in rows if _TEAM_ROW.match(t.upper().replace(" ", ""))),
        key=lambda r: r[1][1],
    )
    if len(rows) < 2:
        return "unknown", None
    gaps = [b[1][1] - a[1][1] for a, b in zip(rows, rows[1:]) if b[1][1] - a[1][1] > 10]
    if not gaps:
        return "unknown", None
    spacing = median(gaps)
    top = rows[0][1][1]
    offsets = Counter()
    for text, (_, y) in rows:
        if m := re.search(r"(\d+)$", text):
            offsets[int(m.group(1)) - round((y - top) / spacing)] += 1
    if not offsets:
        return "unknown", None
    first, votes = offsets.most_common(1)[0]
    if votes < 2:
        return "unknown", None
    last = first + round((rows[-1][1][1] - top) / spacing)
    if num < first:
        return "up", None
    if num > last:
        return "down", None
    expected = top + (num - first) * spacing
    _, position = min(rows, key=lambda r: abs(r[1][1] - expected))
    if abs(position[1] - expected) > spacing / 3:
        return "unknown", None
    return "found", position
