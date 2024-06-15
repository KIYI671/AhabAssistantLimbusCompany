import os
from time import sleep

from command.get_position import get_pic_position, get_pic_position_without_cap, get_all_pic_position
from command.mouse_activity import mouse_click, mouse_scroll_farthest, mouse_drag_down
from my_decorator.decorator import begin_and_finish_log
from my_log.my_log import my_log
from my_ocr.ocr import get_theme_pack, compare_the_blacklist, commom_ocr, commom_gain_text, commom_all_ocr
from script.all_retry_question import retry
from script.back_init_menu import back_init_menu
from script.decision_event_handling import decision_event_handling
from script.in_battle import battle
from script.team_formation import team_formation, select_battle_team

scale_factors = [0.75, 1.0, 0.5, 0.625, 1.25, 1.5]
# 存放位置
systems = {"burn": "./pic/mirror/event/rest_room/burn.png",
           "sinking": "./pic/mirror/event/rest_room/sinking.png",
           "charge": "./pic/mirror/event/rest_room/charge.png",
           "bleed": "./pic/mirror/event/rest_room/bleed.png",
           "tremor": "./pic/mirror/event/rest_room/tremor.png",
           "rupture": "./pic/mirror/event/rest_room/rupture.png",
           "poise": "./pic/mirror/event/rest_room/poise.png",
           "clash": "./pic/mirror/event/rest_room/clash.png",
           "slash": "./pic/mirror/event/rest_room/slash.png",
           "blunt": "./pic/mirror/event/rest_room/blunt.png"}
systems_big_pic = {"burn": "./pic/mirror/event/rest_room/big_burn.png",
                   "sinking": "./pic/mirror/event/rest_room/big_sinking.png",
                   "charge": "./pic/mirror/event/rest_room/big_charge.png",
                   "bleed": "./pic/mirror/event/rest_room/big_bleed.png",
                   "tremor": "./pic/mirror/event/rest_room/big_tremor.png",
                   "rupture": "./pic/mirror/event/rest_room/big_rupture.png",
                   "poise": "./pic/mirror/event/rest_room/big_poise.png",
                   "clash": "./pic/mirror/event/rest_room/big_clash.png",
                   "slash": "./pic/mirror/event/rest_room/big_slash.png",
                   "blunt": "./pic/mirror/event/rest_room/big_blunt.png"}
systems_shop = {"burn": "./pic/mirror/event/shop/shop_burn.png",
                "sinking": "./pic/mirror/event/shop/shop_sinking.png",
                "charge": "./pic/mirror/event/shop/shop_charge.png",
                "bleed": "./pic/mirror/event/shop/shop_bleed.png",
                "tremor": "./pic/mirror/event/shop/shop_tremor.png",
                "rupture": "./pic/mirror/event/shop/shop_rupture.png",
                "poise": "./pic/mirror/event/shop/shop_poise.png",
                "clash": "./pic/mirror/event/shop/shop_clash.png",
                "slash": "./pic/mirror/event/shop/shop_slash.png",
                "blunt": "./pic/mirror/event/shop/shop_blunt.png"}

must_to_buy_path = "./pic/mirror/event/shop/must_to_buy/"
must_to_buy = []
for root, dirs, files in os.walk(must_to_buy_path):
    for file in files:
        # 拼接完整的文件路径
        full_path = os.path.join(root, file)
        # 将文件路径添加到列表中
        must_to_buy.append(full_path)


def road_to_mir():
    back_init_menu()
    while get_pic_position("./pic/scenes/drive_features.png") is None:
        mouse_click(get_pic_position("./pic/scenes/init_drive.png"))
    mouse_click(get_pic_position("./pic/scenes/mirror_dungeons.png"))


def enter_mir(system="random", team=1):
    systems = {"bleed": "./pic/mirror/select_team/bleed_ego_gift",
               "burn": "./pic/mirror/select_team/burn_ego_gift",
               "tremor": "./pic/mirror/select_team/tremor_ego_gift",
               "rupture": "./pic/mirror/select_team/rupture_ego_gift",
               "sinking": "./pic/mirror/select_team/sinking_ego_gift",
               "poise": "./pic/mirror/select_team/poise_ego_gift",
               "charge": "./pic/mirror/select_team/charge_ego_gift"}
    mouse_click(get_pic_position("./pic/mirror/normal_mirror.png"))
    if enter_normal_mir := get_pic_position("./pic/mirror/enter_normal_mirror.png"):
        mouse_click(enter_normal_mir)
        sleep(1)
        while get_pic_position("./pic/mirror/wish_of_stars.png"):
            mouse_click(get_pic_position("./pic/mirror/wish_of_stars_confirm.png"))
            retry()
        while get_pic_position("./pic/mirror/select_init_ego_gift.png") is None:
            retry()
        mouse_click(get_pic_position(sys := systems[system] + '.png'))
        mouse_click(get_pic_position(sys := systems[system] + '_1.png'))
        mouse_click(get_pic_position(sys := systems[system] + '_2.png'))
        mouse_click(get_pic_position("./pic/mirror/select_team/select_ego_gift.png"))
        while get_pic_position("./pic/mirror/ego_gift_get.png") is None:
            retry()
        while ego_gift_get_confirm := get_pic_position("./pic/mirror/ego_gift_get_confirm.png"):
            mouse_click(ego_gift_get_confirm)
            sleep(1)
        if select_battle_team(team):
            while enter_mir_confirm := get_pic_position("./pic/mirror/enter_mir_confirm.png"):
                mouse_click(enter_mir_confirm)
    elif resume := get_pic_position("./pic/mirror/resume_mir.png"):
        mouse_click(resume)


@begin_and_finish_log(task_name="选择镜牢主题包")
# 选择镜牢主题包
def select_theme_pack():
    while get_pic_position("./pic/mirror/theme_pack_features.png") is None:
        sleep(1)
    if get_pic_position("./pic/mirror/theme_pack_features.png"):
        sleep(4)
        all_pic_byte_stream = get_theme_pack("./pic/mirror/theme_pack_features.png")
        for pic in all_pic_byte_stream:
            if compare_the_blacklist(pic[0]):
                mouse_drag_down(pic[1])
                return 0
    if refresh_button := get_pic_position("./pic/mirror/refresh_theme_pack.png"):
        mouse_click(refresh_button)
    if get_pic_position("./pic/mirror/theme_pack_features.png"):
        sleep(4)
        all_pic_byte_stream = get_theme_pack("./pic/mirror/theme_pack_features.png")
        for pic in all_pic_byte_stream:
            if compare_the_blacklist(pic[0]):
                mouse_drag_down(pic[1])
                return 0
    mouse_drag_down(get_theme_pack("./pic/mirror/theme_pack_features.png"))
    sleep(3)


@begin_and_finish_log(task_name="镜牢获取奖励卡")
# 获取奖励卡
def get_reward_card():
    all_cards = ["./pic/mirror/gain_ego_resource.png", "./pic/mirror/gain_cost.png",
                 "./pic/mirror/gain_cost_and_ego.png", "./pic/mirror/gain_ego.png",
                 "./pic/mirror/gain_starlight.png"]
    for card in all_cards[::-1]:
        card_position = get_pic_position(card)
        if card_position:
            mouse_click(card_position)
            break
    if reward_card_confirm := get_pic_position("./pic/mirror/reward_card_confirm.png"):
        mouse_click(reward_card_confirm)
        sleep(5)
        if ego_gift_get_confirm := get_pic_position("./pic/mirror/ego_gift_get_confirm.png"):
            mouse_click(ego_gift_get_confirm)


@begin_and_finish_log(task_name="镜牢寻路")
# 在默认缩放情况下，进行镜牢寻路
def search_road_default_distanc():
    # 后续补充窗口大小设置后需要修改！！！
    three_roads = [[500 * scale_factors[0], 0],
                   [500 * scale_factors[0], -400 * scale_factors[0]],
                   [500 * scale_factors[0], 450 * scale_factors[0]]]
    if bus_position := get_pic_position("./pic/mirror/mybus_default_distanc.png"):
        for road in three_roads:
            road[0] += bus_position[0]
            road[1] += bus_position[1]
            if 0 < road[0] < 2560 * scale_factors[0] and 0 < road[1] < 1440 * scale_factors[0]:
                mouse_click(road)
                sleep(0.5)
                if enter := get_pic_position("./pic/mirror/enter_room.png"):
                    mouse_click(enter)
                    return True
        mouse_click(bus_position)
        if enter := get_pic_position("./pic/mirror/enter_room.png"):
            mouse_click(enter)
            return True
    else:
        if search_road_farthest_distanc() is False:
            # 如果寻路失败，退出镜牢重进
            pass


# 如果默认缩放无法镜牢寻路，进行滚轮缩放后继续寻路
def search_road_farthest_distanc():
    mouse_scroll_farthest()
    three_roads = [[250 * scale_factors[0], -200 * scale_factors[0]],
                   [250 * scale_factors[0], 0],
                   [250 * scale_factors[0], 225 * scale_factors[0]]]
    if bus_position := get_pic_position("./pic/mirror/mybus_default_distanc.png"):
        for road in three_roads:
            road[0] += bus_position[0]
            road[1] += bus_position[1]
            if 0 < road[0] < 2560 * scale_factors[0] and 0 < road[1] < 1440 * scale_factors[0]:
                mouse_click(road)
                if enter := get_pic_position("./pic/mirror/enter_room.png"):
                    mouse_click(enter)
                    return True
        return False
    else:
        return False


# 为EGO饰品升级
def ego_gift_to_power_up():
    while ego_gift_power_up := get_pic_position("./pic/mirror/event/rest_room/ego_gift_power_up.png"):
        mouse_click(ego_gift_power_up)
        if power_up_confirm := get_pic_position("./pic/mirror/event/rest_room/power_up_confirm.png"):
            mouse_click(power_up_confirm)
            if get_pic_position("./pic/mirror/event/rest_room/power_up_confirm.png"):
                mouse_click(get_pic_position("./pic/mirror/event/rest_room/power_up_cancel.png"))
                break
        elif get_pic_position_without_cap("./pic/mirror/event/rest_room/cannot_enhance.png"):
            break
        else:
            break


@begin_and_finish_log(task_name="镜牢休息房间")
# 在休息房间时的处理
def in_rest_room(system):
    # 全体治疗
    if heal_sinner_button := get_pic_position("./pic/mirror/event/rest_room/heal_sinner.png"):
        mouse_click(heal_sinner_button)
        if get_pic_position("./pic/mirror/event/rest_room/heal_sinner_sold_out.png") is None:
            mouse_click(get_pic_position("./pic/mirror/event/rest_room/heal_sinner_choosen.png"))
            times = 5
            while get_pic_position("./pic/event/continue.png") is None:
                if skip_button := get_pic_position("./pic/mirror/event/skip.png"):
                    mouse_click(skip_button, 5)
                retry()
                times -= 1
                if times < 0:
                    leave = commom_ocr("./pic/mirror/event/leave_heal_sinner.png", 320, 100)
                    p = []
                    for b in leave:
                        if "move" in b['text'].lower():
                            box = b['box']
                            p = [(box[0][0] + box[2][0]) // 2, (box[0][1] + box[2][1]) // 2]
                    mouse_click(p)
                    break
                if times < -5:
                    leave = commom_gain_text(commom_all_ocr()[0])
                    p = []
                    for b in leave:
                        if "move" in b['text'].lower():
                            box = b['box']
                            p = [(box[0][0] + box[2][0]) // 2, (box[0][1] + box[2][1]) // 2]
                    mouse_click(p)
                    break
                if get_pic_position("./pic/mirror/event/rest_room/leave.png"):
                    break
            if continue_button := get_pic_position("./pic/event/continue.png"):
                mouse_click(continue_button)
    # 升级体系ego饰品
    if enhance_gifts_button := get_pic_position("./pic/mirror/event/rest_room/enhance_gifts.png"):
        mouse_click(enhance_gifts_button)
        if get_pic_position(systems_big_pic[system]):
            ego_gift_to_power_up()
        if gifts := get_all_pic_position(systems[system]):
            for gift in gifts:
                mouse_click(gift)
                ego_gift_to_power_up()
        if ego_gift_power_up_close := get_pic_position(
                "./pic/mirror/event/rest_room/ego_gift_power_up_close.png"):
            mouse_click(ego_gift_power_up_close)
    # 离开休息房间
    mouse_click(get_pic_position("./pic/mirror/event/rest_room/leave.png"))
    mouse_click(get_pic_position("./pic/mirror/event/rest_room/leave_confirm.png"))


@begin_and_finish_log(task_name="镜牢商店")
# 在商店的处理
def in_shop(system, shop_sell_list):
    # 全体治疗
    if heal_sinner := get_pic_position("./pic/mirror/event/shop/heal_sinner.png"):
        mouse_click(heal_sinner)
        mouse_click(get_pic_position("./pic/mirror/event/shop/heal_sinner_button.png"))
        times = 5
        while get_pic_position("./pic/event/continue.png") is None:
            if skip_button := get_pic_position("./pic/mirror/event/skip.png"):
                mouse_click(skip_button, 5)
            retry()
            times -= 1
            if times < 0:
                mouse_click(get_pic_position("./pic/mirror/event/leave_heal_sinner.png"))
                break
        if continue_button := get_pic_position("./pic/event/continue.png"):
            mouse_click(continue_button)
    # 出售无用饰品
    if sell_gifts_button := get_pic_position("./pic/mirror/event/shop/sell_gifts.png"):
        mouse_click(sell_gifts_button)
        for sell_system in shop_sell_list:
            path = "./pic/mirror/event/rest_room/"
            my_sell_system = path + sell_system + ".png"
            while gift := get_pic_position(my_sell_system):
                mouse_click(gift)
                mouse_click(get_pic_position("./pic/mirror/event/shop/sell_button.png"))
                mouse_click(get_pic_position("./pic/mirror/event/shop/sell_confirm.png"))
        if white_gossypium := get_pic_position("./pic/mirror/event/shop/must_to_sell/white_gossypium.png"):
            mouse_click(white_gossypium)
            mouse_click(get_pic_position("./pic/mirror/event/shop/sell_button.png"))
            mouse_click(get_pic_position("./pic/mirror/event/shop/sell_confirm.png"))
        while get_pic_position("./pic/mirror/event/shop/sell_close_button.png") is None:
            retry()
        mouse_click(get_pic_position("./pic/mirror/event/shop/sell_close_button.png"))
    # 购买必买项（回血饰品）
    for commodity in must_to_buy:
        if item := get_pic_position(commodity):
            mouse_click(item)
            mouse_click(get_pic_position("./pic/mirror/event/shop/purchase.png"))
            while ego_gift_get_confirm := get_pic_position("./pic/mirror/ego_gift_get_confirm.png"):
                mouse_click(ego_gift_get_confirm)
    # 购买体系饰品
    if gifts := get_all_pic_position(systems_shop[system]):
        for gift in gifts:
            mouse_click(gift)
            if get_pic_position("./pic/mirror/event/shop/purchase.png"):
                mouse_click(get_pic_position("./pic/mirror/event/shop/purchase.png"))
                while ego_gift_get_confirm := get_pic_position("./pic/mirror/ego_gift_get_confirm.png"):
                    mouse_click(ego_gift_get_confirm)

    # 离开商店
    mouse_click(get_pic_position("./pic/mirror/event/rest_room/leave.png"))
    mouse_click(get_pic_position("./pic/mirror/event/rest_room/leave_confirm.png"))


# 一次镜本流程
def execute_a_mirror(sinner_team, which_team, shop_sell_list, system="burn"):
    if get_pic_position("./pic/teams/to_battle.png"):
        mouse_click(get_pic_position("./pic/scenes/the_back_button.png"))
    if get_pic_position("./pic/scenes/road_in_mirror.png") is None and get_pic_position(
            "./pic/mirror/theme_pack_features.png") is None:
        road_to_mir()
        enter_mir(system, which_team)
    first_battle = True
    # 未到达奖励页不会停止
    while get_pic_position("./pic/mirror/total_progress.png") is None:
        # 选择楼层主题的情况
        if get_pic_position("./pic/scenes/mirror_select_theme_pack.png"):
            select_theme_pack()

        # 在镜牢中寻路
        if get_pic_position("./pic/scenes/road_in_mirror.png"):
            search_road_default_distanc()

        # 战斗配队的情况
        if get_pic_position("./pic/teams/formation_features.png"):
            if first_battle or get_pic_position("./pic/teams/full_team.png", 0.9) is None:
                team_formation(sinner_team)
                first_battle = False
            mouse_click(get_pic_position("./pic/teams/to_battle.png"))
            battle()

        # 遇到有SKIP的情况
        while skip_button := get_pic_position("./pic/mirror/event/skip.png"):
            # 如果存在SKIP按钮，多次点击
            mouse_click(skip_button, 5)

            # 针对不同事件进行处理，优先选需要判定的
            if gain_ego := get_pic_position("./pic/mirror/event/advantage_check.png"):
                mouse_click(gain_ego)
            elif gain_ego := get_pic_position("./pic/mirror/event/selet_to_gain_ego.png"):
                mouse_click(gain_ego)
            elif gain_ego := get_pic_position("./pic/mirror/event/gain_a_ego_depending_on_result.png"):
                mouse_click(gain_ego)
            elif get_pic_position("./pic/mirror/event/random_to_choose_event.png") and \
                    get_pic_position("./pic/mirror/event/choices.png"):
                mouse_click(get_pic_position("./pic/mirror/event/random_to_choose_event.png"))

            # 如果是右下角的红色按钮
            if proceed_button := get_pic_position("./pic/mirror/event/proceed.png"):
                mouse_click(proceed_button)
            if continue_button := get_pic_position("./pic/mirror/event/continue.png"):
                mouse_click(continue_button)

            # 如果遇到判定事件
            if get_pic_position("./pic/event/perform_the_check_features_1.png") and get_pic_position(
                    "./pic/event/perform_the_check_features_2.png"):
                decision_event_handling()

            # 如果事件结束，得到饰品
            if get_pic_position("./pic/mirror/ego_gift_get.png"):
                if ego_gift_get_confirm := get_pic_position("./pic/mirror/ego_gift_get_confirm.png"):
                    mouse_click(ego_gift_get_confirm)

            # 休息室事件
            if get_pic_position("./pic/mirror/event/rest_room/rest_room_features_1.png") and \
                    get_pic_position("./pic/mirror/event/rest_room/heal_sinner.png"):
                in_rest_room(system)
            # 商店事件
            if get_pic_position("./pic/mirror/event/shop/shop_features_1.png") and \
                    get_pic_position("./pic/mirror/event/shop/shop_features_2.png"):
                in_shop(system, shop_sell_list)

            retry()

        # 如果遇到获取ego饰品的情况
        if acquire_ego_gift := get_pic_position("./pic/mirror/acquire_ego_gift.png"):
            # 还可以加些判断！！！
            if get_pic_position("./pic/mirror/black_list/white_gossypium.png"):
                mouse_click(get_pic_position("./pic/mirror/refuse_gift.png"))
            else:
                get_gift_path = "./pic/mirror/acquire_ego_gift/"
                select_path = get_gift_path + system + ".png"
                if select_gift := get_pic_position(select_path):
                    mouse_click(select_gift)
                else:
                    mouse_click(acquire_ego_gift)
                if select_ego_gift := get_pic_position("./pic/mirror/select_team/select_ego_gift.png"):
                    mouse_click(select_ego_gift)
                    if ego_gift_get_confirm := get_pic_position("./pic/mirror/ego_gift_get_confirm.png"):
                        mouse_click(ego_gift_get_confirm)

        # 防卡死
        if ego_gift_get_confirm := get_pic_position("./pic/mirror/ego_gift_get_confirm.png"):
            mouse_click(ego_gift_get_confirm)

        if get_pic_position("./pic/mirror/select_encounter_reward_card.png"):
            sleep(2)  # 防止过快点击导致脚本卡死
            get_reward_card()
        if get_pic_position("./pic/mirror/leave_reward_card.png"):
            mouse_click(get_pic_position("./pic/mirror/leave_reward_card_cancel.png"))
        if enter := get_pic_position("./pic/mirror/enter_room.png"):
            mouse_click(enter)
        if enter_mir_confirm := get_pic_position("./pic/mirror/enter_mir_confirm.png"):
            mouse_click(enter_mir_confirm)
    msg = f"开始进行镜牢奖励领取"
    my_log("info", msg)
    if claim_rewards := get_pic_position("./pic/mirror/claim_rewards.png"):
        mouse_click(claim_rewards)
    mouse_click(get_pic_position("./pic/mirror/claim.png"))
    mouse_click(get_pic_position("./pic/mirror/claim_confirm.png"))
    while get_pic_position("./pic/mirror/claim_last_confirm.png") is None:
        retry()
    if claim_last_confirm := get_pic_position("./pic/mirror/claim_last_confirm.png"):
        mouse_click(claim_last_confirm)
        sleep(1)
    if claim_last_confirm := get_pic_position("./pic/mirror/claim_last_confirm.png"):
        mouse_click(claim_last_confirm)
