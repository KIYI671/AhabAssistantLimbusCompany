"""
theme pack catalog test

主题包权重的唯一来源是 assets/config/theme_pack_list.example.yaml
app/theme_pack_setting_interface.py 只负责把权重 key 映射到展示名和封面
用 AST + ruamel 静态比对两边，不 import UI 模块，避免依赖图形环境

主题包选择走 Automation.find_str_in_text 的子串匹配（忽略空格），
因此 key 是卡包名的片段而不是全名。find_str_in_text 按 dict 的插入顺序
遍历，先匹配上的先返回，所以 yaml 里的书写顺序决定了片段的归属，
这里按同样的顺序校验
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Dict, List, Optional

from ruamel.yaml import YAML

REPO_ROOT: Path = Path(__file__).resolve().parents[1]
CATALOG_PATH: Path = REPO_ROOT / "assets" / "config" / "theme_pack_list.example.yaml"
INTERFACE_PATH: Path = REPO_ROOT / "app" / "theme_pack_setting_interface.py"
COVER_DIR: Path = REPO_ROOT / "assets" / "app" / "theme_packs"


def _catalog() -> Dict[str, Dict[str, int]]:
    """从 example.yaml 里加载各难度的主题包权重表"""
    data = YAML().load(CATALOG_PATH.read_text(encoding="utf-8"))
    assert isinstance(data, dict), f"theme_pack_list.example.yaml 顶层应为 mapping，实际为 {type(data).__name__}"
    return {
        section: {str(key): int(weight) for key, weight in data[section].items()}
        for section in (
            "theme_pack_list",
            "theme_pack_list_hard",
            "theme_pack_list_cn",
            "theme_pack_list_hard_cn",
        )
    }


def _interface_dict(name: str) -> Dict[str, str]:
    """从 theme_pack_setting_interface.py 的 AST 里提取指定的字面量字典"""
    tree: ast.Module = ast.parse(INTERFACE_PATH.read_text(encoding="utf-8"))
    for node in tree.body:
        if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Dict):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == name:
                return ast.literal_eval(node.value)
    raise AssertionError(f"theme_pack_setting_interface.py 里找不到 {name}")


def _keywords(*sections: str) -> List[str]:
    """按 get_effective_theme_pack_list 合并名单的顺序取出关键词"""
    catalog = _catalog()
    return [key for section in sections for key in catalog[section]]


def _match(text: str, keywords: List[str]) -> Optional[str]:
    """复刻 Automation.find_str_in_text：忽略空格的子串匹配，按顺序取首个命中"""
    haystack = text.replace(" ", "").lower()
    for keyword in keywords:
        if keyword.replace(" ", "").lower() in haystack:
            return keyword
    return None


def test_ocr_alternatives_are_configured_on_both_sides() -> None:
    # 备用名称在 GUI 中不展示，但必须和主名称一样在 yaml 里有独立权重
    cn_keys = set(_keywords("theme_pack_list_cn", "theme_pack_list_hard_cn"))
    for alternative, main_name in _interface_dict("CN_OCR_ALTERNATIVES").items():
        assert alternative in cn_keys, f"OCR 备用名称 {alternative} 未配置权重"
        assert main_name in cn_keys, f"OCR 主名称 {main_name} 未配置权重"


def test_renamed_translations_keep_old_and_new_keywords() -> None:
    # 零协会把「无作为者」改为「未曾面对」、「无慈悲者」改为「无法去爱」
    # 新旧译名没有公共子串，两边都要能命中且权重一致
    base_cn = _catalog()["theme_pack_list_cn"]
    for old_name, new_name in (("无作为", "未曾面对"), ("无慈悲", "无法去爱")):
        assert new_name in base_cn, f"缺少新译名关键词 {new_name}"
        assert base_cn[new_name] == base_cn[old_name], f"{new_name} 与 {old_name} 权重不一致"

    keywords = _keywords("theme_pack_list_cn")
    assert _match("无作为者", keywords) == "无作为"
    assert _match("未曾面对", keywords) == "未曾面对"
    assert _match("无慈悲者", keywords) == "无慈悲"
    assert _match("无法去爱", keywords) == "无法去爱"


def test_rerun_theme_packs_share_the_original_keyword() -> None:
    # 复刻卡包和本体共用一套关键词和一份权重，短关键词的 OCR 容错率也更高
    cn_keywords = _keywords("theme_pack_list_cn", "theme_pack_list_hard_cn")
    for original, rerun, expected in (
        ("LCB定期体检", "LCB定期体检 复刻", "体检"),
        ("深夜清扫", "深夜清扫 复刻", "清扫"),
        ("肉斩骨断", "肉斩骨断 复刻", "骨断"),
        ("时间杀人时间", "时间杀人时间 复刻", "时间杀人"),
        ("WARP快车谋杀案", "WARP快车谋杀案 复刻", "谋杀"),
        ("20区的奇迹", "20区的奇迹 复刻", "区的奇"),
    ):
        assert _match(original, cn_keywords) == expected, original
        assert _match(rerun, cn_keywords) == expected, rerun

    en_keywords = _keywords("theme_pack_list", "theme_pack_list_hard")
    assert _match("Miracle in District 20", en_keywords) == "miracle"
    assert _match("Miracle in District 20 BokGak", en_keywords) == "miracle"


def test_wrath_keywords_separate_normal_and_hard_variants() -> None:
    # 压抑的暴怒是普通主题包，解放的暴怒是困难独有，两者不能互相抢匹配
    cn_keywords = _keywords("theme_pack_list_cn", "theme_pack_list_hard_cn")
    assert _match("压抑的暴怒", cn_keywords) == "压抑的"
    assert _match("解放的暴怒", cn_keywords) == "解放的"

    # 普通名单排在困难名单之前，Repressed Wrath 始终由 wrath 命中
    en_keywords = _keywords("theme_pack_list", "theme_pack_list_hard")
    assert _match("Repressed Wrath", en_keywords) == "wrath"


def test_emotion_keywords_match_their_own_theme_pack() -> None:
    # 情感系卡包关键词密集，改动展示名时容易互相抢匹配
    cn_keywords = _keywords("theme_pack_list_cn")
    assert _match("因情感困惑者", cn_keywords) == "情感困惑"
    assert _match("空转的怠惰", cn_keywords) == "空转"
    assert _match("于情感沉溺者", cn_keywords) == "沉溺者"


def test_configured_covers_exist() -> None:
    # 展示名和封面都以权重 key 为准，配置了封面就必须有对应图片
    for name in ("THEME_PACK_IMAGE_MAP", "THEME_PACK_HARD_IMAGE_MAP"):
        missing = sorted(
            cover for cover in _interface_dict(name).values()
            if not (COVER_DIR / cover).is_file()
        )
        assert missing == [], f"{name} 配置了不存在的封面：{missing}"
