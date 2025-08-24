import time
from time import sleep

import cv2
import numpy as np
import pyautogui

from module.automation import auto
from module.config import cfg
from module.decorator.decorator import begin_and_finish_time_log
from module.logger import log
from module.my_error.my_error import unableToFindTeamError
from module.ocr import ocr
from tasks import all_systems, start_gift
from tasks.base.back_init_menu import back_init_menu
from tasks.base.make_enkephalin_module import make_enkephalin_module
from tasks.base.retry import retry
from tasks.battle import battle
from tasks.event.event_handling import EventHandling
from tasks.mirror.in_shop import Shop
from tasks.mirror.reward_card import get_reward_card
from tasks.mirror.search_road import search_road_default_distance, search_road_farthest_distance
from tasks.mirror.select_theme_pack import select_theme_pack
from tasks.teams.team_formation import team_formation, select_battle_team, check_team
from utils.image_utils import ImageUtils


# 输出时间统计
def to_log_with_time(msg, elapsed_time):
    # 将总秒数转换为小时、分钟和秒
    hours, remainder = divmod(elapsed_time, 3600)
    minutes, seconds = divmod(remainder, 60)
    time_string = f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"
    log.INFO(f"{msg} 总耗时:{time_string}")


class Mirror:

    def __init__(self, team_setting: dict):
        self.logger = log
        self.sinner_team = team_setting["sinner_order"]  # 选择的罪人序列
        self.team_number = team_setting["team_number"]  # 选择的编队名
        self.shop = Shop(team_setting)
        self.system = all_systems[team_setting["team_system"]]  # 选择的体系
        self.avoid_skill_3 = team_setting["avoid_skill_3"]  # 是否避免使用3技能
        # 自选开局星光
        self.choose_opening_bonus = team_setting["choose_opening_bonus"]
        self.opening_bonus_order = team_setting["opening_bonus_order"]
        self.use_starlight = team_setting["use_starlight"]
        # 自选奖励卡优先度
        self.reward_cards = team_setting["reward_cards"]
        self.reward_cards_select = team_setting["reward_cards_select"]
        # 自选开局饰品
        self.opening_items = team_setting["opening_items"]
        self.opening_items_select = team_setting["opening_items_select"]
        self.opening_items_system = team_setting["opening_items_system"]
        self.re_formation_each_floor = team_setting["re_formation_each_floor"]  # 是否每层重新配队
        # 第二体系
        self.second_system = team_setting["second_system"]  # 启用第二体系
        self.second_system_select = team_setting["second_system_select"]  # 选择的第二体系
        self.second_system_setting = team_setting["second_system_setting"]  # 第二体系策略

        self.start_time = time.time()
        self.first_battle = True  # 判断是否首次进入战斗，如果是则重新配队
        self.hard_switch = cfg.hard_mirror
        # 统计时间
        self.find_road_total_time = 0
        self.battle_total_time = 0
        self.shop_total_time = 0
        self.event_total_time = 0
        self.event_times = 0

        self.flood = 0
        self.get_flood_num = True
        self.flood_times = [time.time() for i in range(5)]
        self.LOOP_COUNT = 250

        self.bequest_from_the_previous_game = False

    def road_to_mir(self):
        loop_count = 30
        auto.model = 'clam'
        self.first_battle = True
        while True:
            # 自动截图
            if auto.take_screenshot() is None:
                continue
            auto.mouse_to_blank()
            if auto.find_element("mirror/claim_reward/clear_assets.png"):
                self.bequest_from_the_previous_game = True
                return True
            if auto.find_element("mirror/road_in_mir/legend_assets.png"):
                break
            if auto.click_element("mirror/road_to_mir/resume_assets.png"):
                break
            if auto.click_element("mirror/road_to_mir/enter_mirror_assets.png",threshold=0.78):
                break
            infinity_bbox = ImageUtils.get_bbox(ImageUtils.load_image("mirror/road_to_mir/infinity_mirror_bbox.png"))
            infinity_bbox = (
                infinity_bbox[2] - 50, infinity_bbox[1], infinity_bbox[2] + 100, infinity_bbox[3])  # 临时修复措施，调整裁切大小
            if auto.find_text_element("on", infinity_bbox):
                auto.click_element("mirror/road_to_mir/infinity_mirror_enter_assets.png")
            if auto.click_element("mirror/road_to_mir/enter_assets.png"):
                sleep(0.5)
                continue
            if auto.click_element("home/mirror_dungeons_assets.png"):
                continue
            if auto.click_element("home/drive_assets.png", model="normal"):
                continue
            if auto.find_element("mirror/road_to_mir/select_team_stars_assets.png"):
                break
            if auto.find_element("mirror/road_to_mir/dreaming_star/coins_assets.png"):
                # 防止卡在星光选择
                break
            if retry() is False:
                return False
            loop_count -= 1
            if loop_count < 20:
                auto.model = "normal"
            if loop_count < 10:
                auto.model = 'aggressive'
            if loop_count < 0:
                log.ERROR("无法进入镜牢,尝试回到初始界面")
                back_init_menu()
                break

    def run(self):
        # 计时开始
        start_time = time.time()

        if auto.click_element("home/drive_assets.png") or auto.find_element("home/window_assets.png"):
            make_enkephalin_module()

        main_loop_count = self.LOOP_COUNT
        back_menu_count = 0
        # 未到达奖励页不会停止
        while True:
            if main_loop_count >= 50:
                auto.model = "clam"  # 防止函数内修改后未还原
            # 自动截图
            if auto.take_screenshot() is None:
                continue

            if cfg.flood_3_exit and self.flood >= 4:
                if auto.click_element("mirror/road_in_mir/towindow&forfeit_confirm_assets.png"):
                    break
                if auto.click_element("mirror/road_in_mir/forfeit_assets.png"):
                    continue
                if auto.click_element("mirror/road_in_mir/setting_assets.png"):
                    continue

            # 镜牢结束领取奖励
            if auto.find_element("mirror/claim_reward/battle_statistics_assets.png"):
                if auto.click_element("mirror/claim_reward/claim_rewards_assets.png") is False:
                    claim_rewards_bbox = ImageUtils.get_bbox(
                        ImageUtils.load_image("mirror/claim_reward/claim_rewards_assets.png"))
                    auto.mouse_click((claim_rewards_bbox[0] + claim_rewards_bbox[2]) / 2,
                                     (claim_rewards_bbox[1] + claim_rewards_bbox[3]) / 2)
                break
            if auto.find_element("mirror/claim_reward/claim_rewards_assets.png") and auto.find_element(
                    "mirror/claim_reward/complete_mirror_100%_assets.png"):
                break
            if auto.find_element("mirror/claim_reward/use_enkephalin_assets.png", threshold=0.9, model='clam'):
                break

            # 选择楼层主题包的情况
            if auto.find_element("mirror/theme_pack/feature_theme_pack_assets.png"):
                sleep(2)
                select_theme_pack(self.hard_switch, self.flood)
                if self.re_formation_each_floor:
                    self.first_battle = True
                flood_num = self.flood # 0,1,2,3,4
                if flood_num != 0:
                    flood_time = time.time() - self.flood_times[flood_num - 1]
                    msg = f"启动后第{self.flood}层卡包"
                    to_log_with_time(msg, flood_time)
                self.flood_times[flood_num] = time.time()
                self.get_flood_num = True
                main_loop_count += 50
                continue

            # 遇到选择增益事件（少见）
            if auto.click_element("mirror/road_in_mir/event_effect_button.png", threshold=0.75):
                auto.click_element("mirror/road_in_mir/select_event_effect_confirm.png")
                continue

            # 在镜牢中寻路
            if auto.find_element("mirror/road_in_mir/legend_assets.png"):
                auto.mouse_to_blank()
                while auto.take_screenshot() is None:
                    continue
                if auto.click_element("mirror/road_in_mir/ego_gift_get_confirm_assets.png"):
                    continue
                if auto.find_element("teams/announcer_assets.png"):
                    continue
                if auto.find_element('mirror/shop/shop_coins_assets.png', model='normal'):
                    continue
                if auto.find_element("mirror/claim_reward/claim_rewards_assets.png") and auto.find_element(
                        "mirror/claim_reward/complete_mirror_100%_assets.png"):
                    break
                retry()
                if self.get_flood_num:
                    get_flood_bbox = ImageUtils.get_bbox(
                        ImageUtils.load_image("mirror/road_in_mir/get_flood_bbox.png"))
                    ocr_result = auto.find_text_element(None, my_crop=get_flood_bbox, only_text=True)
                    try:
                        if cfg.language_in_game == 'zh_cn':
                            result = ocr_result[-1].split("第")
                            flood = result[1][0]
                            flood = int(flood)
                            self.flood = flood
                            self.get_flood_num = False
                        elif cfg.language_in_game == 'en':
                            get_flood_bbox = ImageUtils.get_bbox(
                                ImageUtils.load_image("mirror/road_in_mir/get_flood_bbox.png"))
                            sc = ImageUtils.crop(np.array(auto.screenshot), get_flood_bbox)
                            mask = cv2.inRange(sc, 75, 255)
                            result = ocr.run(mask)
                            ocr_result = [item["text"] for item in result["data"]]
                            ocr_result = "".join(ocr_result)
                            result = ocr_result.split(" ")
                            flood = result[-1][0]
                            flood = int(flood)
                            self.flood = flood
                            self.get_flood_num = False
                    except:
                        log.DEBUG("获取楼层失败，将在下次寻路时重新尝试获取")
                while auto.take_screenshot() is None:
                    continue
                if auto.find_element("mirror/road_in_mir/legend_assets.png"):
                    self.find_road_total_time += self.search_road()
                continue

            # 进入节点
            if auto.click_element("mirror/road_in_mir/enter_assets.png"):
                continue

            # 选择镜牢队伍
            if auto.find_element("mirror/road_to_mir/select_team_stars_assets.png"):
                self.select_mirror_team()
                continue

            # 战斗配队的情况
            if auto.find_element("teams/announcer_assets.png"):
                # 如果第一次启动脚本，还没进行编队，就先编队
                if self.first_battle:
                    team_formation(self.sinner_team)
                    self.first_battle = False
                    continue
                # 检测罪人幸存人数是否少于10人
                if not (auto.find_element("teams/12_sinner_live_assets.png") or
                        auto.find_element("teams/11_sinner_live_assets.png") or
                        auto.find_element("teams/10_sinner_live_assets.png")):
                    continue_mirror = check_team()
                    # 如果还有至少5人能战斗就继续，不然就退出重开
                    if continue_mirror is False and self.first_battle is False:
                        self.re_start()
                if auto.click_element("battle/chaim_to_battle_assets.png") or auto.click_element(
                        "battle/normal_to_battle_assets.png"):
                    retry()
                    continue

            # 没有配队的情况
            if auto.find_element("battle/select_none_assets.png"):
                auto.mouse_click_blank()
                self.first_battle = True
                continue

            # 在战斗中
            if battle.identify_keyword_turn and self.LOOP_COUNT - main_loop_count < 5:
                if auto.find_element("battle/turn_assets.png") or auto.find_element("battle/in_mirror_assets.png"):
                    self.battle_total_time += battle.fight(self.avoid_skill_3)
                    continue
            else:
                turn_bbox = ImageUtils.get_bbox(ImageUtils.load_image("battle/turn_assets.png"))
                turn_ocr_result = auto.find_text_element("turn", turn_bbox)
                if turn_ocr_result is not False:
                    self.battle_total_time += battle.fight(self.avoid_skill_3)
                    continue

            # 镜牢星光
            if auto.find_element("mirror/road_to_mir/dreaming_star/coins_assets.png", threshold=0.9):
                self.enter_mir_with_star()
                continue

            # 如果遇到选择ego饰品的情况
            if auto.find_element("mirror/road_in_mir/acquire_ego_gift.png"):
                self.acquire_ego_gift()
                continue

            # 如果遇到获取ego饰品的情况
            if auto.click_element("mirror/road_in_mir/ego_gift_get_confirm_assets.png"):
                continue

            # 遇到事件
            if auto.click_element("/event/skip_assets.png", times=6):
                self.event_handling()
                continue

            # 商店事件
            if auto.find_element('mirror/shop/shop_coins_assets.png'):
                self.shop_total_time += self.in_shop()
                continue

            # 选择奖励卡
            if auto.find_element("mirror/road_in_mir/select_encounter_reward_card_assets.png"):
                if self.reward_cards:
                    get_reward_card(self.reward_cards_select)
                else:
                    get_reward_card()
                continue

            # 在主界面时，开始进入镜牢
            if auto.click_element("home/drive_assets.png") or auto.find_element("home/window_assets.png"):
                if self.road_to_mir() and self.bequest_from_the_previous_game:
                    break
                continue
            # 在镜牢界面，进入镜牢
            if auto.click_element("mirror/road_to_mir/enter_assets.png"):
                if self.road_to_mir() and self.bequest_from_the_previous_game:
                    break
                continue

            # 初始饰品选择
            if auto.find_element("mirror/road_to_mir/activate_gift_search_on_assets.png") or auto.find_element(
                    "mirror/road_to_mir/activate_gift_search_off_assets.png"):
                self.select_init_ego_gift()
                continue

            # 取消十层
            if auto.find_element("mirror/infinity_mirror_assets.png"):
                auto.click_element("mirror/infinity_mirror_close_assets.png")
                continue

            # 防卡死
            auto.mouse_click_blank()
            retry()
            main_loop_count -= 1
            if main_loop_count % 10 == 0:
                log.DEBUG(f"镜牢道中识别次数剩余{main_loop_count}次")
            if main_loop_count < 75:
                auto.model = "normal"
                log.DEBUG("识别模式切换到正常模式")
            if main_loop_count < 15:
                auto.model = 'aggressive'
                log.DEBUG("识别模式切换到激进模式，警告，道中识别可能会出错")
            if main_loop_count < 0:
                if back_menu_count > 5:
                    raise log.ERROR("镜牢道中出错,请手动操作重试")
                log.ERROR("镜牢道中识别失败次数达到最大值,正在返回主界面")
                back_init_menu()
                back_menu_count += 1
                main_loop_count = 250

        msg = f"开始进行镜牢奖励领取"
        log.INFO(msg)

        if self.bequest_from_the_previous_game:
            self.get_reward_in_road()
            return True

        main_loop_count = 20
        auto.model = 'clam'
        failed = None
        while True:
            # 自动截图
            if auto.take_screenshot() is None:
                auto.mouse_to_blank()
                continue
            if not auto.find_element(
                    "mirror/claim_reward/complete_mirror_100%_assets.png") and failed is None and cfg.flood_3_exit is False:
                failed = True
            if auto.find_element("mirror/claim_reward/complete_mirror_100%_assets.png"):
                failed = False
            # 如果回到主界面，退出循环
            if auto.find_element("home/drive_assets.png"):
                break
            if auto.click_element("base/battle_finish_confirm_assets.png"):
                continue
            if auto.click_element("mirror/claim_reward/rewards_acquired_assets.png"):
                continue
            if cfg.no_weekly_bonuses:
                bonuses = auto.find_element("mirror/claim_reward/weekly_bonuses.png",
                                            find_type='image_with_multiple_targets')
                if len(bonuses) >= 1:
                    for _ in range(len(bonuses)):
                        position = bonuses.pop(-1)
                        auto.mouse_click(position[0], position[1])
            if cfg.hard_mirror_single_bonuses:
                bonuses = auto.find_element("mirror/claim_reward/weekly_bonuses.png",
                                            find_type='image_with_multiple_targets')
                bonuses = sorted(bonuses, key=lambda x: x[0])
                if len(bonuses) > 1:
                    for _ in range(len(bonuses) - 1):
                        position = bonuses.pop(-1)
                        auto.mouse_click(position[0], position[1])
            if auto.click_element("mirror/claim_reward/claim_rewards_confirm_assets.png", threshold=0.75, model='clam'):
                continue
            if failed:
                if auto.click_element("mirror/claim_reward/claim_rewards_assets.png"):
                    sleep(1)
                if auto.click_element("mirror/claim_reward/claim_forfeit_assets.png",take_screenshot=True):
                    continue
            else:
                if self.hard_switch and cfg.save_rewards:
                    auto.click_element("mirror/claim_reward/claim_rewards_assets.png")
                    sleep(1)
                    pos = auto.find_element("mirror/claim_reward/use_enkephalin_assets.png", take_screenshot=True)
                    if pos:
                        auto.mouse_click(pos[0] - 300 * (cfg.set_win_size / 1440), pos[1])
                    continue
                elif auto.click_element("mirror/claim_reward/claim_rewards_assets.png"):
                    sleep(1)
                    # TODO: 统计获取的coins
                    continue
            if auto.click_element("mirror/claim_reward/use_enkephalin_assets.png", threshold=0.75):  # 降低识别阈值
                continue
            # 处理周年活动弹出的窗口
            if auto.click_element("home/close_anniversary_event_assets.png"):
                continue
            retry()
            main_loop_count -= 1
            if main_loop_count % 3 == 0:
                log.DEBUG(f"镜牢奖励识别次数剩余{main_loop_count}次")
            if main_loop_count < 10:
                auto.model = "normal"
                log.DEBUG("识别模式切换到正常模式")
            if main_loop_count < 5:
                auto.model = 'aggressive'
                log.DEBUG("识别模式切换到激进模式")
            if main_loop_count < 0:
                raise log.ERROR("镜牢奖励领取出错,请手动操作重试")

        if failed:
            return False
        # 计时结束
        end_time = time.time()
        elapsed_time = end_time - start_time

        last_flood_time = time.time() - self.flood_times[self.flood - 1]
        msg = f"启动后第{self.flood}层卡包"
        to_log_with_time(msg, last_flood_time)

        # 输出战斗总时间
        msg = f"此次镜牢在战斗"
        to_log_with_time(msg, self.battle_total_time)

        # 输出事件总时间
        msg = f"此次镜牢走的事件次数{self.event_times}"
        log.INFO(msg)
        # 输出事件总时间
        msg = f"此次镜牢在事件"
        to_log_with_time(msg, self.event_total_time)

        # 输出商店总时间
        msg = f"此次镜牢中在商店"
        to_log_with_time(msg, self.shop_total_time)

        # 输出寻路总时间
        msg = f"此次镜牢中在寻路"
        to_log_with_time(msg, self.find_road_total_time)

        # debug输出时间
        log.DEBUG(
            f"战斗时间:{self.battle_total_time} 事件时间:{self.event_total_time} 商店时间:{self.shop_total_time} 寻路时间:{self.find_road_total_time} 总时间:{elapsed_time}")

        # 输出镜牢总时间
        msg = f"此次镜牢使用{self.system}体系队伍"
        to_log_with_time(msg, elapsed_time)

        return True

    def enter_mir_with_star(self):
        coins = auto.find_element("mirror/road_to_mir/dreaming_star/coins_assets.png", threshold=0.9)
        scale = cfg.set_win_size / 1440
        first_starlight = [coins[0] - 1800 * scale, coins[1] + 300 * scale]

        loop_count = 30
        auto.model = 'clam'
        while True:
            # 自动截图
            if auto.take_screenshot() is None:
                continue

            if auto.find_element("mirror/road_to_mir/bleed_gift_assets.png"):
                break

            if self.use_starlight and auto.click_element(
                    "mirror/road_to_mir/dreaming_star/convert_star_to_cost_assets.png"):
                continue

            if auto.click_element("mirror/road_to_mir/dreaming_star/select_star_confirm_assets.png", model="normal"):
                break

            if not self.choose_opening_bonus:
                for i in range(4):
                    auto.mouse_click(first_starlight[0] + 400 * i * scale, first_starlight[1])
                    sleep(cfg.mouse_action_interval)
            else:
                for i in range(1, 11):
                    if i in self.opening_bonus_order:
                        index = self.opening_bonus_order.index(i)
                        if index <= 4:
                            auto.mouse_click(first_starlight[0] + 400 * index * scale, first_starlight[1])
                        else:
                            auto.mouse_click(first_starlight[0] + 400 * (index - 5) * scale,
                                             first_starlight[1] + 450 * scale)
                        sleep(cfg.mouse_action_interval)

            if auto.click_element("mirror/road_to_mir/dreaming_star/dreaming_star_enter_assets.png"):
                sleep(0.5)
                continue

            if retry() is False:
                return False
            loop_count -= 1
            if loop_count % 5 == 0:
                log.DEBUG(f"进入镜牢识别次数剩余{loop_count}次")
            if loop_count < 20:
                auto.model = "normal"
                log.DEBUG("识别模式切换到正常模式")
            if loop_count < 10:
                auto.model = 'aggressive'
                log.DEBUG("识别模式切换到激进模式")
            if loop_count < 0:
                raise log.ERROR("无法进入镜牢，不能进行下一步,请手动操作重试")

    def select_init_ego_gift(self):
        scroll = False
        select_system = False
        loop_count = 30
        auto.model = 'clam'

        team_system = self.system
        if self.opening_items:
            team_system = all_systems[self.opening_items_system]
        log.DEBUG("开始选择初始EGO")
        while True:
            # 自动截图
            if auto.take_screenshot() is None:
                continue

            if auto.click_element("mirror/road_in_mir/ego_gift_get_confirm_assets.png"):
                auto.mouse_to_blank()
                continue

            if auto.click_element("mirror/road_to_mir/activate_gift_search_on_assets.png"):
                continue

            if auto.find_element("mirror/theme_pack/feature_theme_pack_assets.png"):
                break

            if team_system == "slash" or team_system == "pierce" or team_system == "blunt" and scroll == False:
                slash_button = auto.find_element("mirror/road_to_mir/slash_gift_model_assets.png")
                if slash_button is not None:
                    auto.mouse_drag(slash_button[0], slash_button[1], drag_time=0.2, dx=0, dy=-400)
                    sleep(0.5)
                    continue
                scroll = True

            if auto.click_element(f"mirror/road_to_mir/{team_system}_gift_assets.png") and select_system == False:
                select_system = True
                continue

            if self.opening_items:
                start_gift_order = start_gift[self.opening_items_select]
                auto.click_element(
                    f"mirror/road_to_mir/select_init_gift/{team_system}_ego_gift_{start_gift_order[0]}.png")
                auto.click_element(
                    f"mirror/road_to_mir/select_init_gift/{team_system}_ego_gift_{start_gift_order[1]}.png")
                auto.click_element(
                    f"mirror/road_to_mir/select_init_gift/{team_system}_ego_gift_{start_gift_order[2]}.png")
            else:
                auto.click_element(f"mirror/road_to_mir/select_init_gift/{team_system}_ego_gift_1.png")
                auto.click_element(f"mirror/road_to_mir/select_init_gift/{team_system}_ego_gift_2.png")
                auto.click_element(f"mirror/road_to_mir/select_init_gift/{team_system}_ego_gift_3.png")

            if auto.click_element("mirror/road_to_mir/select_init_ego_gifts_confirm_assets.png"):
                sleep(1)
                continue

            if retry() is False:
                return False
            loop_count -= 1
            if loop_count % 5 == 0:
                log.DEBUG(f"选择藏品识别次数剩余{loop_count}次")
            if loop_count < 20:
                auto.model = "normal"
                log.DEBUG("识别模式切换到正常模式")
            if loop_count < 10:
                auto.model = 'aggressive'
                log.DEBUG("识别模式切换到激进模式")
            if loop_count < 0:
                log.ERROR("无法进入镜牢,尝试回到初始界面")
                back_init_menu()
                break

    def select_mirror_team(self):
        chance_to_select_team = 5
        while not select_battle_team(self.team_number):
            chance_to_select_team -= 1
            if chance_to_select_team < 0:
                log.ERROR("无法寻得队伍")
                raise unableToFindTeamError("无法寻得队伍，请检查队伍名称是否为默认名称")
        loop_count = 30
        auto.model = 'clam'
        while auto.find_element("mirror/road_to_mir/dreaming_star/coins_assets.png") is None:
            if auto.take_screenshot() is None:
                continue
            if retry() is False:
                return False
            if auto.click_element("mirror/road_to_mir/level_confirm_assets.png"):
                continue
            if auto.click_element("mirror/road_to_mir/select_team_confirm_assets.png"):
                continue
            loop_count -= 1
            if loop_count % 5 == 0:
                log.DEBUG(f"选择队伍识别次数剩余{loop_count}次")
            if loop_count < 20:
                auto.model = "normal"
                log.DEBUG("识别模式切换到正常模式")
            if loop_count < 10:
                auto.model = 'aggressive'
                log.DEBUG("识别模式切换到激进模式")
            if loop_count < 0:
                log.ERROR("无法进入镜牢,尝试回到初始界面")
                back_init_menu()
                break
        time.sleep(3)

    @begin_and_finish_time_log(task_name="镜牢寻路")
    def search_road(self):
        try:
            for _ in range(3):
                while auto.take_screenshot() is None:
                    continue
                if search_road_default_distance():
                    sleep(1)
                    return True
                if retry() is False:
                    return False
            for _ in range(3):
                while auto.take_screenshot() is None:
                    continue
                if search_road_farthest_distance():
                    sleep(1)
                    return True
                if retry() is False:
                    return False
        except Exception as e:
            log.ERROR(f"寻路出错:{e}")
            return False
        while True:
            # 自动截图
            if auto.take_screenshot() is None:
                continue
            auto.mouse_to_blank()
            if auto.click_element("home/drive_assets.png") or auto.find_element("home/window_assets.png"):
                break
            if auto.click_element("mirror/road_in_mir/towindow&forfeit_confirm_assets.png"):
                break
            if auto.click_element("mirror/road_in_mir/to_window_assets.png"):
                continue
            if auto.click_element("mirror/road_in_mir/setting_assets.png"):
                sleep(1)
                continue
            if retry() is False:
                return False

    def re_start(self):
        while True:
            # 自动截图
            if auto.take_screenshot() is None:
                continue
            if auto.click_element("mirror/road_in_mir/towindow&forfeit_confirm_assets.png"):
                break
            if auto.click_element("mirror/road_in_mir/forfeit_assets.png"):
                continue
            if auto.click_element("mirror/road_in_mir/setting_assets.png"):
                continue
            pyautogui.press("esc")
            time.sleep(1)
            if retry() is False:
                return False
        # TODO耗时
        msg = f"满 身 疮 痍 ！ 重 开 ！此次战败耗时{time.time() - self.start_time}"
        log.INFO(msg)
        self.first_battle = True
        self.start_time = time.time()

    def event_handling(self):
        # 遇到有SKIP的情况
        event_start_time = time.time()
        loop_count = 30
        auto.model = 'clam'
        event_chance = 15
        while True:
            # 自动截图
            if auto.take_screenshot() is None:
                continue
                
            if retry() is False:
                return False


            # 如果在战斗中或回到镜牢路线图中，则跳出循环
            if auto.find_element("battle/turn_assets.png"):
                break
            if auto.find_element("mirror/road_in_mir/legend_assets.png"):
                break

            # 针对不同事件进行处理，优先选???与直接获取的，再选需要判定的，再选后续事件的，最后第一个事项
            if auto.click_element("event/unknown_event.png"):
                continue
            if positions_list := auto.find_element("event/select_to_gain_ego.png",
                                                   find_type="image_with_multiple_targets"):
                positions_list = sorted(positions_list, key=lambda x: (x[1], x[0]))
                auto.mouse_click(positions_list[0][0], positions_list[0][1])
                continue
            if auto.click_element("event/advantage_check.png"):
                continue
            if auto.click_element("event/gain_a_ego_depending_on_result.png"):
                continue
            if event_chance > 5:
                auto.click_element("event/select_first_option_assets.png")
                event_chance -= 1
            elif event_chance > 0:
                auto.click_element("event/select_first_option_assets.png", find_type="image_with_multiple_targets")
                event_chance -= 1
            else:
                finishes_bbox = ImageUtils.get_bbox(
                    ImageUtils.load_image("event/continue_assets.png"))
                if auto.find_text_element(
                        ["continue", "proceed", "commence", "choices", "confirm", "进行判定", "开始战斗", "继续"],
                        finishes_bbox):
                    auto.mouse_click((finishes_bbox[0] + finishes_bbox[2]) // 2,
                                     (finishes_bbox[1] + finishes_bbox[3]) // 2)
                    break
                else:
                    event_chance = -1

            # 如果需要罪人判定
            if auto.find_element("event/choices_assets.png") and auto.find_element(
                    "event/select_first_option_assets.png"):
                auto.click_element("event/select_first_option_assets.png")
            if auto.find_element("event/perform_the_check_feature_assets.png"):
                EventHandling.decision_event_handling()
            if auto.click_element("event/continue_assets.png"):
                continue
            if auto.click_element("event/proceed_assets.png"):
                continue
            if auto.click_element("event/commence_assets.png"):
                continue
            if auto.click_element("event/commence_battle_assets.png"):
                continue

            if auto.click_element("mirror/road_in_mir/ego_gift_get_confirm_assets.png"):
                continue
               

            if auto.click_element("event/skip_assets.png", times=6):
                continue

            if event_chance < 0:
                msg = "事件卡死，尝试返回主界面"
                log.ERROR(msg)
                back_init_menu()
                break
            loop_count -= 1
            if loop_count % 3 == 0:
                log.DEBUG(f"事件处理识别次数剩余{loop_count}次")
            if loop_count < 20:
                auto.model = "normal"
                log.DEBUG("识别模式切换到正常模式")
            if loop_count < 10:
                auto.model = 'aggressive'
                log.DEBUG("识别模式切换到激进模式")
            if loop_count < 0:
                log.ERROR("无法解决事件,尝试回到初始界面")
                back_init_menu()
                break

        # 统计事件处理时间
        event_end_time = time.time()
        event_elapsed_time = event_end_time - event_start_time
        self.event_total_time += event_elapsed_time
        self.event_times += 1

    def acquire_ego_gift(self):
        my_scale = cfg.set_win_size / 1440
        auto.model = 'clam'
        auto.mouse_to_blank()
        while True:
            if auto.take_screenshot() is None:
                continue

            if auto.click_element("mirror/road_in_mir/ego_gift_get_confirm_assets.png"):
                break
            try:
                acquire_button = auto.find_element("mirror/road_in_mir/acquire_ego_gift.png",
                                                   find_type='image_with_multiple_targets')
                my_list = []
                if len(acquire_button) == 2:
                    for button in acquire_button:
                        bbox = (button[0] - 350 * my_scale, button[1] - 50 * my_scale, button[0] + 150 * my_scale,
                                button[1] + 250 * my_scale)
                        if cfg.language_in_game == "zh_cn":
                            ocr_result = auto.find_text_element("白棉花", bbox)
                        else:
                            ocr_result = auto.find_text_element(["white", "gossypium"], bbox)
                        if isinstance(ocr_result, list):
                            if len(ocr_result) >= 2:
                                continue
                        auto.mouse_click(button[0], button[1])
                        auto.click_element("mirror/road_in_mir/acquire_ego_gift_select_assets.png", model="normal")
                        time.sleep(2)
                        if retry() is False:
                            return False
                        return
                elif len(acquire_button) == 1:
                    for button in acquire_button:
                        bbox = (button[0] - 350 * my_scale, button[1] - 50 * my_scale, button[0] + 150 * my_scale,
                                button[1] + 250 * my_scale)
                        if cfg.language_in_game == "zh_cn":
                            ocr_result = auto.find_text_element("白棉花", bbox)
                        else:
                            ocr_result = auto.find_text_element(["white", "gossypium"], bbox)
                        if isinstance(ocr_result, list):
                            if len(ocr_result) >= 2:
                                time.sleep(1)
                                auto.click_element("mirror/road_in_mir/refuse_gift_assets.png",
                                                   take_screenshot=True)
                                sleep(1)
                                auto.click_element("mirror/road_in_mir/refuse_gift_confirm_assets.png",
                                                   take_screenshot=True)
                                time.sleep(2)
                                if retry() is False:
                                    return False
                                return
                        auto.mouse_click(button[0], button[1])
                        auto.click_element("mirror/road_in_mir/acquire_ego_gift_select_assets.png", model="normal")
                        time.sleep(2)
                        if retry() is False:
                            return False
                        return
                else:
                    system_nums = 0
                    for button in acquire_button:
                        bbox = (button[0] - 350 * my_scale, button[1] - 50 * my_scale, button[0] + 150 * my_scale,
                                button[1] + 250 * my_scale)
                        if cfg.language_in_game == "zh_cn":
                            ocr_result = auto.find_text_element("白棉花", bbox)
                        else:
                            ocr_result = auto.find_text_element(["white", "gossypium"], bbox)
                        if ocr_result:
                            continue
                        if auto.find_element(f"mirror/road_in_mir/acquire_ego_gift/{self.system}.png", my_crop=bbox,
                                             threshold=0.85):
                            my_list.insert(0, button)
                            system_nums += 1
                        else:
                            if self.second_system and (self.second_system_setting == 0 or (
                                    self.second_system_setting == 1 and self.shop.fuse_IV)):
                                if auto.find_element(
                                        f"mirror/road_in_mir/acquire_ego_gift/{all_systems[self.second_system_select]}.png",
                                        my_crop=bbox,
                                        threshold=0.85):
                                    my_list.insert(system_nums, button)
                                    continue
                            my_list.append(button)
                select_bbox = ImageUtils.get_bbox(ImageUtils.load_image("mirror/road_in_mir/ego_gift_get_bbox.png"))
                if select_bbox:
                    select_bbox = (
                        max(select_bbox[0] - 100, 0),  # 确保左上角 x 坐标不小于 0
                        max(select_bbox[1] - 100, 0),  # 确保左上角 y 坐标不小于 0
                        min(select_bbox[2] + 100, cfg.set_win_size * 16 / 9),  # 确保右下角 x 坐标不大于 图片宽
                        min(select_bbox[3] + 100, cfg.set_win_size)  # 确保右下角 y 坐标不大于 图片高
                    )
                if auto.find_text_element(["0/1", "01", "1/1", "11", "1/2", "12"], my_crop=select_bbox):
                    for gift in my_list[:1]:
                        auto.mouse_click(gift[0], gift[1])
                    auto.click_element("mirror/road_in_mir/acquire_ego_gift_select_assets.png", model="normal")
                    time.sleep(2)
                    if retry() is False:
                        return False
                    return
                elif auto.find_text_element(["0/2", "02", "2/2", "22"], my_crop=select_bbox):
                    for gift in my_list[:2]:
                        auto.mouse_click(gift[0], gift[1])
                    auto.click_element("mirror/road_in_mir/acquire_ego_gift_select_assets.png", model="normal")
                    time.sleep(2)
                    if retry() is False:
                        return False
                    return
                else:
                    for gift in my_list:
                        auto.mouse_click(gift[0], gift[1])
                    auto.click_element("mirror/road_in_mir/acquire_ego_gift_select_assets.png", model="normal")
                    time.sleep(2)
                    if retry() is False:
                        return False
                    return

            except Exception as e:
                log.ERROR(e)
                continue

    def get_reward_in_road(self):
        main_loop_count = 20
        auto.model = 'clam'
        while True:
            if auto.take_screenshot() is None:
                auto.mouse_to_blank()
                continue
            # 如果回到主界面，退出循环
            if auto.click_element("mirror/claim_reward/rewards_acquired_assets.png"):
                return True
            if cfg.no_weekly_bonuses:
                bonuses = auto.find_element("mirror/claim_reward/weekly_bonuses.png",
                                            find_type='image_with_multiple_targets')
                if len(bonuses) >= 1:
                    for _ in range(len(bonuses)):
                        position = bonuses.pop(-1)
                        auto.mouse_click(position[0], position[1])
            if cfg.hard_mirror_single_bonuses:
                bonuses = auto.find_element("mirror/claim_reward/weekly_bonuses.png",
                                            find_type='image_with_multiple_targets')
                bonuses = sorted(bonuses, key=lambda x: x[0])
                if len(bonuses) > 1:
                    for _ in range(len(bonuses) - 1):
                        position = bonuses.pop(-1)
                        auto.mouse_click(position[0], position[1])
            if auto.click_element("mirror/claim_reward/claim_rewards_confirm_assets.png", threshold=0.75, model='clam'):
                continue
            if self.hard_switch and cfg.save_rewards:
                auto.click_element("mirror/claim_reward/claim_rewards_assets.png")
                sleep(1)
                pos = auto.find_element("mirror/claim_reward/use_enkephalin_assets.png", take_screenshot=True)
                if pos:
                    auto.mouse_click(pos[0] - 300 * (cfg.set_win_size / 1440), pos[1])
                continue
            elif auto.click_element("mirror/claim_reward/claim_rewards_assets.png"):
                sleep(1)
                # TODO: 统计获取的coins
                continue
            if auto.click_element("mirror/claim_reward/use_enkephalin_assets.png", threshold=0.75):  # 降低识别阈值
                continue
            # 处理周年活动弹出的窗口
            if auto.click_element("home/close_anniversary_event_assets.png"):
                continue
            retry()
            main_loop_count -= 1
            if main_loop_count % 3 == 0:
                log.DEBUG(f"镜牢奖励识别次数剩余{main_loop_count}次")
            if main_loop_count < 10:
                auto.model = "normal"
                log.DEBUG("识别模式切换到正常模式")
            if main_loop_count < 5:
                auto.model = 'aggressive'
                log.DEBUG("识别模式切换到激进模式")
            if main_loop_count < 0:
                raise log.ERROR("镜牢奖励领取出错,请手动操作重试")

    @begin_and_finish_time_log(task_name="镜牢商店")
    def in_shop(self):
        self.shop.in_shop(self.flood)
