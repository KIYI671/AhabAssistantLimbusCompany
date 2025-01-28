from time import sleep

from module.automation import auto
from module.config import cfg
from module.logger import log
from tasks.base.back_init_menu import back_init_menu
from tasks.base.retry import retry
from tasks.mirror import must_be_abandoned, must_purchase, fusion_material
from utils.image_utils import ImageUtils

system_cn_zh = {
    "burn": "烧伤",
    "bleed": "流血",
    "tremor": "震颤",
    "rupture": "破裂",
    "poise": "呼吸",
    "sinking": "沉沦",
    "charge": "充能",
    "slash": "斩击",
    "pierce": "突刺",
    "blunt": "打击"
}


def ego_gift_to_power_up():
    loop_count = 30
    auto.model = 'clam'
    while True:
        # 自动截图
        if auto.take_screenshot() is None:
            continue
        auto.mouse_to_blank()
        if auto.click_element("mirror/shop/power_up_assets.png"):
            auto.mouse_to_blank()
            sleep(0.5)
            while auto.take_screenshot() is None:
                continue
            if auto.click_element("mirror/shop/power_up_confirm_assets.png") is False:
                return True
            sleep(3)
            retry()
        if auto.find_element("mirror/shop/power_up_confirm_assets.png"):
            return False
        loop_count -= 1
        if loop_count < 20:
            auto.model = "normal"
        if loop_count < 10:
            auto.model = 'aggressive'
        if loop_count < 0:
            log.ERROR("无法升级ego饰品")
            break


def buy_gifts(system, fuse_aggressive_switch):
    refresh = False
    refresh_keyword = False
    while True:
        # 自动截图
        if auto.take_screenshot() is None:
            continue
        # 购买必买项（回血饰品）
        for commodity in must_purchase:
            if auto.click_element(commodity, threshold=0.85):
                while auto.click_element("mirror/shop/purchase_assets.png") is False:
                    while auto.take_screenshot() is None:
                        continue
                    retry()
                    continue
                sleep(1)
                auto.click_element("mirror/road_in_mir/ego_gift_get_confirm_assets.png", take_screenshot=True)
                while auto.take_screenshot() is None:
                    continue
        # 购买体系饰品
        system_gift = auto.find_element(f"mirror/shop/enhance_gifts/shop_{system}.png",
                                        find_type='image_with_multiple_targets', threshold=0.85)
        for gift in system_gift:
            auto.mouse_click(gift[0], gift[1])
            sleep(1)
            while auto.take_screenshot() is None:
                continue
            if system == 'bleed':
                if cfg.language == 'en':
                    if auto.find_text_element(["white", "gossypium"], all_text=True):
                        auto.mouse_click_blank(times=2)
                elif cfg.language == 'zh_cn':
                    if auto.find_text_element("白棉花"):
                        auto.mouse_click_blank(times=2)
                sleep(1)
            if auto.click_element("mirror/shop/purchase_assets.png", take_screenshot=True):
                sleep(1)
                auto.click_element("mirror/road_in_mir/ego_gift_get_confirm_assets.png", take_screenshot=True)
                auto.mouse_click_blank(times=3)
                continue
            else:
                auto.mouse_click_blank(times=2)
                sleep(1)

        if fuse_aggressive_switch:
            if auto.click_element("mirror/shop/level_IV_to_buy.png", threshold=0.9):
                sleep(1)
                while auto.take_screenshot() is None:
                    continue
                if auto.click_element("mirror/shop/purchase_assets.png"):
                    sleep(1)
                    while auto.take_screenshot() is None:
                        continue
                    auto.click_element("mirror/road_in_mir/ego_gift_get_confirm_assets.png")
                    continue
                else:
                    auto.mouse_click_blank()

            if auto.click_element("mirror/shop/level_III_to_buy.png", threshold=0.9):
                sleep(1)
                if auto.click_element("mirror/shop/purchase_assets.png", take_screenshot=True):
                    sleep(1)
                    auto.click_element("mirror/road_in_mir/ego_gift_get_confirm_assets.png", take_screenshot=True)
                    continue
                else:
                    auto.mouse_click_blank()

        retry()
        try:
            money_bbox = ImageUtils.get_bbox(ImageUtils.load_image("mirror/shop/my_money_bbox.png"))
            my_money = auto.get_text_from_screenshot(money_bbox)
            my_remaining_money = int(my_money[0])
            if not isinstance(my_remaining_money, int):
                log.ERROR(f"获取剩余金钱失败")
                my_remaining_money = -1
            else:
                log.DEBUG(f"剩余金钱：{my_remaining_money}")
        except Exception as e:
            log.ERROR(f"获取剩余金钱失败：{e}")
            my_remaining_money = -1
        if my_remaining_money <= 300:
            refresh_keyword = True
        if my_remaining_money <= 200:
            refresh = True

        if refresh is False:
            auto.mouse_click_blank(times=3)
            if auto.click_element("mirror/shop/refresh_assets.png"):
                refresh = True
                sleep(3)
                continue
            refresh = True

        if refresh_keyword is False:
            auto.mouse_click_blank(times=3)
            if auto.click_element("mirror/shop/refresh_keyword_assets.png"):
                sleep(1)
                auto.click_element(f"mirror/shop/keyword/keyword_{system}.png", take_screenshot=True)
                auto.click_element("mirror/shop/refresh_keyword_confirm_assets.png")
                refresh_keyword = True
                auto.mouse_click_blank()
                sleep(3)
                continue
            refresh_keyword = True

        break


def fuse_useless_gifts_aggressive(system):
    """合成无用饰品_激进版"""

    def processing_coordinates(my_gift_list):
        """将列表从左上到右下排序，然后去重"""
        scale = cfg.set_win_size / 1080
        # 排序
        sorted_list = sorted(my_gift_list, key=lambda x: (x[1], x[0]))

        # 去除重复坐标
        unique_list = []
        for coord in sorted_list:
            if not any(abs(coord[0] - x[0]) <= 40 * scale and
                       abs(coord[1] - x[1]) <= 40 * scale for x in unique_list):
                unique_list.append(coord)
        for i in range(len(unique_list)):
            coord = unique_list[i]
            coord = (coord[0] + 100 * scale, coord[1] - 100 * scale)
            unique_list[i] = coord

        return unique_list

    fuse_IV = False
    while True:
        if auto.take_screenshot() is None:
            continue

        fuse = False
        gift_list = []

        gift = auto.find_element("mirror/shop/fuse_aggressive.png", find_type="image_with_multiple_targets")
        if gift:
            if isinstance(gift, list):
                gift_list.extend(list(g) for g in gift)
            elif isinstance(gift, tuple):
                gift_list.append(gift)

        # 对饰品位置列表进行排序、去重处理
        my_list = processing_coordinates(gift_list)

        # 选择至多3样饰品
        if len(my_list) <= 2:
            msg = f"饰品列表数量不足，结束合成"
            log.DEBUG(msg)
            return
        else:
            for sequence in range(3):
                try:
                    gift_position = my_list[sequence]
                    auto.mouse_click(gift_position[0], gift_position[1])
                    sleep(0.75)
                except IndexError:
                    msg = f"饰品列表已经没有第{sequence + 1}项了"
                    log.DEBUG(msg)
            sleep(1)

        fuse_confirm = False
        loop_times = 15
        while True:
            if auto.take_screenshot() is None:
                continue

            if fuse_confirm:
                if ego_gift_get_confirm := auto.find_element("mirror/road_in_mir/ego_gift_get_confirm_assets.png"):
                    if cfg.language == "zh_cn":
                        excluded_names = "残片"
                    else:
                        excluded_names = ["fragment", "corrosion"]
                    if auto.find_element(excluded_names, find_type="text"):
                        fuse = True
                    else:
                        if cfg.language == "zh_cn":
                            system_name = system_cn_zh[system]
                        else:
                            system_name = system
                        if auto.find_element(system_name, find_type="text"):
                            fuse_IV = True
                            fuse = False
                    auto.mouse_click(ego_gift_get_confirm[0], ego_gift_get_confirm[1])
                    break

                if auto.click_element("mirror/shop/enhance_and_fuse_and_sell_confirm_assets.png", model="normal"):
                    sleep(2)
                    if loop_times <= 0:
                        break
                    loop_times -= 1
                    continue
            else:
                if auto.find_element("mirror/shop/fusion_level_IV_gift_assets.png",
                                     threshold=0.9) and auto.find_element("mirror/shop/fuse_90%_assets.png"):
                    fuse_confirm = True
                else:
                    break

        if fuse:
            sleep(2)
            auto.click_element("mirror/shop/fuse_ego_gift_assets.png", take_screenshot=True)
            continue

        break
    if fuse_IV:
        log.INFO(f"合成四级")
        return True


def fuse_useless_gifts(shop_sell_list,system):
    """合成无用饰品"""

    def processing_coordinates(my_gift_list):
        """将列表从左上到右下排序，然后去重"""
        scale = cfg.set_win_size / 1080
        # 排序
        sorted_list = sorted(my_gift_list, key=lambda x: (x[1], x[0]))

        # 去除重复坐标
        unique_list = []
        for coord in sorted_list:
            if not any(abs(coord[0] - x[0]) <= 40 * scale and
                       abs(coord[1] - x[1]) <= 40 * scale for x in unique_list):
                unique_list.append(coord)

        return unique_list

    fuse_IV_confirm = False
    block = True
    while True:
        if auto.take_screenshot() is None:
            continue

        fuse = False
        select_gifts = False
        gift_list = []

        # 获取无用饰品列表
        for commodity in must_be_abandoned:
            item = auto.find_element(commodity, find_type="image_with_multiple_targets")
            if "white_gossypium" in commodity and "bleed" in shop_sell_list:
                continue
            if item:
                if isinstance(item, list):
                    gift_list.extend(list(g) for g in item)
                elif isinstance(item, tuple):
                    gift_list.append(item)
        for sell_system in shop_sell_list:
            my_sell_system = f"mirror/shop/enhance_gifts/{sell_system}.png"
            gift = auto.find_element(my_sell_system, find_type="image_with_multiple_targets")
            if gift:
                if isinstance(gift, list):
                    gift_list.extend(list(g) for g in gift)
                elif isinstance(gift, tuple):
                    gift_list.append(gift)
        # 对饰品位置列表进行排序、去重处理
        my_list = processing_coordinates(gift_list)
        # 选择至多3样无用饰品
        if len(my_list) <= 1:
            if block is False:
                msg = f"饰品舍弃列表数量不足，结束合成"
                log.DEBUG(msg)
                return
        else:
            for sequence in range(3):
                try:
                    gift_position = my_list[sequence]
                    auto.mouse_click(gift_position[0], gift_position[1])
                    sleep(0.75)
                except IndexError:
                    msg = f"饰品舍弃列表已经没有第{sequence + 1}项了"
                    log.DEBUG(msg)
            select_gifts = True

        if select_gifts:
            loop_times = 15
            fuse_IV = False
            while True:
                if auto.take_screenshot() is None:
                    continue

                if loop_times < 0:
                    break
                loop_times -= 1

                if auto.find_element("mirror/shop/fusion_level_IV_gift_assets.png",
                                     threshold=0.9) and auto.find_element("mirror/shop/fuse_90%_assets.png"):
                    fuse_IV = True

                if auto.find_element("mirror/road_in_mir/ego_gift_get_confirm_assets.png"):
                    if fuse_IV:
                        if cfg.language == "zh_cn":
                            excluded_names = "残片"
                        else:
                            excluded_names = ["fragment", "corrosion"]
                        if auto.find_element(excluded_names, find_type="text"):
                            pass
                        else:
                            if cfg.language == "zh_cn":
                                system_name = system_cn_zh[system]
                            else:
                                system_name = system
                            if auto.find_element(system_name, find_type="text"):
                                fuse_IV_confirm = True
                        fuse = True
                        auto.click_element("mirror/road_in_mir/ego_gift_get_confirm_assets.png")
                        sleep(1)
                        break
                    else:
                        if auto.click_element("mirror/road_in_mir/ego_gift_get_confirm_assets.png"):
                            fuse = True
                            sleep(1)
                            break

                if auto.click_element("mirror/shop/enhance_and_fuse_and_sell_confirm_assets.png", model="normal"):
                    continue

                if auto.click_element("mirror/shop/fuse_ego_gift_assets.png"):
                    continue

        if fuse:
            auto.click_element("mirror/shop/fuse_ego_gift_assets.png", take_screenshot=True)
            continue

        while auto.take_screenshot() is None:
            continue
        list_block = auto.find_element("mirror/shop/gifts_list_block.png")
        if list_block is not None and block:
            block = False
            auto.mouse_drag(list_block[0], list_block[1], drag_time=1, dy=500)
            continue

        auto.mouse_click_blank(times=3)
        break
    if fuse_IV_confirm:
        log.INFO(f"合成四级")
        return True


def fuse_system_gifts(system, times):
    """合成体系饰品"""
    loop_count = 30
    auto.model = 'clam'

    print(f"开始合成{system}体系饰品第{times + 1}种")
    # 获取合成公式
    system_gifts = fusion_material[system]
    if len(system_gifts) == 2:
        my_fuse_system_gifts = [system_gifts[0], system_gifts[1]]
    else:
        my_fuse_system_gifts = [system_gifts, []]
    # 标记合成可行性
    fusion = True
    fusion_position = {}
    # 如果无第二合成公式，返回
    if len(my_fuse_system_gifts[times]) == 0:
        return

    while True:
        if auto.take_screenshot() is None:
            continue

        # 进入合成页面
        if auto.click_element("mirror/shop/fuse_gift_assets.png"):
            continue

        if auto.click_element(f"mirror/shop/keyword/keyword_{system}.png"):
            while auto.take_screenshot() is None:
                continue
            if auto.click_element("mirror/shop/fuse_gift_confirm_assets.png", model="normal"):
                break
        if auto.click_element("mirror/shop/fuse_to_select_keyword_assets.png"):
            continue

        loop_count -= 1
        if loop_count < 20:
            auto.model = "normal"
        if loop_count < 10:
            auto.model = 'aggressive'
        if loop_count < 0:
            log.ERROR("无法合成ego饰品")
            break

    # 如果找到合成素材，记录位置后点击
    for select_gift in my_fuse_system_gifts[times]:
        while auto.take_screenshot() is None:
            continue
        pos = auto.find_element(f"mirror/shop/fusion_material/{select_gift}")
        if pos is None:
            if select_gift not in fusion_position:
                fusion_position[select_gift] = None
        else:
            if select_gift in fusion_position:
                if fusion_position[select_gift] is None:
                    fusion_position[select_gift] = pos
            else:
                fusion_position[select_gift] = pos
            auto.mouse_click(pos[0], pos[1])
            auto.click_element("mirror/shop/fuse_ego_gift_assets.png")

    list_block = auto.find_element("mirror/shop/gifts_list_block.png")
    block = False
    if list_block is not None:
        block = True
        auto.mouse_drag(list_block[0], list_block[1], drag_time=1, dy=500)

    if block:
        # 如果找到合成素材，如果是无记录位置的，记录位置后点击
        for select_gift in my_fuse_system_gifts[times]:
            while auto.take_screenshot() is None:
                continue
            pos = auto.find_element(f"mirror/shop/fusion_material/{select_gift}")
            if pos is not None:
                if select_gift in fusion_position:
                    if fusion_position[select_gift] is None:
                        fusion_position[select_gift] = pos
                        auto.mouse_click(pos[0], pos[1])
                        sleep(0.5)
                        auto.click_element("mirror/shop/fuse_ego_gift_assets.png")
                else:
                    fusion_position[select_gift] = pos
                    auto.mouse_click(pos[0], pos[1])
                    sleep(0.5)
                    auto.click_element("mirror/shop/fuse_ego_gift_assets.png")

    for name in (my_fuse_system_gifts[times]):
        if fusion_position[name] is None:
            fusion = False

    loop_count = 30
    auto.model = 'clam'
    while fusion:
        if auto.take_screenshot() is None:
            continue
        auto.mouse_to_blank()

        if auto.click_element("mirror/road_in_mir/ego_gift_get_confirm_assets.png"):
            break

        if auto.click_element("mirror/shop/enhance_and_fuse_and_sell_confirm_assets.png", model="normal"):
            continue

        loop_count -= 1
        if loop_count < 20:
            auto.model = "normal"
        if loop_count < 10:
            auto.model = 'aggressive'
        if loop_count < 0:
            log.ERROR("无法合成ego饰品")
            break

    if fusion:
        msg = f"成功合成{system}体系饰品{times + 1}号"
        log.DEBUG(msg)
    else:
        msg = f"无法合成{system}体系饰品{times + 1}号"
        log.DEBUG(msg)

    auto.mouse_click_blank(times=3)


def sell_gifts(shop_sell_list):
    list_block = False
    system_sell = True
    while True:
        # 自动截图
        if auto.take_screenshot() is None:
            continue

        gift_sell = False

        if auto.click_element("mirror/shop/sell_gift_assets.png"):
            continue

        if auto.click_element("mirror/shop/sell_gift_confirm_assets.png"):
            continue

        if system_sell:
            for sell_system in shop_sell_list:
                my_sell_system = f"mirror/shop/enhance_gifts/{sell_system}.png"
                if auto.click_element(my_sell_system):
                    auto.click_element("mirror/shop/enhance_and_fuse_and_sell_confirm_assets.png", model='normal')
                    sleep(1)
                    gift_sell = True
                    break

        if gift_sell:
            continue

        if list_block is False and auto.find_element("mirror/shop/gifts_list_block.png"):
            block_position = auto.find_element("mirror/shop/gifts_list_block.png")
            auto.mouse_drag(block_position[0], block_position[1], drag_time=1, dy=500)
            list_block = True
            continue

        system_sell = False

        for commodity in must_be_abandoned:
            if auto.click_element(commodity):
                auto.click_element("mirror/shop/enhance_and_fuse_and_sell_confirm_assets.png", model='normal')
                sleep(1)
                gift_sell = True
                break

        if gift_sell:
            continue

        auto.mouse_click_blank(times=3)
        sleep(1)
        break


def enter_fuse(system):
    while True:
        if auto.take_screenshot() is None:
            continue

        # 进入合成页面
        if auto.click_element("mirror/shop/fuse_gift_assets.png"):
            continue

        if auto.click_element(f"mirror/shop/keyword/keyword_{system}.png"):
            while auto.take_screenshot() is None:
                continue
            if auto.click_element("mirror/shop/fuse_gift_confirm_assets.png", model="normal"):
                break
        if auto.click_element("mirror/shop/fuse_to_select_keyword_assets.png"):
            continue


def fuse_gift(shop_sell_list, system, fuse_aggressive=False):
    fuse_IV = False
    if fuse_aggressive:
        enter_fuse(system)
        fuse_IV = fuse_useless_gifts_aggressive(system)
        auto.mouse_click_blank(times=3)

    enter_fuse(system)
    result = fuse_useless_gifts(shop_sell_list,system)
    auto.mouse_click_blank(times=3)
    if fuse_IV is False and result is True:
        fuse_IV = True

    if fuse_aggressive and fuse_IV is not True:
        enter_fuse(system)
        fuse_IV = fuse_useless_gifts_aggressive(system)
        auto.mouse_click_blank(times=3)

    if system not in fusion_material:
        fuse_times = 0
    else:
        fuse_times = 2
    for i in range(fuse_times):
        fuse_system_gifts(system, i)
        auto.mouse_click_blank(times=3)

    if fuse_IV:
        return True


def heal_sinner():
    # 全体治疗
    loop_count = 5
    auto.model = 'clam'
    sinner_be_heal = False
    while True:
        # 自动截图
        if auto.take_screenshot() is None:
            continue

        if sinner_be_heal is True and auto.click_element("mirror/shop/heal_sinner/heal_sinner_return_assets.png"):
            sleep(1)
            if auto.take_screenshot() is None:
                continue
            if auto.find_element('mirror/shop/shop_coins_assets.png'):
                break

        if auto.click_element("mirror/shop/heal_sinner/heal_all_sinner_assets.png"):
            sinner_be_heal = True
            continue

        if auto.click_element("mirror/shop/heal_sinner/heal_sinner_assets.png"):
            continue

        loop_count -= 1
        if loop_count < 3:
            auto.model = "normal"
        if loop_count < 1:
            auto.model = 'aggressive'
        if loop_count < 0:
            log.ERROR("治疗罪人失败")
            break


def enhance_gifts(system):
    while True:
        # 自动截图
        if auto.take_screenshot() is None:
            continue
        if auto.click_element("mirror/shop/enhance_gifts_assets.png"):
            sleep(1)
            break
        auto.mouse_click_blank()

    first_gift = True
    list_block = False
    loop_count = 30
    auto.model = 'clam'
    while True:
        # 自动截图
        if auto.take_screenshot() is None:
            continue
        next_gift = True
        if first_gift and auto.find_element(f"mirror/shop/enhance_gifts/big_{system}.png"):
            if ego_gift_to_power_up() is False:
                next_gift = False
            else:
                first_gift = False
                continue
        if gifts := auto.find_element(f"mirror/shop/enhance_gifts/{system}.png",
                                      find_type="image_with_multiple_targets"):
            all_true = True
            for gift in gifts:
                auto.mouse_click(gift[0], gift[1])
                if ego_gift_to_power_up() is False:
                    next_gift = False
                    all_true = False
                    break
            if all_true:
                break

        if list_block is False and auto.find_element("mirror/shop/gifts_list_block.png"):
            block_position = auto.find_element("mirror/shop/gifts_list_block.png")
            auto.mouse_drag(block_position[0], block_position[1], drag_time=1, dy=500)
            list_block = True
            continue

        if next_gift is False:
            break

        loop_count -= 1
        if loop_count < 20:
            auto.model = "normal"
        if loop_count < 10:
            auto.model = 'aggressive'
        if loop_count < 0:
            log.ERROR("升级ego饰品失败")
            break


# 在商店的处理
def in_shop(system, shop_sell_list, fuse_switch, fuse_aggressive_switch):
    heal = False
    sell = False
    buy = False
    fuse = False
    enhance = False
    fuse_IV = False
    while True:
        # 自动截图
        if auto.take_screenshot() is None:
            continue

        auto.mouse_click_blank(times=3)
        sleep(1)

        if heal is False:
            heal_sinner()
            heal = True
            continue

        if sell is False:
            # 出售无用饰品
            if fuse_switch is False:
                sell_gifts(shop_sell_list)
            sell = True
            continue

        if buy is False:
            buy_gifts(system, fuse_aggressive_switch)
            buy = True
            continue

        if fuse is False:
            # 合成饰品
            if fuse_switch:
                fuse_IV = fuse_gift(shop_sell_list, system, fuse_aggressive=fuse_aggressive_switch)
            fuse = True
            continue

        if enhance is False:
            # 升级体系ego饰品
            enhance_gifts(system)
            enhance = True
            continue

        break

    auto.mouse_click_blank(times=3)
    loop_count = 30
    auto.model = 'clam'
    while True:
        # 自动截图
        if auto.take_screenshot() is None:
            continue
        if auto.find_element("mirror/road_in_mir/legend_assets.png"):
            break
        if auto.click_element("mirror/shop/leave_shop_confirm_assets.png"):
            continue
        if auto.click_element("mirror/shop/leave_assets.png"):
            continue
        loop_count -= 1
        if loop_count < 20:
            auto.model = "normal"
        if loop_count < 10:
            auto.model = 'aggressive'
        if loop_count < 0:
            log.ERROR("无法退出商店,尝试回到初始界面")
            back_init_menu()
            break

    if fuse_IV:
        return True
    else:
        return False
