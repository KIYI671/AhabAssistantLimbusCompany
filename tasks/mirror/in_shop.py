from time import sleep

from module.automation import auto
from module.config import cfg
from module.logger import log
from tasks import system_cn_zh, all_systems, all_sinners_name, all_sinners_name_zh
from tasks.base.back_init_menu import back_init_menu
from tasks.base.retry import retry
from tasks.mirror import must_be_abandoned, must_purchase, fusion_material
from utils.image_utils import ImageUtils


class Shop:
    def __init__(self, team_setting: dict):
        self.system = all_systems[team_setting["team_system"]]  # 队伍体系
        self.sinner_team = team_setting["sinner_order"]  # 选择的罪人序列
        # 获取舍弃的饰品体系列表
        self.shop_sell_list = []
        for system in list(all_systems.values()):
            if system == self.system:
                continue
            if team_setting[f"system_{system}"]:
                self.shop_sell_list.append(system)
        self.fuse_switch = False if team_setting["shop_strategy"] == 0 else True  # 是否启动合成模式
        self.fuse_aggressive_switch = True if team_setting["shop_strategy"] == 2 else False  # 是否启动激进合成模式
        self.do_not_heal = team_setting["do_not_heal"]  # 是否不治疗
        self.do_not_buy = team_setting["do_not_buy"]  # 是否不购买
        self.do_not_fuse = team_setting["do_not_fuse"]  # 是否不合成
        self.do_not_sell = team_setting["do_not_sell"]  # 是否不出售
        self.do_not_enhance = team_setting["do_not_enhance"]  # 是否不升级
        self.only_aggressive_fuse = team_setting["only_aggressive_fuse"]  # 是否只进行激进合成，不进行其他合成
        self.do_not_system_fuse = team_setting["do_not_system_fuse"]  # 是否不进行体系饰品合成
        self.only_system_fuse = team_setting["only_system_fuse"]  # 是否只进行体系饰品合成
        # 是否在合成四级后改变行动策略
        self.after_level_IV = team_setting["after_level_IV"]
        self.after_level_IV_select = team_setting["after_level_IV_select"]
        # 是否自定义商店购物策略
        self.shopping_strategy = team_setting["shopping_strategy"]
        self.shopping_strategy_select = team_setting["shopping_strategy_select"]
        # 是否启用第二体系
        self.second_system = team_setting["second_system"]
        self.second_system_select = all_systems[team_setting["second_system_select"]]
        self.second_system_setting = team_setting["second_system_setting"]
        self.second_system_action = team_setting["second_system_action"]
        # 技能替换
        self.skill_replacement = team_setting["skill_replacement"]
        self.skill_replacement_select = team_setting["skill_replacement_select"]
        self.skill_replacement_mode = team_setting["skill_replacement_mode"]
        self.ignore_shop = team_setting["ignore_shop"]  # 忽略的商店楼层

        self.aggressive_also_enhance = team_setting["aggressive_also_enhance"]  # 激进合成期间也升级饰品

        self.fuse_IV = False
        self.fuse_second_IV = False
        self.fuse_system_gift_1 = False
        self.fuse_system_gift_2 = False
        self.the_first_line_position = None
        self.replacement = False

        # 用于记录已升级的ego饰品
        self.enhance_gifts_list = []
        self.first_gift_enhance = False

    class RestartGame(Exception):
        pass

    def ego_gift_to_power_up(self):
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
                if auto.click_element("mirror/shop/power_up_confirm_assets.png", take_screenshot=True) is False:
                    return True
                sleep(3)
                if retry() is False:
                    raise self.RestartGame()
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

    def buy_gifts(self):
        log.DEBUG("开始执行饰品购买模块")
        refresh = False
        refresh_keyword = False
        while True:
            # 自动截图
            if auto.take_screenshot() is None:
                continue
            if self.shopping_strategy is False or (
                    self.shopping_strategy and self.shopping_strategy_select in (0, 1, 5)):
                # 购买必买项（回血饰品）
                log.DEBUG("开始购买必买项")
                for commodity in must_purchase:
                    if auto.click_element(commodity, threshold=0.85):
                        while auto.click_element("mirror/shop/purchase_assets.png") is False:
                            while auto.take_screenshot() is None:
                                continue
                            if retry() is False:
                                raise self.RestartGame()
                            if auto.click_element("mirror/road_in_mir/ego_gift_get_confirm_assets.png"):
                                break
                            continue
                        sleep(1)
                        auto.click_element("mirror/road_in_mir/ego_gift_get_confirm_assets.png", take_screenshot=True)
                        while auto.take_screenshot() is None:
                            continue

            if self.fuse_aggressive_switch:
                log.DEBUG("开始购买强化素材")
                if self.shopping_strategy is False or (
                        self.shopping_strategy and self.shopping_strategy_select in (1, 3, 4)):
                    if auto.click_element("mirror/shop/level_IV_to_buy.png", threshold=0.82):
                        sleep(1)
                        while auto.take_screenshot() is None:
                            continue
                        if auto.click_element("mirror/shop/purchase_assets.png"):
                            sleep(1)
                            while auto.take_screenshot() is None:
                                continue
                            if retry() is False:
                                raise self.RestartGame()
                            auto.click_element("mirror/road_in_mir/ego_gift_get_confirm_assets.png")
                            continue
                        else:
                            auto.mouse_click_blank()

                    if auto.click_element("mirror/shop/level_III_to_buy.png", threshold=0.82):
                        sleep(1)
                        if auto.click_element("mirror/shop/purchase_assets.png", take_screenshot=True):
                            sleep(1)
                            if retry() is False:
                                raise self.RestartGame()
                            auto.click_element("mirror/road_in_mir/ego_gift_get_confirm_assets.png",
                                               take_screenshot=True)
                            continue
                        else:
                            auto.mouse_click_blank()

            if self.shopping_strategy is False or (
                    self.shopping_strategy and self.shopping_strategy_select in (2, 4, 5)):
                log.DEBUG("开始购买本体系饰品")
                # 购买体系饰品
                system_gift = auto.find_element(f"mirror/shop/enhance_gifts/shop_{self.system}.png",
                                                find_type='image_with_multiple_targets', threshold=0.85,
                                                take_screenshot=True)
                for gift in system_gift:
                    auto.mouse_click(gift[0], gift[1])
                    sleep(1)
                    while auto.take_screenshot() is None:
                        continue
                    if self.system == 'bleed':
                        if cfg.language_in_game == 'en':
                            if auto.find_text_element(["white", "gossypium"], all_text=True):
                                auto.mouse_click_blank(times=2)
                        elif cfg.language_in_game == 'zh_cn':
                            if auto.find_text_element("白棉花"):
                                auto.mouse_click_blank(times=2)
                        sleep(1)
                    if auto.click_element("mirror/shop/purchase_assets.png", take_screenshot=True):
                        sleep(1)
                        auto.click_element("mirror/road_in_mir/ego_gift_get_confirm_assets.png",
                                           take_screenshot=True)
                        auto.mouse_click_blank(times=3)
                        continue
                    else:
                        auto.mouse_click_blank(times=2)
                        sleep(1)

            if self.second_system and self.second_system_action[1]:
                if self.second_system_setting == 1 or (self.second_system_setting == 0 and self.fuse_IV is True):
                    system_gift = auto.find_element(f"mirror/shop/enhance_gifts/shop_{self.second_system_select}.png",
                                                    find_type='image_with_multiple_targets', threshold=0.85)
                    for gift in system_gift:
                        auto.mouse_click(gift[0], gift[1])
                        sleep(1)
                        while auto.take_screenshot() is None:
                            continue
                        if self.system == 'bleed':
                            if cfg.language_in_game == 'en':
                                if auto.find_text_element(["white", "gossypium"], all_text=True):
                                    auto.mouse_click_blank(times=2)
                            elif cfg.language_in_game == 'zh_cn':
                                if auto.find_text_element("白棉花"):
                                    auto.mouse_click_blank(times=2)
                            sleep(1)
                        if auto.click_element("mirror/shop/purchase_assets.png", take_screenshot=True):
                            sleep(1)
                            auto.click_element("mirror/road_in_mir/ego_gift_get_confirm_assets.png",
                                               take_screenshot=True)
                            auto.mouse_click_blank(times=3)
                            continue
                        else:
                            auto.mouse_click_blank(times=2)
                            sleep(1)

            if retry() is False:
                raise self.RestartGame()
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
                    if retry() is False:
                        raise self.RestartGame()
                    if self.skill_replacement and self.replacement is False:
                        self.replacement_skill()
                    continue

            if refresh_keyword is False:
                auto.mouse_click_blank(times=3)
                if auto.click_element("mirror/shop/refresh_keyword_assets.png"):
                    sleep(1)
                    auto.click_element(f"mirror/shop/keyword/keyword_{self.system}.png", take_screenshot=True)
                    auto.click_element("mirror/shop/refresh_keyword_confirm_assets.png")
                    refresh_keyword = True
                    auto.mouse_click_blank()
                    sleep(3)
                    if retry() is False:
                        raise self.RestartGame()
                    if self.skill_replacement and self.replacement is False:
                        self.replacement_skill()
                    continue

            break

    def fuse_useless_gifts_aggressive(self):
        """合成无用饰品_激进版"""

        scale = cfg.set_win_size / 1440

        def processing_coordinates(my_gift_list, coordinates, threshold=50):
            """将需要保护的坐标移除出列表"""
            for position in my_gift_list:
                if abs(position[0] - coordinates[0]) <= threshold * scale and abs(
                        position[1] - coordinates[1]) <= threshold * scale:
                    my_gift_list.pop(my_gift_list.index(position))

            return my_gift_list

        if auto.find_element(f"mirror/shop/level_IV_gifts/{self.system}_level_IV.png", take_screenshot=True):
            self.after_fuse_IV()
            if self.fuse_aggressive_switch is False:
                log.INFO("已有本体系四级饰品，切换到非激进模式")
                return

        if auto.find_element(f"mirror/shop/level_IV_gifts/{self.second_system_select}_level_IV.png", take_screenshot=True):
            if self.fuse_IV is True:
                self.fuse_switch = False
                self.fuse_aggressive_switch = False
                self.fuse_second_IV = True
                log.INFO("已有本体系、第二体系的四级饰品，切换到出售模式")
                return

        log.DEBUG("开始执行激进合成模块")
        while True:
            auto.mouse_to_blank()
            if auto.take_screenshot() is None:
                continue

            fuse = False
            gift_list = []

            gift = auto.find_element("mirror/shop/fuse_markers_assets.png")
            if gift:
                first_gift = [gift[0] + 135 * scale, gift[1] + 200 * scale]
                if self.the_first_line_position is None:
                    self.the_first_line_position = first_gift[1] + 100 * scale
                for i in range(10):
                    gift_list.append([first_gift[0] + 200 * (i % 5) * scale, first_gift[1] + 200 * (i // 5) * scale])
            else:
                return

            protect_list = ["mirror/shop/level_IV_gifts/lunar_memory.png",
                            f"mirror/shop/level_IV_gifts/{self.system}_level_IV.png"]
            if self.second_system and self.second_system_action[0]:
                protect_list.append(f"mirror/shop/level_IV_gifts/{self.second_system_select}_level_IV.png")

            for protect_gift in protect_list:
                if protect_coordinates := auto.find_element(protect_gift,threshold=0.7):
                    gift_list = processing_coordinates(gift_list, protect_coordinates)

            # 直到合成概率90%
            for coord in gift_list:
                auto.mouse_click(coord[0], coord[1])
                if auto.find_element("mirror/shop/fuse_90%_assets.png", threshold=0.97, take_screenshot=True):
                    break

            # 如果无法合成四级，或可用饰品不足三个，则退出此次合成
            if not auto.find_element("mirror/shop/fuse_90%_assets.png", take_screenshot=True):
                return
            if not auto.find_element("mirror/shop/fusion_level_IV_gift_assets.png", threshold=0.9):
                return

            loop_times = 15
            fuse_use_starlight_chance = 5
            while True:
                auto.mouse_to_blank()
                if auto.take_screenshot() is None:
                    continue

                if ego_gift_get_confirm := auto.find_element("mirror/road_in_mir/ego_gift_get_confirm_assets.png"):
                    if cfg.language_in_game == "zh_cn":
                        excluded_names = ["残片", "罪孽"]
                    else:
                        excluded_names = ["fragment", "corrosion", "resources"]
                    if auto.find_element(excluded_names, find_type="text"):
                        fuse = True
                    else:
                        if cfg.language_in_game == "zh_cn":
                            system_name = system_cn_zh[self.system]
                        else:
                            system_name = self.system
                        if auto.find_element(system_name, find_type="text"):
                            self.after_fuse_IV()
                            fuse = False
                    auto.mouse_click(ego_gift_get_confirm[0], ego_gift_get_confirm[1])
                    sleep(0.5)
                    auto.click_element("mirror/road_in_mir/ego_gift_get_confirm_assets.png", take_screenshot=True)
                    break

                if fuse_use_starlight_chance > 0 and auto.click_element("mirror/shop/fuse_use_starlight_assets.png"):
                    fuse_use_starlight_chance -= 1
                    auto.click_element("mirror/shop/fuse_use_starlight_confirm_assets.png", model="normal",
                                       take_screenshot=True)
                    continue

                if auto.click_element("mirror/shop/enhance_and_fuse_and_sell_confirm_assets.png", model="normal"):
                    sleep(2)
                    if loop_times <= 0:
                        break
                    loop_times -= 1
                    continue

                if retry() is False:
                    raise self.RestartGame()

            if fuse:
                sleep(2)
                auto.click_element("mirror/shop/fuse_ego_gift_assets.png", take_screenshot=True)
                continue

            break

        if retry() is False:
            raise self.RestartGame()

    def fuse_useless_gifts(self):
        """合成无用饰品"""
        scale = cfg.set_win_size / 1440

        def protect_coordinates(my_gift_list, coordinates, threshold=50):
            """将需要保护的坐标移除出列表"""
            for position in my_gift_list:
                if abs(position[0] - 50 - coordinates[0]) <= threshold * scale and abs(
                        position[1] - 50 - coordinates[1]) <= threshold * scale:
                    my_gift_list.pop(my_gift_list.index(position))

            return my_gift_list

        def processing_coordinates(my_gift_list):
            """将列表从左上到右下排序，然后去重"""

            # 排序
            sorted_list = sorted(my_gift_list, key=lambda x: (x[1], x[0]))

            # 去除重复坐标
            unique_list = []
            for coord in sorted_list:
                if not any(abs(coord[0] - x[0]) <= 40 * scale and
                           abs(coord[1] - x[1]) <= 40 * scale for x in unique_list):
                    unique_list.append(coord)

            # 如果激活激进模式，则过滤第一行的饰品
            if self.fuse_aggressive_switch:
                unique_list = [items for items in unique_list if items[1] >= self.the_first_line_position]

            return unique_list

        log.DEBUG("开始执行普通合成模块")
        block = True
        while True:
            auto.mouse_to_blank()
            if auto.take_screenshot() is None:
                continue

            fuse = False
            select_gifts = False
            gift_list = []

            # 获取无用饰品列表
            for commodity in must_be_abandoned:
                item = auto.find_element(commodity, find_type="image_with_multiple_targets")
                if "white_gossypium" in commodity and "bleed" in self.shop_sell_list:
                    continue
                if item:
                    if isinstance(item, list):
                        gift_list.extend(list(g) for g in item)
                    elif isinstance(item, tuple):
                        gift_list.append(item)
            for sell_system in self.shop_sell_list:
                my_sell_system = f"mirror/shop/enhance_gifts/{sell_system}.png"
                gift = auto.find_element(my_sell_system, find_type="image_with_multiple_targets")
                if gift:
                    if isinstance(gift, list):
                        gift_list.extend(list(g) for g in gift)
                    elif isinstance(gift, tuple):
                        gift_list.append(gift)
            # 对饰品位置列表进行排序、去重处理
            my_list = processing_coordinates(gift_list)

            if self.second_system and self.second_system_action[0]:
                if protect_gift := auto.find_element(
                        f"mirror/shop/level_IV_gifts/{self.second_system_select}_level_IV.png"):
                    my_list = protect_coordinates(my_list, protect_gift)

            # 选择3样无用饰品，不足则退出合成
            if len(my_list) <= 2:
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
                    auto.mouse_to_blank()
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
                            if cfg.language_in_game == "zh_cn":
                                excluded_names = ["残片", "罪孽"]
                            else:
                                excluded_names = ["fragment", "corrosion", "resources"]
                            if auto.find_element(excluded_names, find_type="text"):
                                pass
                            else:
                                if cfg.language_in_game == "zh_cn":
                                    system_name = system_cn_zh[self.system]
                                else:
                                    system_name = self.system
                                if auto.find_element(system_name, find_type="text"):
                                    self.fuse_IV = True
                                    self.fuse_aggressive_switch = False
                                    log.INFO("合成四级，切换到非激进模式")
                            fuse = True
                            auto.click_element("mirror/road_in_mir/ego_gift_get_confirm_assets.png")
                            sleep(1)
                            auto.click_element("mirror/road_in_mir/ego_gift_get_confirm_assets.png",
                                               take_screenshot=True)
                            break
                        else:
                            if auto.click_element("mirror/road_in_mir/ego_gift_get_confirm_assets.png"):
                                fuse = True
                                sleep(1)
                                auto.click_element("mirror/road_in_mir/ego_gift_get_confirm_assets.png",
                                                   take_screenshot=True)
                                break

                    if auto.click_element("mirror/shop/enhance_and_fuse_and_sell_confirm_assets.png", model="normal"):
                        continue

                    if auto.click_element("mirror/shop/fuse_ego_gift_assets.png"):
                        continue

                    if retry() is False:
                        raise self.RestartGame()

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

        if retry() is False:
            raise self.RestartGame()

    def fuse_system_gifts(self, times):
        """合成体系饰品"""
        loop_count = 30
        auto.model = 'clam'

        log.DEBUG("开始执行体系饰品合成模块")
        # 获取合成公式
        system_gifts = fusion_material[self.system]
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

        elif times == 1 and self.fuse_system_gift_2:
            return

        self.enter_fuse()

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

            if retry() is False:
                raise self.RestartGame()

            loop_count -= 1
            if loop_count < 20:
                auto.model = "normal"
            if loop_count < 10:
                auto.model = 'aggressive'
            if loop_count < 0:
                log.ERROR("无法合成ego饰品")
                break

        if fusion:
            msg = f"成功合成{self.system}体系饰品{times + 1}号"
            if times == 0:
                self.fuse_system_gift_1 = True
            else:
                self.fuse_system_gift_2 = True
            log.DEBUG(msg)
        else:
            msg = f"无法合成{self.system}体系饰品{times + 1}号"
            log.DEBUG(msg)

        auto.mouse_click_blank(times=3)

    def sell_gifts(self):
        scale = cfg.set_win_size / 1440

        def protect_coordinates(my_gift, coordinates, threshold=50):
            """将需要保护的坐标移除出列表"""
            if abs(my_gift[0] - coordinates[0]) <= threshold * scale and abs(
                    my_gift[1] - coordinates[1]) <= threshold * scale:
                return True

            return False

        list_block = False
        system_sell = True
        second = None
        log.DEBUG("开始执行饰品出售模块")
        while True:
            # 自动截图
            if auto.take_screenshot() is None:
                continue

            gift_sell = False

            if self.second_system and self.second_system_action[0] and second is None:
                if protect_gift := auto.find_element(
                        f"mirror/shop/level_IV_gifts/{self.second_system_select}_level_IV.png"):
                    second = protect_gift

            if auto.click_element("mirror/shop/sell_gift_assets.png"):
                continue

            if auto.click_element("mirror/shop/sell_gift_confirm_assets.png"):
                sleep(1)
                continue

            if system_sell:
                for sell_system in self.shop_sell_list:
                    my_sell_system = f"mirror/shop/enhance_gifts/{sell_system}.png"
                    if sell_gift := auto.find_element(my_sell_system):
                        if second is not None and protect_coordinates(sell_gift, second):
                            continue
                        else:
                            auto.mouse_click(sell_gift[0], sell_gift[1])
                            sleep(cfg.mouse_action_interval)
                        auto.click_element("mirror/shop/enhance_and_fuse_and_sell_confirm_assets.png", model='normal')
                        sleep(1)
                        if retry() is False:
                            raise self.RestartGame()
                        gift_sell = True
                        break

            if gift_sell:
                continue

            if list_block is False and auto.find_element("mirror/shop/gifts_list_block.png"):
                block_position = auto.find_element("mirror/shop/gifts_list_block.png")
                auto.mouse_drag(block_position[0], block_position[1], drag_time=1, dy=500)
                list_block = True
                second = None
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

    def enter_fuse(self):
        loop_count = 15
        auto.model = 'clam'
        auto.mouse_to_blank()
        log.DEBUG("开始执行饰品合成前置模块")
        while True:
            if auto.take_screenshot() is None:
                continue

            if self.fuse_IV is True and self.second_system is True and self.fuse_second_IV is False and \
                    self.second_system_action[0] is True and self.fuse_aggressive_switch is True:
                if auto.click_element(f"mirror/shop/keyword/keyword_{self.second_system_select}.png"):
                    while auto.take_screenshot() is None:
                        continue
                    if auto.click_element("mirror/shop/fuse_gift_confirm_assets.png", model="normal"):
                        break
            else:
                if auto.click_element(f"mirror/shop/keyword/keyword_{self.system}.png"):
                    while auto.take_screenshot() is None:
                        continue
                    if auto.click_element("mirror/shop/fuse_gift_confirm_assets.png", model="normal"):
                        break
            if auto.click_element("mirror/shop/fuse_to_select_keyword_assets.png"):
                continue

            loop_count -= 1
            if loop_count < 10:
                auto.model = "normal"
            if loop_count < 5:
                auto.model = 'aggressive'
            if loop_count < 0:
                log.ERROR("无法合成ego饰品")
                return False

            # 进入合成页面
            if auto.click_element("mirror/shop/fuse_gift_assets.png"):
                continue

        return True

    def fuse_gift(self):
        # 激进合成
        if self.fuse_aggressive_switch and not self.only_system_fuse:
            if self.enter_fuse() is False:
                return False
            self.fuse_useless_gifts_aggressive()
            auto.mouse_click_blank(times=3)
        if self.fuse_switch is False:
            return
        # 普通合成
        if self.only_aggressive_fuse or self.only_system_fuse:
            pass
        else:
            if self.enter_fuse() is False:
                return False
            self.fuse_useless_gifts()
            auto.mouse_click_blank(times=3)

        # 再次激进合成
        if self.fuse_aggressive_switch and self.fuse_IV is not True and not self.only_system_fuse:
            if self.enter_fuse() is False:
                return False
            self.fuse_useless_gifts_aggressive()
            auto.mouse_click_blank(times=3)
        if self.fuse_switch is False:
            return
        # 合成体系饰品
        if not self.only_aggressive_fuse and not self.do_not_system_fuse:
            if self.system not in fusion_material:
                fuse_times = 0
            else:
                fuse_times = 2
            for i in range(fuse_times):
                self.fuse_system_gifts(i)
                auto.mouse_click_blank(times=3)

    @staticmethod
    def heal_sinner():
        # 全体治疗
        loop_count = 5
        auto.model = 'clam'
        log.DEBUG("开始执行罪人治疗模块")
        sinner_be_heal = False
        while True:
            # 自动截图
            if auto.take_screenshot() is None:
                continue

            if sinner_be_heal is True and auto.click_element("mirror/shop/heal_sinner/heal_sinner_return_assets.png"):
                if auto.find_element('mirror/shop/shop_coins_assets.png', take_screenshot=True):
                    break
                elif auto.find_element('mirror/shop/heal_sinner/heal_sinner_return_assets.png'):
                    continue
                elif auto.find_element('mirror/shop/heal_sinner/heal_sinner_return_assets.png'):
                    continue

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

    def enhance_gifts(self):
        def check_enhanced(pos):
            for p in self.enhance_gifts_list:
                if abs(pos[0] - p[0]) <= 10 and abs(pos[1] - p[1]) <= 10:
                    return True
            return False

        log.DEBUG("开始执行饰品升级模块")

        while True:
            loop_try_count = 10
            # 自动截图
            if auto.take_screenshot() is None:
                continue
            if auto.click_element("mirror/shop/enhance_gifts_assets.png"):
                sleep(1)
                break
            auto.mouse_click_blank()
            loop_try_count -= 1
            if loop_try_count < 0:  # issue 171
                if retry() is False:
                    raise self.RestartGame()

            if loop_try_count < -50:
                log.ERROR("不应该发生这样的问题，请提交issue")

        list_block = False
        loop_count = 30
        auto.model = 'clam'
        system_level_IV = False
        second_system_level_IV = False
        while True:
            # 自动截图
            if auto.take_screenshot() is None:
                continue

            next_gift = True

            # 升级本体系四级
            if not system_level_IV:
                if level_IV := auto.find_element(f"mirror/shop/level_IV_gifts/{self.system}_level_IV.png"):
                    if check_enhanced(level_IV) is False:
                        auto.mouse_click(level_IV[0], level_IV[1])
                        if self.ego_gift_to_power_up() is False:
                            break
                        else:
                            self.enhance_gifts_list.append(level_IV)
                    system_level_IV = True
                    continue

            # 升级第二体系四级
            if self.second_system and self.second_system_action[3] and second_system_level_IV is False:
                if self.second_system_setting == 1 or (self.second_system_setting == 0 and self.fuse_IV is True):
                    if level_IV_2 := auto.find_element(
                            f"mirror/shop/level_IV_gifts/{self.second_system_select}_level_IV.png"):
                        if check_enhanced(level_IV_2) is False:
                            auto.mouse_click(level_IV_2[0], level_IV_2[1])
                            if self.ego_gift_to_power_up() is False:
                                break
                            else:
                                self.enhance_gifts_list.append(level_IV_2)
                        second_system_level_IV = True
                        continue

            if self.first_gift_enhance is False and system_level_IV is False:
                if f_gift := auto.find_element(f"mirror/shop/enhance_gifts/big_{self.system}.png"):
                    if self.ego_gift_to_power_up() is False:
                        break
                    else:
                        self.enhance_gifts_list.append(f_gift)
                        self.first_gift_enhance = True
                        continue

            if gifts := auto.find_element(f"mirror/shop/enhance_gifts/{self.system}.png",
                                          find_type="image_with_multiple_targets"):
                gifts = sorted(gifts, key=lambda x: (x[1], x[0]))
                for gift in gifts:
                    if check_enhanced(gift) is False:
                        auto.mouse_click(gift[0], gift[1])
                        if self.ego_gift_to_power_up() is False:
                            next_gift = False
                            break
                        else:
                            self.enhance_gifts_list.append(gift)
                    else:
                        continue
                    next_gift = False

            # if list_block is False and auto.find_element("mirror/shop/gifts_list_block.png"):
            #     block_position = auto.find_element("mirror/shop/gifts_list_block.png")
            #     auto.mouse_drag(block_position[0], block_position[1], drag_time=1, dy=500)
            #     list_block = True
            #     continue

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

        if retry() is False:
            raise self.RestartGame()

    def after_fuse_IV(self):
        self.fuse_IV = True
        if self.after_level_IV:
            if self.after_level_IV_select == 0:
                self.fuse_switch = False
                self.fuse_aggressive_switch = False
                log.INFO("合成四级，切换到出售模式")
            elif self.after_level_IV_select == 1:
                self.fuse_aggressive_switch = False
                log.INFO("合成四级，切换到非激进模式")
            elif self.after_level_IV_select == 2 and self.second_system is True and self.fuse_second_IV is False and \
                    self.second_system_action[0] is True:
                self.fuse_aggressive_switch = True
                log.DEBUG("合成四级，切换到第二体系四级合成")
            elif self.after_level_IV_select == 3:
                log.INFO("合成四级，跳过之后商店")
                for i in range(5):
                    self.ignore_shop[i] = True
            else:
                self.fuse_switch = False
                self.fuse_aggressive_switch = False
                log.INFO("合成四级但设置出错，切换到出售模式")
            return
        self.fuse_aggressive_switch = False
        log.INFO("合成四级，切换到非激进模式")

    def replacement_skill(self):
        if module_position := auto.find_element("mirror/shop/skill_replacement_assets.png", take_screenshot=True):
            my_scale = cfg.set_win_size / 1440
            bbox = (
                module_position[0] - 150 * my_scale, module_position[1] + 20 * my_scale,
                module_position[0] + 150 * my_scale,
                module_position[1] + 100 * my_scale)
            if self.skill_replacement_select == 0:
                sinner_nums = 1
            elif self.skill_replacement_select == 1:
                sinner_nums = 3
            elif self.skill_replacement_select == 2:
                sinner_nums = 7
            else:
                sinner_nums = 12
            if cfg.language_in_game == 'en':
                sinner = [
                    all_sinners_name[self.sinner_team.index(i + 1)]
                    for i in range(sinner_nums)
                    if (i + 1) in self.sinner_team
                ]
            else:
                sinner = [
                    all_sinners_name_zh[self.sinner_team.index(i + 1)]
                    for i in range(sinner_nums)
                    if (i + 1) in self.sinner_team
                ]
            if auto.find_text_element(sinner, my_crop=bbox):
                auto.mouse_click(module_position[0], module_position[1] - 100 * my_scale)
                sleep(0.5)
                coins = auto.find_element(f"mirror/shop/skill_replacement_coins.png",
                                          find_type="image_with_multiple_targets", take_screenshot=True)
                if len(coins) != 3:
                    self.replacement = True
                    return
                coins = sorted(coins, key=lambda x: x[0])
                select_mode = 3 - self.skill_replacement_mode - 1
                auto.mouse_click(coins[select_mode][0], coins[select_mode][1])
                sleep(0.5)
                auto.click_element("mirror/shop/skill_replacement_confirm_assets.png")
                auto.click_element("mirror/shop/skill_replacement_confirm_assets.png")
                if retry() is False:
                    raise self.RestartGame()
                self.replacement = True

    # 在商店的处理
    def in_shop(self, layer):
        heal = False
        sell = False
        buy = False
        fuse = False
        enhance = False
        skill = False
        try:
            while True:
                # 忽略楼层商店的情况
                if layer <= 5 and self.ignore_shop[layer - 1]:
                    break

                # 自动截图
                if auto.take_screenshot() is None:
                    continue

                auto.mouse_click_blank(times=3)
                sleep(1)

                if self.skill_replacement and skill is False:
                    self.replacement = False
                    self.replacement_skill()
                    skill = True
                    continue

                if heal is False:
                    if self.do_not_heal:
                        heal = True
                    else:
                        self.heal_sinner()
                        heal = True
                        continue

                if sell is False:
                    if self.do_not_sell:
                        sell = True
                    else:
                        # 出售无用饰品
                        if self.fuse_switch is False:
                            self.sell_gifts()
                        sell = True
                        continue

                if buy is False:
                    if self.do_not_buy:
                        buy = True
                    else:
                        self.buy_gifts()
                        buy = True
                        continue

                if fuse is False:
                    if self.do_not_fuse:
                        fuse = True
                    else:
                        # 合成饰品
                        if self.fuse_switch:
                            self.fuse_gift()
                        fuse = True
                        continue

                if enhance is False:
                    if self.do_not_enhance:
                        enhance = True
                    elif self.fuse_aggressive_switch and self.aggressive_also_enhance is False:
                        enhance = True
                    else:
                        # 升级体系ego饰品
                        self.enhance_gifts()
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

                if retry() is False:
                    raise self.RestartGame()
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
        except self.RestartGame:
            log.ERROR("执行商店操作期间出现错误，尝试重启游戏")
            return
