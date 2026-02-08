from enum import Enum

from PySide6.QtCore import QT_TRANSLATE_NOOP

from app.mediator import Mediator
from module.config import cfg

mediator = Mediator()

toggle_button_group = {}

team_toggle_button_group = []

task_check_box = []

page_name_and_index = {
    "set_windows": 0,
    "daily_task": 1,
    "get_reward": 2,
    "buy_enkephalin": 3,
    "mirror": 4,
}

set_win_size_options = {
    "1920*1080": 1080,
    "2560*1440": 1440,
    "1280*720": 720,
    "1600*900": 900,
    "3200*1800": 1800,
    "3840*2160": 2160,
}
set_win_position_options = {
    QT_TRANSLATE_NOOP("BaseComboBox", "无限制"): "free",
    QT_TRANSLATE_NOOP("BaseComboBox", "左上角"): "left_top",
    QT_TRANSLATE_NOOP("BaseComboBox", "左下角"): "left_bottom",
    QT_TRANSLATE_NOOP("BaseComboBox", "右上角"): "right_top",
    QT_TRANSLATE_NOOP("BaseComboBox", "右下角"): "right_bottom",
    QT_TRANSLATE_NOOP("BaseComboBox", "居中"): "center",
}
set_reduce_miscontact_options = {QT_TRANSLATE_NOOP("BaseComboBox", "是"): True}
set_lunacy_to_enkephalin_options = {
    QT_TRANSLATE_NOOP("BaseComboBox", "不换"): 0,
    QT_TRANSLATE_NOOP("BaseComboBox", "换第一次"): 1,
    QT_TRANSLATE_NOOP("BaseComboBox", "换第二次"): 2,
    QT_TRANSLATE_NOOP("BaseComboBox", "换第三次"): 3,
}
set_get_prize_options = {
    QT_TRANSLATE_NOOP("BaseComboBox", "邮件+日/周常"): 0,
    QT_TRANSLATE_NOOP("BaseComboBox", "日/周常"): 1,
    QT_TRANSLATE_NOOP("BaseComboBox", "邮件"): 2,
}
set_after_completion_options = {
    QT_TRANSLATE_NOOP("BaseComboBox", "无"): 0,
    QT_TRANSLATE_NOOP("BaseComboBox", "睡眠"): 1,
    QT_TRANSLATE_NOOP("BaseComboBox", "休眠"): 2,
    QT_TRANSLATE_NOOP("BaseComboBox", "关机"): 3,
    QT_TRANSLATE_NOOP("BaseComboBox", "退出游戏"): 4,
    QT_TRANSLATE_NOOP("BaseComboBox", "退出AALC"): 5,
    QT_TRANSLATE_NOOP("BaseComboBox", "退出AALC和游戏"): 6,
}
all_teams = {f"Team{i}": i for i in range(1, 21)}
all_systems = {
    QT_TRANSLATE_NOOP("BaseComboBox", "烧伤"): 0,
    QT_TRANSLATE_NOOP("BaseComboBox", "流血"): 1,
    QT_TRANSLATE_NOOP("BaseComboBox", "震颤"): 2,
    QT_TRANSLATE_NOOP("BaseComboBox", "破裂"): 3,
    QT_TRANSLATE_NOOP("BaseComboBox", "呼吸"): 4,
    QT_TRANSLATE_NOOP("BaseComboBox", "沉沦"): 5,
    QT_TRANSLATE_NOOP("BaseComboBox", "充能"): 6,
    QT_TRANSLATE_NOOP("BaseComboBox", "斩击"): 7,
    QT_TRANSLATE_NOOP("BaseComboBox", "突刺"): 8,
    QT_TRANSLATE_NOOP("BaseComboBox", "打击"): 9,
}
shop_strategy = {
    QT_TRANSLATE_NOOP("BaseComboBox", "出售"): 0,
    QT_TRANSLATE_NOOP("BaseComboBox", "合成"): 1,
    QT_TRANSLATE_NOOP("BaseComboBox", "合成：四级优先"): 2,
}
after_fuse_level_IV = {
    QT_TRANSLATE_NOOP("BaseComboBox", "商店策略改为出售"): 0,
    QT_TRANSLATE_NOOP("BaseComboBox", "商店策略改为普通合成"): 1,
    QT_TRANSLATE_NOOP("BaseComboBox", "合成第二体系四级饰品"): 2,
    QT_TRANSLATE_NOOP("BaseComboBox", "跳过商店"): 3,
}
reward_cards = {
    QT_TRANSLATE_NOOP("BaseComboBox", "星光→饰品→钱→饰品/钱→罪孽"): 0,
    QT_TRANSLATE_NOOP("BaseComboBox", "星光→钱→饰品→饰品/钱→罪孽"): 1,
    QT_TRANSLATE_NOOP("BaseComboBox", "钱→饰品→饰品/钱→罪孽→星光"): 2,
    QT_TRANSLATE_NOOP("BaseComboBox", "饰品→钱→饰品/钱→罪孽→星光"): 3,
}
fixed_team_use = {
    QT_TRANSLATE_NOOP("BaseComboBox", "困难镜牢"): 0,
    QT_TRANSLATE_NOOP("BaseComboBox", "普通镜牢"): 1,
}
shopping_strategy = {
    QT_TRANSLATE_NOOP("BaseComboBox", "仅购买回血饰品"): 0,
    QT_TRANSLATE_NOOP("BaseComboBox", "启用四级优先时：仅购买所有3-4级饰品"): 1,
    QT_TRANSLATE_NOOP("BaseComboBox", "仅购买体系饰品"): 2,
    QT_TRANSLATE_NOOP("BaseComboBox", "不购买体系饰品"): 3,
    QT_TRANSLATE_NOOP("BaseComboBox", "不购买回血饰品"): 4,
    QT_TRANSLATE_NOOP("BaseComboBox", "启用四级优先时：不购买所有3-4级饰品"): 5,
}
start_gift = {"1→2→3": 0, "1→3→2": 1, "2→1→3": 2, "2→3→1": 3, "3→1→2": 4, "3→2→1": 5}
second_systems = {
    QT_TRANSLATE_NOOP("BaseComboBox", "合成第一体系四级饰品后"): 0,
    QT_TRANSLATE_NOOP("BaseComboBox", "一直"): 1,
}
skill_replacement_sinner = {
    QT_TRANSLATE_NOOP("BaseComboBox", "配队首位"): 0,
    QT_TRANSLATE_NOOP("BaseComboBox", "配队前3"): 1,
    QT_TRANSLATE_NOOP("BaseComboBox", "配队前7"): 2,
    QT_TRANSLATE_NOOP("BaseComboBox", "所有人"): 3,
}
skill_replacement_mode = {"1→3": 0, "2→3": 1, "1→2": 2}

blank_team_setting = {}

team_setting_template = cfg._load_default_config().get("team1_setting", {})

all_sinners_name = [
    "YiSang",
    "Faust",
    "DonQuixote",
    "Ryoshu",
    "Meursault",
    "HongLu",
    "Heathcliff",
    "Ishmael",
    "Rodion",
    "Sinclair",
    "Outis",
    "Gregor",
]

all_systems_name = {
    0: "burn",
    1: "bleed",
    2: "tremor",
    3: "rupture",
    4: "poise",
    5: "sinking",
    6: "charge",
    7: "slash",
    8: "pierce",
    9: "blunt",
}

second_system_mode = [
    "second_system_fuse_IV",
    "second_system_buy",
    "second_system_choose",
    "second_system_power_up",
]

all_combobox_config_name = [
    "team_number",
    "team_system",
    "shop_strategy",
    "fixed_team_use_select",
    "reward_cards_select",
    "after_level_IV_select",
    "shopping_strategy_select",
    "opening_items_select",
    "opening_items_system",
    "second_system_select",
    "second_system_setting",
    "skill_replacement_select",
    "skill_replacement_mode",
]

all_checkbox_config_name = [
    "system_burn",
    "system_bleed",
    "system_tremor",
    "system_rupture",
    "system_poise",
    "system_sinking",
    "system_charge",
    "system_slash",
    "system_pierce",
    "system_blunt",
    "do_not_heal",
    "do_not_buy",
    "do_not_fuse",
    "do_not_sell",
    "do_not_enhance",
    "only_aggressive_fuse",
    "do_not_system_fuse",
    "only_system_fuse",
    "avoid_skill_3",
    "re_formation_each_floor",
    "use_starlight",
    "aggressive_also_enhance",
    "aggressive_save_systems",
    "defense_first_round",
    "fixed_team_use",
    "reward_cards",
    "choose_opening_bonus",
    "after_level_IV",
    "shopping_strategy",
    "opening_items",
    "second_system",
    "skill_replacement",
    "ignore_shop",
]


class AnnouncementStatus(Enum):
    """
    定义更新状态的枚举类

    该枚举类用于表示更新操作的三种可能结果状态：
    - SUCCESS 表示更新操作成功
    - UPDATE_AVAILABLE 表示有可用的更新
    - FAILURE 表示更新操作失败
    """

    SUCCESS = 1
    ANNO_AVAILABLE = 2
    FAILURE = 0
