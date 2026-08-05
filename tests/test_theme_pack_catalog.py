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


def test_user_config_merge_drops_keywords_removed_from_the_example() -> None:
    # 关键词改名后，用户配置里的旧关键词必须丢弃：残留的短关键词仍会参与
    # OCR 子串匹配，并抢走困难侧同名系列卡包（如 und 抢 Unbound Wrath）
    from module.config.config import Theme_pack_list

    merged = {
        "preferred_thresholds": 0,
        "theme_pack_list": {"nagel": 0, "devoured": 0},
        "theme_pack_list_hard": {"excessive": -5},
    }
    user_config = {
        "preferred_thresholds": 2,
        "theme_pack_list": {"nagel": 1, "und": 0, "glutton": 0},
        "theme_pack_list_hard": {"excessive": -5},
    }
    Theme_pack_list._update_config(merged, user_config)

    assert merged["preferred_thresholds"] == 2
    assert merged["theme_pack_list"] == {"nagel": 1, "devoured": 0}
    assert merged["theme_pack_list_hard"] == {"excessive": -5}


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


def test_emotion_keywords_match_their_own_theme_pack() -> None:
    # 情感系卡包关键词密集，改动展示名时容易互相抢匹配
    cn_keywords = _keywords("theme_pack_list_cn")
    assert _match("因情感困惑者", cn_keywords) == "情感困惑"
    assert _match("空转的怠惰", cn_keywords) == "空转"
    assert _match("于情感沉溺者", cn_keywords) == "沉溺者"


def test_english_keywords_do_not_shadow_other_theme_packs() -> None:
    # 关键词是卡包名的片段，短片段容易被别的卡包名包含。
    # 下列卡包名取自游戏 EN_MirrorDungeonTheme-1.json，普通与困难同名系列成对列出，
    # 普通名单先于困难名单合并，普通侧的片段一旦过短就会抢走困难侧的卡包。
    en_keywords = _keywords("theme_pack_list", "theme_pack_list_hard")
    for name, expected in (
        ("Nagel and Hammer", "nagel"),
        ("Thunder and Lightning", "thunder"),
        ("To be Crushed", "crushed"),
        ("Crushers & Breakers", "crushers"),
        ("Repressed Wrath", "repressed"),
        ("Unbound Wrath", "unbound"),
        ("Treadwheel Sloth", "treadwheel"),
        ("Inert Sloth", "inert"),
        ("Devoured Gluttony", "devoured"),
        ("Excessive Gluttony", "excessive"),
        ("Degraded Gloom", "degraded"),
        ("Sunk Gloom", "sunk"),
        ("Mnestic Experience", "mnestic"),
        ("Crushing External Force", "external"),
    ):
        assert _match(name, en_keywords) == expected, name


def test_english_ocr_fallbacks_are_configured_on_both_sides() -> None:
    # 英文 OCR 短片段兜底与中文侧（海边/切琢/凤皇）同构：yaml 里紧跟主
    # 关键词配置独立权重。备用 key 不能进 NAME_MAP，否则反向映射会被它
    # 覆盖，主 key 的权重不再随中文界面调整而同步（Theb/b·e 先例）
    catalog = _catalog()
    name_maps = {
        False: _interface_dict("THEME_PACK_NAME_MAP"),
        True: _interface_dict("THEME_PACK_HARD_NAME_MAP"),
    }
    for fallback, main in _interface_dict("EN_OCR_ALTERNATIVES").items():
        hard = main in catalog["theme_pack_list_hard"]
        weights = catalog["theme_pack_list_hard" if hard else "theme_pack_list"]
        assert main in weights, f"英文 OCR 主关键词 {main} 未在 yaml 中配置权重"
        assert fallback in weights, f"英文 OCR 兜底 {fallback} 未在 yaml 中配置权重"
        assert weights[fallback] == weights[main], f"英文 OCR 兜底 {fallback} 与主关键词 {main} 权重不一致"
        assert fallback not in name_maps[hard], f"英文 OCR 兜底 {fallback} 不应进入 NAME_MAP"


def test_english_ocr_fallbacks_are_short_unique_fragments() -> None:
    # 兜底片段必须比主关键词短，且只出现在自己卡包的英文名里，
    # 否则会像修掉的 und/wrath 一样抢走别的卡包
    image_maps = {
        **_interface_dict("THEME_PACK_IMAGE_MAP"),
        **_interface_dict("THEME_PACK_HARD_IMAGE_MAP"),
    }
    english_names = {
        key: Path(filename).stem.lower().replace(" ", "")
        for key, filename in image_maps.items()
    }
    english_names["mnestic"] = "mnesticexperience"

    for fallback, main in _interface_dict("EN_OCR_ALTERNATIVES").items():
        assert len(fallback) < len(main), f"英文 OCR 兜底 {fallback} 没有缩短关键词"
        if "·" in fallback:
            # 带点号的兜底只匹配 OCR 误识别，官方卡包名里不会出现点号
            assert not any(fallback in name for name in english_names.values()), (
                f"英文 OCR 兜底 {fallback} 不应出现在任何官方卡包名中"
            )
        else:
            fallback_names = {name for name in english_names.values() if fallback in name}
            main_names = {name for name in english_names.values() if main in name}
            assert fallback_names == main_names and fallback_names, (
                f"英文 OCR 兜底 {fallback} 不是主关键词 {main} 的专属片段：{fallback_names}"
            )


def test_english_keywords_do_not_cover_each_other() -> None:
    # 除设计内的主备对（EN_OCR_ALTERNATIVES）外，任意两个英文关键词不得
    # 互为子串：过短的片段会抢走别的卡包（und/wrath 教训）。后续新增短链
    # 与其他关键词冲突时，此测试会先报出未登记或缺失的覆盖关系
    keywords = _keywords("theme_pack_list", "theme_pack_list_hard")
    expected_covers = {
        frozenset((fallback, main))
        for fallback, main in _interface_dict("EN_OCR_ALTERNATIVES").items()
        if fallback.lower() in main.lower() or main.lower() in fallback.lower()
    }
    covers = set()
    for index, first in enumerate(keywords):
        for second in keywords[index + 1:]:
            if first.lower() in second.lower() or second.lower() in first.lower():
                covers.add(frozenset((first, second)))
    assert covers == expected_covers, (
        f"英文关键词存在未登记的覆盖关系：{covers - expected_covers}；"
        f"登记但实际不覆盖：{expected_covers - covers}"
    )


def test_weights_match_between_languages() -> None:
    # 同一卡包的中英默认权重必须一致，否则选包行为会随界面语言变化
    catalog = _catalog()
    name_map = _interface_dict("THEME_PACK_NAME_MAP")
    hard_name_map = _interface_dict("THEME_PACK_HARD_NAME_MAP")
    for en_section, cn_section, mapping in (
        ("theme_pack_list", "theme_pack_list_cn", name_map),
        ("theme_pack_list_hard", "theme_pack_list_hard_cn", hard_name_map),
    ):
        en_weights, cn_weights = catalog[en_section], catalog[cn_section]
        mismatched = {
            en_key: (weight, mapping[en_key], cn_weights[mapping[en_key]])
            for en_key, weight in en_weights.items()
            if en_key in mapping
            and mapping[en_key] in cn_weights
            and weight != cn_weights[mapping[en_key]]
        }
        assert mismatched == {}, f"{en_section} 与 {cn_section} 权重不一致：{mismatched}"


def test_unknown_fallback_weight_is_configurable() -> None:
    # 识别不到任何关键词时兜底到「未知 / unknown」的权重，而不是硬编码常量
    catalog = _catalog()
    assert "unknown" in catalog["theme_pack_list"], "英文名单缺少 unknown 兜底项"
    assert "未知" in catalog["theme_pack_list_cn"], "中文名单缺少未知兜底项"
    assert catalog["theme_pack_list"]["unknown"] == catalog["theme_pack_list_cn"]["未知"]

    source = (REPO_ROOT / "tasks" / "mirror" / "select_theme_pack.py").read_text(encoding="utf-8")
    assert 'theme_pack_list_zh.get("未知"' in source, "兜底权重未从中文名单读取"
    assert 'theme_pack_list_en.get("unknown"' in source, "兜底权重未从英文名单读取"
    assert "theme_pack_weight = unknown_weight" in source, "未命中分支未使用兜底权重"


def test_unknown_keyword_never_shadows_a_real_theme_pack() -> None:
    # 兜底项也在名单里参与子串匹配，不能抢走任何真实卡包
    for sections, fallback, samples in (
        (("theme_pack_list_cn", "theme_pack_list_hard_cn"), "未知", ("因情感困惑者", "经验记忆", "善意的巡礼")),
        (("theme_pack_list", "theme_pack_list_hard"), "unknown", ("Mnestic Experience", "Repressed Wrath")),
    ):
        keywords = _keywords(*sections)
        for sample in samples:
            assert _match(sample, keywords) != fallback, sample


def test_configured_covers_exist() -> None:
    # 展示名和封面都以权重 key 为准，配置了封面就必须有对应图片
    for name in ("THEME_PACK_IMAGE_MAP", "THEME_PACK_HARD_IMAGE_MAP"):
        missing = sorted(
            cover for cover in _interface_dict(name).values()
            if not (COVER_DIR / cover).is_file()
        )
        assert missing == [], f"{name} 配置了不存在的封面：{missing}"
