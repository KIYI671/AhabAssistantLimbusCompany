# 应用 UI 配置
from PySide6.QtCore import QT_TRANSLATE_NOOP, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QFrame
from qfluentwidgets import isDarkTheme, qconfig

BORDER_STYLE = {
    "dark": """border: 1px solid #545454; border-radius: {radius}px;""",
    "light": """border: 1px solid #c0c0c0; border-radius: {radius}px;""",
}

# 全局字体配置
FONT_FAMILIES = [
    "Segoe UI",  # Windows 现代UI字体
    "Microsoft YaHei",  # 微软雅黑
    "微软雅黑",  # 微软雅黑中文名
    "Noto Sans CJK SC",  # 跨平台中文字体
    "sans-serif",  # 最后回退到无衬线字体
    "SansSerif",  # 无衬线字体另一个名称
    "SimSun",  # 宋体
]

# 主窗口样式配置
MAIN_WINDOW_STYLES = {
    "dark": {"bg_color": "rgba(28, 28, 28, 1)"},
    "light": {"bg_color": "rgba(255, 255, 255, 1)"},
}

# 标题栏样式配置
TITLE_BAR_STYLES = {
    "dark": {"text_color": "white", "btn_color": Qt.white},
    "light": {"text_color": "black", "btn_color": Qt.black},
}


def apply_font_config():
    """应用全局字体配置"""
    qconfig.fontFamilies.value = FONT_FAMILIES


def get_main_window_style(is_dark: bool) -> dict:
    """获取主窗口样式"""
    return MAIN_WINDOW_STYLES["dark"] if is_dark else MAIN_WINDOW_STYLES["light"]


def get_title_bar_style(is_dark: bool) -> dict:
    """获取标题栏样式"""
    return TITLE_BAR_STYLES["dark"] if is_dark else TITLE_BAR_STYLES["light"]


# 设置卡片样式配置
SETTING_LAYOUT_STYLES = {
    "dark": {
        "border": "1px solid rgba(255, 255, 255, 0.25)",
        "border_hover": "1px solid rgba(255, 255, 255, 0.25)",
    },
    "light": {
        "border": "1px solid rgba(0, 0, 0, 0.25)",
        "border_hover": "1px solid rgba(0, 0, 0, 0.25)",
    },
}


def get_setting_layout_style(is_dark: bool) -> dict:
    """获取设置卡片样式"""
    return SETTING_LAYOUT_STYLES["dark"] if is_dark else SETTING_LAYOUT_STYLES["light"]


LOG_TEXT_EDIT_STYLES = {
    "dark": """
        TextEdit {
            color: rgba(255, 255, 255, 0.75);
            background-color: rgba(255, 255, 255, 0.01);
            border: 1px solid rgba(255, 255, 255, 0.25);
            border-radius: 5px;
            padding: 10px;
        }
        TextEdit:hover {
            background-color: rgba(255, 255, 255, 0.01);
            border: 1px solid rgba(255, 255, 255, 0.25);
        }
        TextEdit:focus {
            background-color: rgba(255, 255, 255, 0.01);
            border: 1px solid rgba(255, 255, 255, 0.25);
        }
    """,
    "light": """
        TextEdit {
            color: rgba(0, 0, 0, 0.75);
            background-color: rgba(0, 0, 0, 0.01);
            border: 1px solid rgba(0, 0, 0, 0.25);
            border-radius: 5px;
            padding: 10px;
        }
        TextEdit:hover {
            background-color: rgba(0, 0, 0, 0.01);
            border: 1px solid rgba(0, 0, 0, 0.25);
        }
        TextEdit:focus {
            background-color: rgba(0, 0, 0, 0.01);
            border: 1px solid rgba(0, 0, 0, 0.25);
        }
    """,
}


def get_log_text_edit_qss() -> tuple[str, str]:
    """Return (light_qss, dark_qss) for the log TextEdit."""
    return LOG_TEXT_EDIT_STYLES["light"], LOG_TEXT_EDIT_STYLES["dark"]


THEME_AWARE_TEXT_BROWSER_STYLES = {
    "dark": """
        ThemeAwareTextBrowser,
        ThemeAwareTextBrowser:hover,
        ThemeAwareTextBrowser:focus,
        ThemeAwareTextBrowser:focus:hover {
            background-color: rgba(28, 28, 28, 1);
            border: none;
        }
    """,
    "light": """
        ThemeAwareTextBrowser,
        ThemeAwareTextBrowser:hover,
        ThemeAwareTextBrowser:focus,
        ThemeAwareTextBrowser:focus:hover {
            background-color: rgba(255, 255, 255, 1);
            border: none;
        }
    """,
}


def get_theme_aware_text_browser_qss() -> tuple[str, str]:
    """Return (light_qss, dark_qss) for ThemeAwareTextBrowser."""
    return (
        THEME_AWARE_TEXT_BROWSER_STYLES["light"],
        THEME_AWARE_TEXT_BROWSER_STYLES["dark"],
    )


# Pivot Item 样式配置
# 注意：{theme_color} 需要在运行时替换
PIVOT_ITEM_STYLES = {
    "light": """
        PivotItem[pivotItem="true"] {{
            background-color: transparent;
            border: none;
            padding: 8px 16px;
            font-family: 'Segoe UI', 'Microsoft YaHei', 'PingFang SC';
            font-size: 14px;
            font-weight: 400;
            text-align: center;
            color: rgba(0, 0, 0, 0.7);
        }}
        PivotItem[pivotItem="true"]:hover {{
            color: rgba(0, 0, 0, 0.9);
        }}
        PivotItem[pivotItem="true"][selected="true"] {{
            color: {theme_color};
        }}
    """,
    "dark": """
        PivotItem[pivotItem="true"] {{
            background-color: transparent;
            border: none;
            padding: 8px 16px;
            font-family: 'Segoe UI', 'Microsoft YaHei', 'PingFang SC';
            font-size: 14px;
            font-weight: 400;
            text-align: center;
            color: rgba(255, 255, 255, 0.7);
        }}
        PivotItem[pivotItem="true"]:hover {{
            color: rgba(255, 255, 255, 0.9);
        }}
        PivotItem[pivotItem="true"][selected="true"] {{
            color: {theme_color};
        }}
    """,
}


def get_pivot_item_qss(theme_color: str) -> tuple[str, str]:
    light_qss = PIVOT_ITEM_STYLES["light"].format(theme_color=theme_color)
    dark_qss = PIVOT_ITEM_STYLES["dark"].format(theme_color=theme_color)
    return light_qss, dark_qss


# SegmentedWidget 样式配置
SEGMENTED_WIDGET_STYLES = {
    "light": """
        SegmentedWidget {{
            background: transparent;
            border: none;
        }}
        SegmentedItem[pivotItem="true"] {{
            padding: 6px 16px;
            font-size: 14px;
            font-weight: 400;
            color: rgba(0, 0, 0, 0.7);
            background: transparent;
            border: none;
        }}
        SegmentedItem[pivotItem="true"]:hover {{
            color: rgba(0, 0, 0, 0.9);
        }}
        SegmentedItem[pivotItem="true"][selected="true"] {{
            color: {theme_color};
            font-weight: bold;
        }}
    """,
    "dark": """
        SegmentedWidget {{
            background: transparent;
            border: none;
        }}
        SegmentedItem[pivotItem="true"] {{
            padding: 6px 16px;
            font-size: 14px;
            font-weight: 400;
            color: rgba(255, 255, 255, 0.7);
            background: transparent;
            border: none;
        }}
        SegmentedItem[pivotItem="true"]:hover {{
            color: rgba(255, 255, 255, 0.9);
        }}
        SegmentedItem[pivotItem="true"][selected="true"] {{
            color: {theme_color};
            font-weight: bold;
        }}
    """,
}


def get_segmented_widget_qss(theme_color: str) -> tuple[str, str]:
    """Return (light_qss, dark_qss) for SegmentedWidget."""
    light_qss = SEGMENTED_WIDGET_STYLES["light"].format(theme_color=theme_color)
    dark_qss = SEGMENTED_WIDGET_STYLES["dark"].format(theme_color=theme_color)
    return light_qss, dark_qss


# 星光加成配置
STARLIGHT_BONUS_NAMES = [
    QT_TRANSLATE_NOOP("CustomizeSettingsModule", "起始之星"),
    QT_TRANSLATE_NOOP("CustomizeSettingsModule", "层积星云"),
    QT_TRANSLATE_NOOP("CustomizeSettingsModule", "星际旅行"),
    QT_TRANSLATE_NOOP("CustomizeSettingsModule", "倾落的流星雨"),
    QT_TRANSLATE_NOOP("CustomizeSettingsModule", "双星商店"),
    QT_TRANSLATE_NOOP("CustomizeSettingsModule", "卫星商店"),
    QT_TRANSLATE_NOOP("CustomizeSettingsModule", "星云的宠爱"),
    QT_TRANSLATE_NOOP("CustomizeSettingsModule", "星芒的引导"),
    QT_TRANSLATE_NOOP("CustomizeSettingsModule", "偶然的彗星"),
    QT_TRANSLATE_NOOP("CustomizeSettingsModule", "全面的可能性"),
]

STARLIGHT_BONUS_COSTS = [10, 10, 20, 20, 30, 30, 40, 40, 50, 60]

STARLIGHT_BONUS_TIPS = [
    {
        "buff": "buff：\n初始经费 +150\n主题卡包出现数量 +1\n商店里展出的饰品数量 +1\n可免费进行商店普通刷新 1次",
        "buff+": "buff+：\n初始经费 \\yellow{+250}\n主题卡包出现数量 +1\n商店里展出的饰品数量 +1\n可免费进行商店普通刷新 1次",
        "buff++": "buff++：\n初始经费 \\yellow{+250}\n主题卡包出现数量 +1\n商店里展出的饰品数量 +1\n可免费进行商店普通刷新 \\yellow{2次}",
    },
    {
        "buff": "buff：\n进入下个阶段时，增加当前经费的10%(最多100)\n售卖饰品所得经费增加50%(每个商店1次)",
        "buff+": "buff+：\n进入下个阶段时，增加当前经费的\\yellow{20%(最多125)}\n售卖饰品所得经费增加\\yellow{75%(每个商店1次)}",
        "buff++": "buff++：\n进入下个阶段时，增加当前经费的\\yellow{30%(最多150)}\n售卖饰品所得经费增加\\yellow{100%(每个商店1次)}",
    },
    {
        "buff": "buff：\n主题卡包出现数量 +1\n主题卡包刷新次数 +2\n选择未记录的主题卡包时，所有人格等级 +3(最多9级)",
        "buff+": "buff+：\n主题卡包出现数量 +1\n主题卡包刷新次数 \\yellow{+3}\n选择未记录的主题卡包时，所有人格等级 +3(最多9级)\n\\yellow{如果解锁了45个及以上主题卡包图鉴中的主题卡包，获得1层拼点威力提升}",
        "buff++": "buff++：\n主题卡包出现数量 +1\n主题卡包刷新次数 \\yellow{+4}\n选择未记录的主题卡包时，所有人格等级 +3(最多9级)\n\\yellow{如果解锁了45个及以上主题卡包图鉴中的主题卡包，获得2层拼点威力提升}",
    },
    {
        "buff": "buff：\n初始经费 +400\n初始饰品可选择数 +1",
        "buff+": "buff+：\n初始经费 \\yellow{+500}\n初始饰品可选择数 +1\n\\yellow{选择遭遇战奖励卡中的星芒选项时，经费 +75}",
        "buff++": "buff++：\n初始经费 \\yellow{+700}\n初始饰品可选择数 +1\n\\yellow{选择遭遇战奖励卡中的星芒选项时，经费 +150}",
    },
    {
        "buff": "buff：\n商店里展出的饰品数量 +1\n战斗胜利时获得的经费 +20%\n提升商店里更高等级饰品的展出概率",
        "buff+": "buff+：\n商店里展出的饰品数量 +1\n战斗胜利时获得的经费 \\yellow{+30%}\n提升商店里更高等级饰品的展出概率\n\\yellow{进入商店时，获得等同于当前持有的饰品等级之和的经费(最多75)}",
        "buff++": "buff++：\n商店里展出的饰品数量 +1\n战斗胜利时获得的经费 \\yellow{+40%}\n提升商店里更高等级饰品的展出概率\n\\yellow{进入商店时，获得等同于当前持有的饰品等级之和的经费(最多150)}",
    },
    {
        "buff": "buff：\n可免费进行商店关键词刷新 1次\n进入第1层时，随机获得1件1级饰品",
        "buff+": "buff+：\n可免费进行商店关键词刷新 1次\n进入第1层时，随机获得\\yellow{2件}1级饰品\n\\yellow{特殊商店出现概率 +10%}",
        "buff++": "buff++：\n可免费进行商店关键词刷新 \\yellow{2次}\n进入第1层时，随机获得\\yellow{3件}1级饰品\n\\yellow{特殊商店出现概率 +25%}",
    },
    {
        "buff": "buff：\n进入第1层时，人格等级 +3\n通过阶段时，人格等级 +1(最多+5)",
        "buff+": "buff+：\n进入第1层时，人格等级 +3\n通过阶段时，人格等级 +1\\yellow{(最多+9)}",
        "buff++": "buff++：\n进入第1层时，人格等级 +3\n\\yellow{进入第6层时，人格等级 +3}\n通过阶段时，人格等级 +1\\yellow{(最多+9)}",
    },
    {
        "buff": "buff：\n最大速度值 +2\n获得1层 拼点威力提升\n获得1层 伤害强化\n获得1层 守护",
        "buff+": "buff+：\n最大速度值 \\yellow{+3}\n获得\\yellow{2层} 拼点威力提升\n获得1层 伤害强化\n获得1层 守护",
        "buff++": "buff++：\n最大速度值 \\yellow{+3}\n获得\\yellow{2层} 拼点威力提升\n获得\\yellow{2层} 伤害强化\n获得\\yellow{2层} 守护",
    },
    {
        "buff": "buff：\n进入商店时，随机获得1件3级及以下的合成/售卖专用饰品\n进入第3层时，随机获得1件3级饰品\n合成时，随机获得比合成产物(3级及以上)低2级的饰品(每个商店最多1次)",
        "buff+": "buff+：\n进入商店时，随机获得1件3级及以下的合成・售卖专用E.G.O饰品\n第5层及以下：\\yellow{1~3级}\n第6层及以上：\\yellow{2~3级}\n进入第3层\\yellow{与第5层}时，随机获得1件所选关键词的3级E.G.O饰品\n合成时，可随机获得比合成产物(3级及以上)低2级的E.G.O饰品(每个商店1次)",
        "buff++": "buff++：\n进入商店时，随机获得1件3级及以下的合成・售卖专用E.G.O饰品\n第5层及以下：\\yellow{2~3级}\n第6层及以上：\\yellow{3~4级}\n进入第3层、第5层\\yellow{与第7层}时，随机获得1件所选关键词的\\yellow{4级}E.G.O饰品\n合成时，可随机获得比合成产物(3级及以上)低\\yellow{1级}的E.G.O饰品(每个商店1次)",
    },
    {
        "buff": "buff：\n主题卡包出现数量 +1\n初始饰品可选择数 +1\n进入镜像迷宫时，选择获得1件所选关键词对应的随机3级饰品(若无该等级的饰品，则会出现更低等级的饰品)\n进入镜像迷宫时，获得1个黯淡的残影",
        "buff+": "buff+：\n主题卡包出现数量 +1\n初始饰品可选择数 +1\n进入镜像迷宫时，选择获得\\yellow{2件}所选关键词对应的随机3级饰品(若无该等级的饰品，则会出现更低等级的饰品)\n进入镜像迷宫时，获得1个黯淡的残影、\\yellow{1个微茫的残影}",
        "buff++": "buff++：\n主题卡包出现数量 +1\n初始饰品可选择数 +1\n进入镜像迷宫时，选择获得\\yellow{3件}所选关键词对应的随机3级饰品(若无该等级的饰品，则会出现更低等级的饰品)\n进入镜像迷宫时，获得1个黯淡的残影、\\yellow{1个微茫的残影}与\\yellow{1个闪耀的残影}",
    },
]

STARLIGHT_BONUS_NAMES_EN = [
    "Star of the Beginning",
    "Cumulating Starcloud",
    "Interstellar Travel",
    "Star-shower",
    "Binary Star-shop",
    "Moon Star-shop",
    "Favor of the Nebulae",
    "Starlight Guidance",
    "Chance Comet",
    "Perfected Possibility",
]

STARLIGHT_ACTION_LABELS_EN = {
    "全选": "Select All",
    "清空": "Clear",
}

STARLIGHT_BONUS_TIPS_EN = [
    {
        "buff": "buff:\nStarting Cost +150\nTheme Pack Selection +1\nShop E.G.O Gift Choice +1\n1 Free normal Refresh(es) for Shops",
        "buff+": "buff+:\nStarting Cost \\yellow{+250}\nTheme Pack Selection +1\nShop E.G.O Gift Choice +1\n1 Free normal Refresh(es) for Shops",
        "buff++": "buff++:\nStarting Cost \\yellow{+250}\nTheme Pack Selection +1\nShop E.G.O Gift Choice +1\n\\yellow{2} Free normal Refresh(es) for Shops",
    },
    {
        "buff": "buff:\nWhen moving to the next floor, increase current Cost balance by 10% (max 100)\nIncrease E.G.O Gift sale price by 50% (once per Shop)",
        "buff+": "buff+:\nWhen moving to the next floor, increase current Cost balance by \\yellow{20% (max 125)}\nIncrease E.G.O Gift sale price by \\yellow{75% (once per Shop)}",
        "buff++": "buff++:\nWhen moving to the next floor, increase current Cost balance by \\yellow{30% (max 150)}\nIncrease E.G.O Gift sale price by \\yellow{100% (once per Shop)}",
    },
    {
        "buff": "buff:\nTheme Pack Selection +1\nTheme Pack Refresh Chance +2\nWhen choosing a new Theme Pack for the first time, all Identities gain +3 Level(s) (max 9)",
        "buff+": "buff+:\nTheme Pack Selection +1\nTheme Pack Refresh Chance \\yellow{+3}\nWhen choosing a new Theme Pack for the first time, all Identities gain +3 Level(s) (max 9)\n\\yellow{If 45+ Theme Packs are unlocked in the Theme Pack Compendium, gain 1 Clash Power Up}",
        "buff++": "buff++:\nTheme Pack Refresh Chance \\yellow{+4}\nWhen choosing a new Theme Pack for the first time, all Identities gain +3 Level(s) (max 9)\n\\yellow{If 45+ Theme Packs are unlocked in the Theme Pack Compendium, gain 2 Clash Power Up}",
    },
    {
        "buff": "buff:\nStarting Cost +400\nStarting E.G.O Gift Choice +1",
        "buff+": "buff+:\nStarting Cost \\yellow{+500}\nStarting E.G.O Gift Choice +1\n\\yellow{When Choosing Starlight from Encounter Reward Cards, Cost +75}",
        "buff++": "buff++:\nStarting Cost \\yellow{+700}\nStarting E.G.O Gift Choice +1\n\\yellow{When Choosing Starlight from Encounter Reward Cards, Cost +150}",
    },
    {
        "buff": "buff:\nShop E.G.O Gift Choice +1\nEncounter Reward Cost +20%\nGreater chance for high Tier E.G.O Gifts to appear in Shops",
        "buff+": "buff+:\nShop E.G.O Gift Choice +1\nEncounter Reward Cost \\yellow{+30%}\nGreater chance for high Tier E.G.O Gifts to appear in Shops\n\\yellow{Upon entering a Shop, add up all the Tier numbers of currently owned E.G.O Gifts}",
        "buff++": "buff++:\nEncounter Reward Cost \\yellow{+40%}\nGreater chance for high Tier E.G.O Gifts to appear in Shops\n\\yellow{Upon entering a Shop, add up all the Tier numbers of currently owned E.G.O Gifts}",
    },
    {
        "buff": "buff:\n1 Free Keyword Refresh(es) for Shops\nUpon entering Floor 1, gain 1 random Tier 1 E.G.O Gift(s)",
        "buff+": "buff+:\n1 Free Keyword Refresh(es) for Shops\nUpon entering Floor 1, gain \\yellow{2} random Tier 1 E.G.O Gift(s)\n\\yellow{+10% chance for Super Shop to appear}",
        "buff++": "buff++:\n\\yellow{2} Free Keyword Refresh(es) for Shops\nUpon entering Floor 1, gain \\yellow{3} random Tier 1 E.G.O Gift(s)\n\\yellow{+25% chance for Super Shop to appear}",
    },
    {
        "buff": "buff:\nUpon entering Floor 1, all Identities gain 3 Level(s)\nUpon Floor clear, all Identities gain 1 Level(s) (max 5)",
        "buff+": "buff+:\nUpon entering Floor 1, all Identities gain 3 Level(s)\nUpon Floor clear, all Identities gain 1 Level(s) \\yellow{(max 9)}",
        "buff++": "buff++:\nUpon entering Floor 1, all Identities gain 3 Level(s)\n\\yellow{Upon entering Floor 6, all Identities gain 3 Level(s)}\nUpon Floor clear, all Identities gain 1 Level(s) \\yellow{(max 9)}",
    },
    {
        "buff": "buff:\nMax Speed +2\nGain 1 Clash Power Up\nGain 1 Damage Up\nGain 1 Protection",
        "buff+": "buff+:\nMax Speed \\yellow{+3}\nGain \\yellow{2} Clash Power Up\nGain 1 Damage Up\nGain 1 Protection",
        "buff++": "buff++:\nMax Speed \\yellow{+3}\nGain \\yellow{2} Clash Power Up\nGain \\yellow{2} Damage Up\nGain \\yellow{2} Protection",
    },
    {
        "buff": "buff:\nFuse or Sale only E.G.O Gift(s)\nUpon entering Floor 3, gain 1 random Tier 3 E.G.O Gift(s)\nWhen Fusing, gain a random additional E.G.O Gift 2 Tiers below the Fusion result(must be Tier 3 or higher) (once per Shop)",
        "buff+": "buff+:\nFuse or Sale only E.G.O Gift(s)\nFloor 5 or lower : \\yellow{Tier 1~3}\nFloor 6 or higher : \\yellow{Tier 2~3}\nUpon entering Floor 3/Floor 5, gain 1 random Tier 3 E.G.O Gift(s) from the selected Keyword category\nWhen Fusing, gain a random additional E.G.O Gift 2 Tiers below the Fusion result(must be Tier 3 or higher) (once per Shop)",
        "buff++": "buff++:\nFuse or Sale only E.G.O Gift(s)\nFloor 5 or lower : \\yellow{Tier 2~3}\nFloor 6 or higher : \\yellow{Tier 3~4}\nUpon entering Floor 3/Floor 5/Floor 7, gain 1 random Tier \\yellow{4} E.G.O Gift(s) from the selected Keyword category\nWhen Fusing, gain a random additional E.G.O Gift \\yellow{1 Tier below} the Fusion result(must be Tier 3 or higher) (once per Shop)",
    },
    {
        "buff": "buff:\nTheme Pack Selection +1\nStarting E.G.O Gift Choice +1\nUpon entry, gain 1 Tier 3 E.G.O Gift(s) of your choice for the selected Keyword (if no remaining Gifts meet the conditions, a lower Tier one will appear instead)\nUpon entry, gain 1 Dark Vestige",
        "buff+": "buff+:\nTheme Pack Selection +1\nStarting E.G.O Gift Choice +1\nUpon entry, gain \\yellow{2} Tier 3 E.G.O Gift(s) of your choice for the selected Keyword (if no remaining Gifts meet the conditions, a lower Tier one will appear instead)\nUpon entry, gain 1 Dark Vestige and \\yellow{1 Dim Vestige}",
        "buff++": "buff++:\nTheme Pack Selection +1\nStarting E.G.O Gift Choice +1\nUpon entry, gain \\yellow{3} Tier 3 E.G.O Gift(s) of your choice for the selected Keyword (if no remaining Gifts meet the conditions, a lower Tier one will appear instead)\nUpon entry, gain 1 Dark Vestige, 1 Dim Vestige, and \\yellow{1 Shining Vestige}",
    },
]


def _is_starlight_english(language: str | None) -> bool:
    return str(language or "").lower().startswith("en")


def get_starlight_bonus_name(index: int, language: str | None = None) -> str:
    names = STARLIGHT_BONUS_NAMES_EN if _is_starlight_english(language) else STARLIGHT_BONUS_NAMES
    return names[index]


def get_starlight_action_label(text: str, language: str | None = None) -> str:
    if _is_starlight_english(language):
        return STARLIGHT_ACTION_LABELS_EN.get(text, text)
    return text


def get_starlight_bonus_tips(index: int, language: str | None = None) -> dict[str, str]:
    tips = STARLIGHT_BONUS_TIPS_EN if _is_starlight_english(language) else STARLIGHT_BONUS_TIPS
    return tips[index]



STARLIGHT_TOTAL_COST_STYLES = {
    "light": """
        QLabel#starlightTotalCostLabel {
            background: transparent;
            border: none;
            color: rgba(0, 0, 0, 0.82);
            font-size: 18px;
            font-weight: 600;
        }
    """,
    "dark": """
        QLabel#starlightTotalCostLabel {
            background: transparent;
            border: none;
            color: rgba(255, 255, 255, 0.92);
            font-size: 18px;
            font-weight: 600;
        }
    """,
}


def get_starlight_total_cost_qss() -> tuple[str, str]:
    return STARLIGHT_TOTAL_COST_STYLES["light"], STARLIGHT_TOTAL_COST_STYLES["dark"]


STARLIGHT_COST_LABEL_STYLES = {
    "light": """
        QLabel {
            background: transparent;
            border: none;
            color: rgba(0, 0, 0, 0.82);
            font-size: 11px;
            font-weight: 500;
        }
    """,
    "dark": """
        QLabel {
            background: transparent;
            border: none;
            color: rgba(255, 255, 255, 0.92);
            font-size: 11px;
            font-weight: 500;
        }
    """,
}

STARLIGHT_TOOLTIP_STYLES = {
    "light": """
        QFrame#starlightToolTipPopup {
            background-color: rgb(255, 255, 255);
            border: 1px solid rgba(0, 0, 0, 38);
            border-radius: 6px;
        }
        QLabel#starlightToolTipText {
            background: transparent;
            border: none;
            color: rgba(0, 0, 0, 0.82);
            padding: 0;
        }
    """,
    "dark": """
        QFrame#starlightToolTipPopup {
            background-color: rgb(45, 45, 45);
            border: 1px solid rgba(255, 255, 255, 46);
            border-radius: 6px;
        }
        QLabel#starlightToolTipText {
            background: transparent;
            border: none;
            color: rgba(255, 255, 255, 0.92);
            padding: 0;
        }
    """,
}

STARLIGHT_LEVEL_BUTTON_STYLES = {
    "light": """
        QPushButton {
            border: none;
            background: transparent;
            padding: 5px 6px;
            min-height: 32px;
            color: rgba(0, 0, 0, 0.82);
            font-size: 13px;
        }
        QPushButton:hover {
            background: transparent;
        }
        QPushButton:checked {
            color: rgba(0, 0, 0, 0.82);
        }
        QPushButton[segment="left"] {
            padding-right: 24px;
        }
    """,
    "dark": """
        QPushButton {
            border: none;
            background: transparent;
            padding: 5px 6px;
            min-height: 32px;
            color: rgba(255, 255, 255, 0.92);
            font-size: 13px;
        }
        QPushButton:hover {
            background: transparent;
        }
        QPushButton:checked {
            color: rgba(255, 255, 255, 0.92);
        }
        QPushButton[segment="left"] {
            padding-right: 24px;
        }
    """,
}

STARLIGHT_SELECTOR_STYLES = {
    "light": "StarlightLevelSelector { background: transparent; }",
    "dark": "StarlightLevelSelector { background: transparent; }",
}

STARLIGHT_PAINT_COLORS = {
    "light": {
        "empty": (120, 120, 120, 20),
        "left": (255, 143, 161, 150),
        "middle": (224, 76, 76, 175),
        "right": (190, 38, 52, 195),
    },
    "dark": {
        "empty": (255, 255, 255, 18),
        "left": (255, 182, 193, 70),
        "middle": (214, 96, 96, 88),
        "right": (170, 32, 44, 130),
    },
}


def get_starlight_cost_label_qss() -> tuple[str, str]:
    return STARLIGHT_COST_LABEL_STYLES["light"], STARLIGHT_COST_LABEL_STYLES["dark"]


def get_starlight_tooltip_qss() -> tuple[str, str]:
    return STARLIGHT_TOOLTIP_STYLES["light"], STARLIGHT_TOOLTIP_STYLES["dark"]


def get_starlight_level_button_qss() -> tuple[str, str]:
    return STARLIGHT_LEVEL_BUTTON_STYLES["light"], STARLIGHT_LEVEL_BUTTON_STYLES["dark"]


def get_starlight_selector_qss() -> tuple[str, str]:
    return STARLIGHT_SELECTOR_STYLES["light"], STARLIGHT_SELECTOR_STYLES["dark"]


def get_starlight_paint_colors(is_dark: bool) -> dict[str, QColor]:
    style = STARLIGHT_PAINT_COLORS["dark"] if is_dark else STARLIGHT_PAINT_COLORS["light"]
    default_line_color = QColor(120, 120, 120, 105)
    return {
        "border": default_line_color,
        "divider": default_line_color,
        "empty": QColor(*style["empty"]),
        "left": QColor(*style["left"]),
        "middle": QColor(*style["middle"]),
        "right": QColor(*style["right"]),
    }


# 公告板侧边栏样式配置
ANNOUNCEMENT_SIDEBAR_STYLES = {
    "dark": """
        QFrame#announcementSidebar {
            background-color: rgba(45, 45, 45, 1);
            border: none;
            border-top-left-radius: 8px;
            border-bottom-left-radius: 8px;
        }
        QLabel#sidebarTitle {
            color: rgba(255, 255, 255, 0.95);
            font-size: 16px;
            font-weight: bold;
            padding: 0px;
        }
    """,
    "light": """
        QFrame#announcementSidebar {
            background-color: rgba(245, 245, 245, 1);
            border: none;
            border-right: 1px solid rgba(0, 0, 0, 0.1);
            border-top-left-radius: 8px;
            border-bottom-left-radius: 8px;
        }
        QLabel#sidebarTitle {
            color: rgba(0, 0, 0, 0.9);
            font-size: 16px;
            font-weight: bold;
            padding: 0px;
        }
    """,
}


def get_announcement_sidebar_qss() -> tuple[str, str]:
    """返回 (light_qss, dark_qss) 用于公告板侧边栏"""
    return ANNOUNCEMENT_SIDEBAR_STYLES["light"], ANNOUNCEMENT_SIDEBAR_STYLES["dark"]


# 公告板列表项样式配置
ANNOUNCEMENT_LIST_STYLES = {
    "dark": """
        ListWidget {
            background-color: transparent;
            border: none;
            outline: 0px;
        }
        ListWidget::item {
            color: rgba(255, 255, 255, 0.85);
            background-color: transparent;
            border-left: 3px solid transparent;
            padding: 12px 15px;
            margin: 2px 5px;
            border-radius: 4px;
        }
        ListWidget::item:hover {
            background-color: rgba(255, 255, 255, 0.08);
        }
        ListWidget::item:selected {
            background-color: rgba(255, 255, 255, 0.12);
            border-left: 3px solid #0078d4;
        }
    """,
    "light": """
        ListWidget {
            background-color: transparent;
            border: none;
            outline: 0px;
        }
        ListWidget::item {
            color: rgba(0, 0, 0, 0.85);
            background-color: transparent;
            border-left: 3px solid transparent;
            padding: 12px 15px;
            margin: 2px 5px;
            border-radius: 4px;
        }
        ListWidget::item:hover {
            background-color: rgba(0, 0, 0, 0.05);
        }
        ListWidget::item:selected {
            background-color: rgba(0, 0, 0, 0.08);
            border-left: 3px solid #0078d4;
        }
    """,
}


def get_announcement_list_qss() -> tuple[str, str]:
    """返回 (light_qss, dark_qss) 用于公告板列表"""
    return ANNOUNCEMENT_LIST_STYLES["light"], ANNOUNCEMENT_LIST_STYLES["dark"]


ANNOUNCEMENT_CONTENT_STYLES = {
    "dark": """
        QTextBrowser {
            color: rgb(201, 209, 217);
            background-color: rgba(28, 28, 28, 1);
            border: none;
            padding: 20px;
            selection-background-color: rgba(88, 166, 255, 0.3);
            selection-color: rgb(255, 255, 255);
        }
    """,
    "light": """
        QTextBrowser {
            color: rgb(36, 41, 47);
            background-color: rgba(255, 255, 255, 1);
            border: none;
            padding: 20px;
            selection-background-color: rgba(0, 120, 212, 0.3);
            selection-color: rgb(0, 0, 0);
        }
    """,
}


def get_announcement_content_qss() -> tuple[str, str]:
    """返回 (light_qss, dark_qss) 用于公告板内容区域"""
    return ANNOUNCEMENT_CONTENT_STYLES["light"], ANNOUNCEMENT_CONTENT_STYLES["dark"]


# 公告板底部按钮区域样式
ANNOUNCEMENT_FOOTER_STYLES = {
    "dark": """
        QFrame#announcementFooter {
            background-color: rgba(45, 45, 45, 1);
            border-top: 1px solid rgba(255, 255, 255, 0.1);
            border-bottom-right-radius: 8px;
        }
    """,
    "light": """
        QFrame#announcementFooter {
            background-color: rgba(250, 250, 250, 1);
            border-top: 1px solid rgba(0, 0, 0, 0.1);
            border-bottom-right-radius: 8px;
        }
    """,
}


def get_announcement_footer_qss() -> tuple[str, str]:
    """返回 (light_qss, dark_qss) 用于公告板底部区域"""
    return ANNOUNCEMENT_FOOTER_STYLES["light"], ANNOUNCEMENT_FOOTER_STYLES["dark"]


# 设置界面样式配置
SETTING_INTERFACE_STYLES = {
    "dark": """
        SettingInterface, #scrollWidget, QWidget {
            background-color: rgb(28, 28, 28);
        }
        QScrollArea, QScrollArea > QWidget, QScrollArea > QWidget > QWidget {
            background-color: rgb(28, 28, 28);
            border: none;
        }
        /* 导航栏背景 (Navigation Bar Background) */
        #navFrame {
            background-color: rgb(28, 28, 28);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 8px;
        }
        /* 项目背景与字体颜色 (Item Background and Font Color - Normal State) */
        #navFrame QPushButton {
            text-align: left;
            padding: 8px 12px;
            border-radius: 6px;
            color: rgba(255, 255, 255, 0.7); /* 项目默认字体颜色 */
            margin: 0px;
            background-color: transparent; /* 项目默认背景透明 */
            border: none;
        }
        /* 项目背景与字体颜色 (Item Background and Font Color - Hover State) */
        #navFrame QPushButton:hover {
            background-color: rgba(255, 255, 255, 0.08); /* 悬停时的项目背景色 */
            color: rgba(255, 255, 255, 0.9); /* 悬停时的项目字体颜色 */
        }
        /* 项目背景与字体颜色 (Item Background and Font Color - Checked/Active State) */
        #navFrame QPushButton:checked {
            background-color: rgba(255, 255, 255, 0.12); /* 选中时的项目背景色 */
            color: rgb(255, 255, 255); /* 选中时的项目字体颜色 */
            font-weight: bold;
        }
    """,
    "light": """
        SettingInterface, #scrollWidget, QWidget {
            background-color: rgb(255, 255, 255);
        }
        QScrollArea, QScrollArea > QWidget, QScrollArea > QWidget > QWidget {
            background-color: rgb(255, 255, 255);
            border: none;
        }
        /* 导航栏背景 (Navigation Bar Background) */
        #navFrame {
            background-color: rgb(255, 255, 255);
            border: 1px solid rgba(0, 0, 0, 0.08);
            border-radius: 8px;
        }
        /* 项目背景与字体颜色 (Item Background and Font Color - Normal State) */
        #navFrame QPushButton {
            text-align: left;
            padding: 8px 12px;
            border-radius: 6px;
            color: rgba(0, 0, 0, 0.6); /* 项目默认字体颜色 */
            margin: 0px;
            background-color: transparent; /* 项目默认背景透明 */
            border: none;
        }
        /* 项目背景与字体颜色 (Item Background and Font Color - Hover State) */
        #navFrame QPushButton:hover {
            background-color: rgba(0, 0, 0, 0.06); /* 悬停时的项目背景色 */
            color: rgba(0, 0, 0, 0.85); /* 悬停时的项目字体颜色 */
        }
        /* 项目背景与字体颜色 (Item Background and Font Color - Checked/Active State) */
        #navFrame QPushButton:checked {
            background-color: rgba(0, 0, 0, 0.09); /* 选中时的项目背景色 */
            color: rgb(0, 0, 0); /* 选中时的项目字体颜色 */
            font-weight: bold;
        }
    """,
}


def get_setting_interface_qss() -> tuple[str, str]:
    """返回 (light_qss, dark_qss) 用于设置界面"""
    return SETTING_INTERFACE_STYLES["light"], SETTING_INTERFACE_STYLES["dark"]


def set_border_style(qframe: QFrame, is_dark: bool | None = None, border_radius: int = 5):
    """为 QFrame 及子类设置边框样式"""
    if is_dark is None:
        is_dark = isDarkTheme()
    style = BORDER_STYLE["dark"] if is_dark else BORDER_STYLE["light"]
    style = style.format(radius=border_radius)
    qss = f"{qframe.__class__.__name__} {{{style}}}"
    qframe.setStyleSheet(qss)
