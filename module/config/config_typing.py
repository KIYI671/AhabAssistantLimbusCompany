from typing import List, Optional

from pydantic import BaseModel


class TeamSetting(BaseModel):
    """单个队伍设置"""

    team_system: int = 0
    """队伍使用的体系"""

    team_number: int = 1
    """使用的队伍序号"""

    shop_strategy: int = 0
    """商店策略"""

    sinners_be_select: int = 0
    """有几名罪人被选中"""

    chosen_sinners: List[int] = [0] * 12
    """有哪几名罪人被选中"""

    sinner_order: List[int] = [0] * 12
    """罪人被选中的顺序"""

    system_burn: bool = False
    """弃置燃烧饰品"""

    system_bleed: bool = False
    """弃置流血饰品"""

    system_tremor: bool = False
    """弃置震颤饰品"""

    system_rupture: bool = False
    """弃置破裂饰品"""

    system_poise: bool = False
    """弃置呼吸饰品"""

    system_sinking: bool = False
    """弃置沉沦饰品"""

    system_charge: bool = False
    """弃置充能饰品"""

    system_slash: bool = False
    """弃置斩击饰品"""

    system_pierce: bool = False
    """弃置穿刺饰品"""

    system_blunt: bool = False
    """弃置打击饰品"""

    do_not_heal: bool = False
    """不治疗"""

    do_not_buy: bool = False
    """不购买"""

    do_not_fuse: bool = False
    """不合成"""

    do_not_sell: bool = False
    """不出售"""

    do_not_enhance: bool = False
    """不升级"""

    only_aggressive_fuse: bool = False
    """合成只采取激进策略"""

    do_not_system_fuse: bool = False
    """不合成体系饰品"""

    only_system_fuse: bool = False
    """只合成体系饰品"""

    avoid_skill_3: bool = False
    """避免使用3技能"""

    re_formation_each_floor: bool = False
    """每个楼层重新编队"""

    use_starlight: bool = False
    """开局星光换钱"""

    aggressive_also_enhance: bool = False
    """激进合成期间也升级饰品"""

    aggressive_save_systems: bool = False
    """激进合成保留体系饰品"""

    defense_first_round: bool = False
    """第一回合全员防御"""

    fixed_team_use: bool = False
    """固定队伍用途"""

    fixed_team_use_select: int = 0
    """固定队伍用途的选择项"""

    reward_cards: bool = False
    """奖励卡优先度"""

    reward_cards_select: int = 0
    """自定义奖励卡优先度"""

    choose_opening_bonus: bool = False
    """自选开局加成"""

    opening_bonus_select: int = 0
    """开局加成已选数量"""

    opening_bonus: List[int] = [0] * 10
    """启用的开局加成"""

    opening_bonus_order: List[int] = [0] * 10
    """启用的开局加成顺序"""

    opening_bonus_level: List[int] = [0] * 10
    """启用的开局加成等级"""

    after_level_IV: bool = False
    """自定义合成四级后的操作"""

    after_level_IV_select: int = 0
    """合成四级后的操作"""

    shopping_strategy: bool = False
    """自定义购物策略"""

    shopping_strategy_select: int = 0
    """购物策略"""

    opening_items: bool = False
    """自定义开局道具"""

    opening_items_select: int = 0
    """开局道具选择顺序"""

    opening_items_system: int = 0
    """开局道具体系"""

    second_system: bool = False
    """启用第二体系"""

    second_system_select: int = 0
    """第二体系"""

    second_system_setting: int = 0
    """第二体系启用时间"""

    second_system_action: List[int] = [0] * 4
    """第二体系行动模式"""

    skill_replacement: bool = False
    """自定义技能替换"""

    skill_replacement_select: int = 0
    """技能替换设置"""

    skill_replacement_mode: int = 0
    """技能替换模式"""

    ignore_shop: List[int] = [0] * 5
    """忽略商店楼层"""

    remark_name: Optional[str] = None
    """队伍备注名"""

    use_custom_theme_pack_weight: bool = False
    """启用队伍自定义主题包权重"""

    total_mirror_time_hard: List[float] = [0.0, 0.0, 0.0]
    """困难镜牢总用时"""

    mirror_hard_count: int = 0
    """困难镜牢次数"""

    total_mirror_time_normal: List[float] = [0.0, 0.0, 0.0]
    """普通镜牢总用时"""

    mirror_normal_count: int = 0
    """普通镜牢次数"""


class ConfigModel(BaseModel):
    """配置模型"""

    config_version: int = 1775826004
    """配置文件版本号（时间戳）"""

    save_count: int = 0
    """保存次数"""

    game_title_name: str = "LimbusCompany"
    """游戏窗口标题"""

    game_process_name: str = "LimbusCompany.exe"
    """游戏进程名"""

    game_path: str = r"C:\Program Files (x86\Steam\steamapps\common\Limbus Company\LimbusCompany.exe"
    """游戏启动路径"""

    language_in_game: str = "en"
    """游戏语言"""

    after_completion_actions: List[str] = []
    """脚本结束后的前置动作（可多选）：exit_game/exit_emulator/exit_aalc"""

    after_completion_power_action: str = "none"
    """脚本结束后的最终动作（单选）：none/sleep/hibernate/lock/shutdown"""

    keep_after_completion: bool = False
    """是否保持脚本结束后的操作"""

    language_in_program: str = ""
    """程序语言"""

    shutdown_hotkey: str = "<ctrl>+q"
    """关闭快捷键"""

    pause_hotkey: str = "<alt>+p"
    """暂停快捷键"""

    resume_hotkey: str = "<alt>+r"
    """继续快捷键"""

    announcement: float = 1715990400
    """公告板时间戳"""

    memory_protection: bool = False
    """内存占用保护"""

    background_click: bool = True
    """是否使用后台点击"""

    win_input_type: str = "background"
    """键鼠操控方式"""

    auto_hard_mirror: bool = False
    """周四自动切换困难镜牢"""

    last_auto_change: float = 1715990400
    """上次自动切换困难镜牢的时间戳"""

    hard_mirror_chance: int = 0
    """困难镜牢剩余次数"""

    timezone: Optional[float] = None
    """当前时区相对于东九区的偏移量"""

    zoom_scale: int = 0
    """缩放比例"""

    window_position_x: int = 0
    """窗口位置x"""

    window_position_y: int = 0
    """窗口位置y"""

    theme_mode: str = "AUTO"
    """应用主题：AUTO, LIGHT, DARK"""

    autostart: bool = False
    """自启动"""

    autodaily: bool = False
    """启用定时执行"""

    autodaily_task: List[bool] = [False] * 4
    """定时任务列表"""

    autodaily_task_exit: List[bool] = [False] * 5
    """定时任务退出列表"""

    autodaily_time: str = "00:00"
    """定时执行时间（HH:mm）"""

    autodaily2: bool = False
    """启用定时执行2"""

    autodaily2_task: List[bool] = [False] * 4
    """定时任务2列表"""

    autodaily2_task_exit: List[bool] = [False] * 5
    """定时任务2退出列表"""

    autodaily_time2: str = "00:00"
    """定时执行时间2（HH:mm）"""

    autodaily3: bool = False
    """启用定时执行3"""

    autodaily3_task: List[bool] = [False] * 4
    """定时任务3列表"""

    autodaily3_task_exit: List[bool] = [False] * 5
    """定时任务3退出列表"""

    autodaily_time3: str = "00:00"
    """定时执行时间3（HH:mm）"""

    autodaily4: bool = False
    """启用定时执行4"""

    autodaily4_task: List[bool] = [False] * 4
    """定时任务4列表"""

    autodaily4_task_exit: List[bool] = [False] * 5
    """定时任务4退出列表"""

    autodaily_time4: str = "00:00"
    """定时执行时间4（HH:mm）"""

    minimize_to_tray: bool = False
    """最小化到托盘"""

    screenshot_interval: float = 0.85
    """截图间隔时间"""

    mouse_action_interval: float = 0.5
    """鼠标操作间隔时间"""

    resonate_with_Ahab: bool = False
    """是否播放亚哈语录"""

    experimental_auto_lang: bool = True
    """是否自动修改语言"""

    simulator: bool = False
    """是否使用模拟器"""

    simulator_type: int = 0
    """0:mumu, 10:其他"""

    simulator_port: int = 0
    """端口"""

    mumu_instance_number: int = -1
    """mumu模拟器的实例编号"""

    start_emulator_timeout: int = 120
    """启动模拟器超时时间"""

    check_update: bool = True
    """检查更新"""

    update_prerelease_enable: bool = False
    """启用预发布版更新"""

    update_source: str = "GitHub"
    """更新源"""

    mirrorchyan_cdk: str = ""
    """Mirror酱 CDK"""

    default_page: int = 0
    """保存启动后的页面"""

    set_windows: bool = True
    """是否进行自动窗口设置"""

    set_win_size: int = 1080
    """设置使用的分辨率"""

    set_win_position: str = "free"
    """是否自动设置窗口的位置"""

    set_reduce_miscontact: bool = True
    """是否防止误触"""

    select_team_by_order: bool = False
    """是否按顺序（而非名称）选择队伍"""

    daily_task: bool = False
    """是否进行日常本"""

    set_EXP_count: int = 1
    """设置经验本的次数"""

    set_thread_count: int = 3
    """设置纽本的次数"""

    daily_teams: int = 1
    """设置日常本使用的队伍"""

    targeted_teaming_EXP: bool = False
    """经验本指定队伍"""

    EXP_day_1_2: int = 1
    """周一/二经验本队伍"""

    EXP_day_3_4: int = 1
    """周三/四经验本队伍"""

    EXP_day_5_6: int = 1
    """周五/六经验本队伍"""

    EXP_day_7: int = 1
    """周日经验本队伍"""

    targeted_teaming_thread: bool = False
    """纽本指定队伍"""

    use_coutinuous_combat: bool = False
    """是否使用连续作战"""

    thread_day_1: int = 1
    """周一纽本队伍"""

    thread_day_2: int = 1
    """周二纽本队伍"""

    thread_day_3: int = 1
    """周三纽本队伍"""

    thread_day_4: int = 1
    """周四纽本队伍"""

    thread_day_5: int = 1
    """周五纽本队伍"""

    thread_day_6: int = 1
    """周六纽本队伍"""

    thread_day_7: int = 1
    """周日纽本队伍"""

    get_reward: bool = False
    """是否进行获取奖励"""

    set_get_prize: int = 0
    """奖励领取模式"""

    buy_enkephalin: bool = False
    """是否自动购买体力"""

    set_lunacy_to_enkephalin: int = 2
    """购买体力次数"""

    Dr_Grandet_mode: bool = False
    """葛朗台模式"""

    skip_enkephalin: bool = False
    """跳过换体"""

    mirror: bool = False
    """是否进行自动镜牢"""

    set_mirror_count: int = 1
    """镜牢的次数"""

    hard_mirror: int | bool = 0
    """进行困难镜牢"""

    no_weekly_bonuses: int | bool = 0
    """不使用每周加成"""

    floor_3_exit: bool = False
    """只打三层"""

    infinite_dungeons: bool = False
    """无限刷牢"""

    save_rewards: bool = False
    """保存奖励不领"""

    hard_mirror_single_bonuses: bool = False
    """困难镜牢使用单次加成"""

    select_event_pack: bool = False
    """第五层选择活动卡包"""

    skip_event_pack: bool = False
    """第五层跳过活动卡包"""

    re_claim_rewards: bool = False
    """再次执行领取奖励任务"""

    not_skip_whitegossypium: bool = False
    """不跳过白棉花"""

    fight_to_last_man: bool = False
    """战斗直到全灭"""

    teams_be_select_num: int = 0
    """被选中的队伍数量"""

    teams_be_select: List[bool] = [False]
    """被选中的队伍"""

    teams_order: List[int] = [0]
    """队伍的顺序"""

    mirror_keyboard_navigation: bool = False
    """使用键盘进行镜牢寻路"""

    teams: dict[str, TeamSetting] = {"1": TeamSetting()}
    """队伍设置"""
