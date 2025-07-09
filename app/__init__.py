from app.mediator import Mediator

mediator = Mediator()

toggle_button_group = {}

team_toggle_button_group = []

task_check_box = []

page_name_and_index = {
    'set_windows': 0,
    'daily_task': 1,
    'get_reward': 2,
    'buy_enkephalin': 3,
    'mirror': 4
}

set_win_size_options = {"1920*1080": 1080, "2560*1440": 1440, "1280*720": 720, "1600*900": 900,
                        "3200*1800": 1800,
                        "3840*2160": 2160}
set_win_position_options = {'左上角（0，0）': True}
set_reduce_miscontact_options = {'是': True}
set_language_options = {'English': 'en', '简体中文': 'zh_cn'}
set_lunacy_to_enkephalin_options = {"不换": 0, "换第一次": 1, "换第二次": 2}
set_get_prize_options = {"邮件+日/周常": 0, "日/周常": 1, "邮件": 2}
set_after_completion_options = {"无 / None": 0, "睡眠 / Sleep": 1, "休眠 / Hibernate": 2,
                                "关机 / Shutdown": 3, "退出游戏 / Exit Game": 4, "退出AALC / Exit AALC": 5,
                                "退出AALC和游戏 / Exit AALC And Game": 6}
all_teams = {f"Team{i}": i for i in range(1, 21)}
all_systems = {"烧伤(burn)": 0, "流血(bleed)": 1, "震颤(tremor)": 2, "破裂(rupture)": 3, "呼吸(poise)": 4,
               "沉沦(sinking)": 5, "充能(charge)": 6, "斩击(slash)": 7, "突刺(pierce)": 8, "打击(blunt)": 9}
shop_strategy = {"出售": 0, "合成": 1, "合成：四级优先": 2}
after_fuse_level_IV = {"商店策略改为出售": 0, "商店策略改为普通合成": 1, "合成第二体系四级饰品": 2, "跳过商店": 3}
reward_cards = {"星光→饰品→钱→饰品/钱→罪孽": 0, "星光→钱→饰品→饰品/钱→罪孽": 1, "钱→饰品→饰品/钱→罪孽→星光": 2,
                "饰品→钱→饰品/钱→罪孽→星光": 3}
shopping_strategy = {"仅购买回血饰品": 0, "仅购买3-5级饰品": 1, "仅购买体系饰品": 2, "不购买体系饰品": 3,
                     "不购买回血饰品": 4, "不购买3-5级饰品": 5}
start_gift = {"1→2→3": 0, "1→3→2": 1, "2→1→3": 2, "2→3→1": 3, "3→1→2": 4, "3→2→1": 5}
second_systems = {"合成第一体系四级饰品后": 0, "一直": 1}
skill_replacement_sinner = {"配队首位": 0, "配队前3": 1, "配队前7": 2, "所有人": 3}
skill_replacement_mode = {"1→3": 0, "1→2": 1, "2→3": 2}

blank_team_setting={}

team_setting_template = {
    "team_system": 0,  # 队伍使用的体系
    "team_number": 1,  # 使用的队伍序号
    "shop_strategy": 0,  # 商店策略
    "sinners_be_select": 0,  # 有几名罪人被选中
    "chosen_sinners": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],  # 有哪几名罪人被选中
    "sinner_order": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],  # 罪人被选中的顺序
    "system_burn": False,  # 弃置燃烧饰品
    "system_bleed": False,  # 弃置流血饰品
    "system_tremor": False,  # 弃置震颤饰品
    "system_rupture": False,  # 弃置破裂饰品
    "system_poise": False,  # 弃置呼吸饰品
    "system_sinking": False,  # 弃置沉沦饰品
    "system_charge": False,  # 弃置充能饰品
    "system_slash": False,  # 弃置斩击饰品
    "system_pierce": False,  # 弃置穿刺饰品
    "system_blunt": False,  # 弃置打击饰品
    "customize": False,  # 启用自定义
    "do_not_heal": False,  # 不治疗
    "do_not_buy": False,  # 不购买
    "do_not_fuse": False,  # 不合成
    "only_aggressive_fuse": False,  # 合成只采取激进策略
    "do_not_system_fuse": False,  # 不合成体系饰品
    "only_system_fuse": False,  # 只合成体系饰品
    "avoid_skill_3": False,  # 避免使用3技能
    "re_formation_each_floor": False,  # 每个楼层重新编队
    "keep_starlight": False,  # 保留开局星光
    "reward_cards": False,  # 奖励卡优先度
    "reward_cards_select": 0, # 自定义奖励卡优先度
    "choose_opening_bonus": False,  # 自选开局加成
    "opening_bonus_select": 0, # 开局加成已选数量
    "opening_bonus": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],  # 启用的开局加成
    "opening_bonus_order": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],  # 启用的开局加成顺序
    "after_level_IV": False,  # 自定义合成四级后的操作
    "after_level_IV_select": 0,  # 合成四级后的操作
    "shopping_strategy": False,  # 自定义商店策略
    "shopping_strategy_select": 0,  # 商店策略
    "opening_items": False,  # 自定义开局道具
    "opening_items_select": 0,  # 开局道具体系
    "opening_items_system": 0,  # 开局道具选择顺序
    "second_system": False,  # 自定义第二体系
    "second_system_select": 0,  # 第二体系启用时间
    "second_system_setting": [0, 0, 0, 0, 0, 0],  # 第二体系设置
    "skill_replacement": False,  # 自定义技能替换
    "skill_replacement_select": 0,  # 技能替换设置
    "skill_replacement_mode": 0,  # 技能替换模式
    "ignore_shop": [0, 0, 0, 0, 0],  # 忽略商店楼层
}


all_sinners_name = ["YiSang", "Faust", "DonQuixote", "Ryoshu", "Meursault", "HongLu",
                    "Heathcliff", "Ishmael", "Rodion", "Sinclair", "Outis", "Gregor"]

second_system_mode = ["second_system_fuse",
                      "second_system_fuse_IV",
                      "second_system_fuse_system",
                      "second_system_buy",
                      "second_system_choose",
                      "second_system_power_up"]

all_combobox_config_name = [
    "team_number",
    "team_system",
    "shop_strategy",
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
    "customize",
    "do_not_heal",
    "do_not_buy",
    "do_not_fuse",
    "only_aggressive_fuse",
    "do_not_system_fuse",
    "only_system_fuse",
    "avoid_skill_3",
    "re_formation_each_floor",
    "keep_starlight",
    "reward_cards",
    "choose_opening_bonus",
    "after_level_IV",
    "shopping_strategy",
    "opening_items",
    "second_system",
    "skill_replacement",
    "ignore_shop"
]

