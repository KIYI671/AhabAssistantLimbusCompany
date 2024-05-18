from command.get_position import get_pic_position_without_cap,  get_pic_position

scenes = {"retry": 0,  # 网络波动，随时遇见

          # 战斗前中后
          "choose_sinners_to_fight": 1, "in_battle": 2, "selecting_ego": 3, "battle_victory": 4, "battle_defeat": 5,

          # 各个镜牢页面
          "init_mirror": 10, "mirror_select_init_ego": 11, "mirror_road": 12, "selecting_a_fight_room": 13,
          "selecting_an_other_room": 14,
          "select_reward_card": 15, "in_shop": 16, "mirror_setting": 17, "settlement_page": 18, "settlement_reward": 19,

          # 主界面六个功能
          "main_window": 30, "sinnners": 31, "drive": 32, "theater": 33, "extract": 34, "dispense": 35,

          # 可以靠点击空白位置或esc键退出
          "notif": 36, "mailbox": 37, "settings": 38, "charge_enkephalin": 39,

          # 剧情对话界面
          "plot_dialogue": 40,

          # 这几个左上角有退后键
          "inventory": 41, "shop": 42, "refund_policy": 43, "display_page": 44, "refraction_railway": 45,
          "luxcavation": 46,

          # 升级页面
          "leave_up": 50,

          # 登录界面
          "log_in": 51,

          # 加载中
          "waiting": 52,

          # 其他未知情况
          "unknown": -1
          }


def where_am_i():
    # 优先处理可能出现的网络问题
    if get_pic_position("./pic/scenes/network/retry_countdown.png") \
            or get_pic_position_without_cap("./pic/scenes/network/retry.png") \
            or get_pic_position_without_cap("./pic/scenes/network/try_again.png"):
        return 0

    # 接下来识别是否在战斗中
    if get_pic_position_without_cap("./pic/teams/formation_features.png"):
        return 1
    elif get_pic_position_without_cap("./pic/battle/in_battle.png"):
        return 2
    elif get_pic_position_without_cap("./pic/battle/use_ego_features.png") or \
            get_pic_position_without_cap("./pic/battle/use_ego_features_2.png") or \
            get_pic_position_without_cap("./pic/battle/ego_resistances.png"):
        return 3
    elif get_pic_position_without_cap("./pic/battle/victory.png"):
        return 4
    elif get_pic_position_without_cap("./pic/battle/defeat.png"):
        return 5

    # 判断是否在镜牢的情况
    if get_pic_position_without_cap("./pic/scenes/init_mirror.png"):
        return 10
    elif get_pic_position_without_cap("./pic/scenes/mirror_select_ego.png"):
        return 11
    elif get_pic_position_without_cap("./pic/scenes/road_in_mirror.png"):
        return 12
    elif get_pic_position_without_cap("./pic/mirror/battle_clear_rewards.png"):
        return 13
    elif get_pic_position_without_cap("./pic/mirror/select_an_other_room.png"):
        return 14
    elif get_pic_position_without_cap("./pic/mirror/select_encounter_reward_card.png"):
        return 15
    elif get_pic_position_without_cap("./pic/mirror/event/shop/shop_features_1.png") and \
            get_pic_position_without_cap("./pic/mirror/event/shop/shop_features_2.png"):
        return 16
    elif get_pic_position_without_cap("./pic/mirror/mirror_setting_forfeit.png") and \
            get_pic_position_without_cap("./pic/mirror/mirror_setting_continue.png") and \
            get_pic_position_without_cap("./pic/mirror/mirror_setting_to_window.png"):
        return 17
    elif get_pic_position_without_cap("./pic/mirror/total_progress.png"):
        return 18
    elif get_pic_position_without_cap("./pic/mirror/exploration_reward.png"):
        return 19

    # 如果在主界面的几个窗口，或其他乱七八糟的位置
    if get_pic_position_without_cap("./pic/scenes/init_window.png") \
            or get_pic_position_without_cap("./pic/scenes/select_window.png"):
        # 代号38,39会因为窗体过小无法遮挡其他识别点，导致无限循环，所以优先度提高
        if get_pic_position_without_cap("./pic/scenes/settings.png"):
            return 38
        elif get_pic_position_without_cap("./pic/scenes/charge_enkephalin.png"):
            return 39
        elif get_pic_position_without_cap("./pic/scenes/select_window.png") and \
                get_pic_position_without_cap("./pic/scenes/mail.png") and \
                get_pic_position_without_cap("./pic/prize/now_season.png"):
            return 30
        elif get_pic_position_without_cap("./pic/scenes/sinners_features.png"):
            return 31
        elif get_pic_position_without_cap("./pic/scenes/drive_features.png"):
            return 32
        elif get_pic_position_without_cap("./pic/scenes/therter_features.png"):
            return 33
        elif get_pic_position_without_cap("./pic/scenes/extract_features.png"):
            return 34
        elif get_pic_position_without_cap("./pic/scenes/dispense_features.png"):
            return 35

    elif get_pic_position_without_cap("./pic/scenes/notifs.png"):
        return 36
    elif get_pic_position_without_cap("./pic/scenes/mailbox.png"):
        return 37
    elif get_pic_position_without_cap("./pic/scenes/plot/plot_dialogue.png"):
        return 40
    elif get_pic_position_without_cap("./pic/scenes/inventory.png"):
        return 41
    elif get_pic_position_without_cap("./pic/scenes/shop.png"):
        return 42
    elif get_pic_position_without_cap("./pic/scenes/refund_policy.png"):
        return 43
    elif get_pic_position_without_cap("./pic/scenes/display_page_features.png"):
        return 44
    elif get_pic_position_without_cap("./pic/scenes/refraction_railway.png"):
        return 45
    elif get_pic_position_without_cap("./pic/scenes/luxcavation.png"):
        return 46
    elif get_pic_position_without_cap("./pic/battle/level_up_message.png") or \
            get_pic_position_without_cap("./pic/battle/level_up_message2.png"):
        return 50
    elif get_pic_position_without_cap("./pic/scenes/login_in.png"):
        return 51
    elif get_pic_position_without_cap("./pic/wait.png") or \
            get_pic_position_without_cap("./pic/wait_2.png"):
        return 52
    return -1
