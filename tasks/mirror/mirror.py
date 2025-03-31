import time
from time import sleep

import pyautogui

from module.automation import auto
from module.config import cfg
from module.decorator.decorator import begin_and_finish_time_log
from module.logger import log
from module.my_error.my_error import unableToFindTeamError
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

    def __init__(self, sinner_team, team_number, shop_sell_list, fuse_switch, system, fuse_aggressive_switch,
                 hard_switch, no_weekly_bonuses):
        self.logger = log
        self.sinner_team = sinner_team
        self.team_number = team_number
        self.shop = Shop(system, shop_sell_list, fuse_switch, fuse_aggressive_switch)
        self.fuse_switch = fuse_switch
        self.system = system
        self.start_time = time.time()
        self.first_battle = True  # 判断是否首次进入战斗，如果是则重新配队
        self.hard_switch = hard_switch
        self.no_weekly_bonuses = no_weekly_bonuses
        # 统计时间
        self.find_road_total_time = 0
        self.battle_total_time = 0
        self.shop_total_time = 0
        self.event_total_time = 0
        self.event_times = 0
        self.layer_times = [0, 0]

    def road_to_mir(self):
        loop_count = 30
        auto.model = 'clam'
        self.first_battle = True
        while True:
            # 自动截图
            if auto.take_screenshot() is None:
                continue
            auto.mouse_to_blank()
            if auto.find_element("mirror/road_in_mir/legend_assets.png"):
                break
            if auto.click_element("mirror/road_to_mir/resume_assets.png"):
                break
            if auto.click_element("mirror/road_to_mir/enter_mirror_assets.png"):
                break
            infinity_bbox = ImageUtils.get_bbox(ImageUtils.load_image("mirror/road_to_mir/infinity_mirror_bbox.png"))
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
            retry()
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

        # 未到达奖励页不会停止
        while True:
            # 自动截图
            if auto.take_screenshot() is None:
                continue

            # 镜牢结束领取奖励
            if auto.find_element("mirror/claim_reward/battle_statistics_assets.png") and auto.click_element(
                    "base/battle_finish_confirm_assets.png"):
                break
            if auto.find_element("mirror/claim_reward/claim_rewards_assets.png") and auto.find_element(
                    "mirror/claim_reward/complete_mirror_100%_assets.png"):
                break
            if auto.find_element("mirror/claim_reward/enkephalin_assets.png", threshold=0.9):
                continue

            # 选择楼层主题包的情况
            if auto.find_element("mirror/theme_pack/feature_theme_pack_assets.png"):
                sleep(2)
                select_theme_pack(self.hard_switch)
                if self.layer_times[0] == 0:
                    self.layer_times[0] = time.time()
                else:
                    this_layer_time = time.time() - self.layer_times[0]
                    self.layer_times[0] = time.time()
                    msg = f"启动后第{self.layer_times[1]}层卡包"
                    to_log_with_time(msg, this_layer_time)
                self.layer_times[1] += 1
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
                if auto.find_element('mirror/shop/shop_coins_assets.png'):
                    continue
                if auto.find_element("mirror/claim_reward/claim_rewards_assets.png") and auto.find_element(
                        "mirror/claim_reward/complete_mirror_100%_assets.png"):
                    break
                retry()
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
                    continue

            # 没有配队的情况
            if auto.find_element("battle/select_none_assets.png"):
                auto.mouse_click_blank()
                self.first_battle = True
                continue

            # 在战斗中
            if battle.identify_keyword_turn:
                if auto.find_element("battle/turn_assets.png") or auto.find_element("battle/in_mirror_assets.png"):
                    self.battle_total_time += battle.fight()
                    continue
            else:
                turn_bbox = ImageUtils.get_bbox(ImageUtils.load_image("battle/turn_assets.png"))
                turn_ocr_result = auto.find_text_element("turn", turn_bbox)
                if turn_ocr_result is not False:
                    self.battle_total_time += battle.fight()
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
                get_reward_card()
                continue

            # 在主界面时，开始进入镜牢
            if auto.click_element("home/drive_assets.png") or auto.find_element("home/window_assets.png"):
                self.road_to_mir()
                continue
            # 在镜牢界面，进入镜牢
            if auto.click_element("mirror/road_to_mir/enter_assets.png"):
                self.road_to_mir()
                continue

            # 初始饰品选择
            if auto.find_element("mirror/road_to_mir/select_init_ego_gifts_assets.png"):
                self.select_init_ego_gift()
                continue

            # 遇到选择增益事件（少见）
            if auto.find_element("mirror/road_in_mir/select_event_effect.png"):
                auto.click_element("mirror/road_in_mir/event_effect_button.png")
                auto.click_element("mirror/road_in_mir/select_event_effect_confirm.png")
                continue

            # 取消十层
            if auto.find_element("mirror/infinity_mirror_assets.png"):
                auto.click_element("mirror/infinity_mirror_close_assets.png")
                continue

            # 防卡死
            auto.mouse_click_blank()
            retry()

        msg = f"开始进行镜牢奖励领取"
        log.INFO(msg)

        while True:
            # 自动截图
            if auto.take_screenshot() is None:
                auto.mouse_to_blank()
                continue
            # 如果回到主界面，退出循环
            if auto.find_element("home/drive_assets.png"):
                break
            if auto.click_element("base/battle_finish_confirm_assets.png"):
                continue
            if auto.click_element("mirror/claim_reward/rewards_acquired_assets.png"):
                continue
            if auto.click_element("mirror/claim_reward/claim_rewards_confirm_assets.png"):
                continue
            if self.no_weekly_bonuses and auto.click_element("mirror/claim_reward/weekly_bonuses.png"):
                continue
            if auto.click_element("mirror/claim_reward/enkephalin_assets.png"):
                continue
            if auto.click_element("mirror/claim_reward/claim_rewards_assets.png"):
                # TODO: 统计获取的coins
                continue
            # 处理周年活动弹出的窗口
            if auto.click_element("home/close_anniversary_event_assets.png"):
                continue
            retry()

        # 计时结束
        end_time = time.time()
        elapsed_time = end_time - start_time

        this_layer_time = time.time() - self.layer_times[0]
        msg = f"启动后第{self.layer_times[1]}层卡包"
        to_log_with_time(msg, this_layer_time)

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
        loop_count = 30
        auto.model = 'clam'
        while True:
            # 自动截图
            if auto.take_screenshot() is None:
                continue

            if auto.find_element("mirror/road_to_mir/bleed_gift_assets.png"):
                break

            if auto.click_element("mirror/road_to_mir/dreaming_star/select_star_confirm_assets.png"):
                break

            if self.fuse_switch is False:
                auto.click_element("mirror/road_to_mir/dreaming_star/20_stars_assets.png")
                auto.click_element("mirror/road_to_mir/dreaming_star/60_stars_assets.png")
                auto.click_element("mirror/road_to_mir/dreaming_star/40_stars_2_assets.png")
                auto.click_element("mirror/road_to_mir/dreaming_star/20_stars_2_assets.png")
                auto.click_element("mirror/road_to_mir/dreaming_star/10_stars_assets.png")
            else:
                # 根据B站UP主 绅士丶蚂蚱 《镜牢5完全攻略》制定
                auto.click_element("mirror/road_to_mir/dreaming_star/20_stars_assets.png")
                auto.click_element("mirror/road_to_mir/dreaming_star/20_stars_2_assets.png")
                auto.click_element("mirror/road_to_mir/dreaming_star/10_stars_assets.png")
                auto.click_element("mirror/road_to_mir/dreaming_star/60_stars_assets.png")
                auto.click_element("mirror/road_to_mir/dreaming_star/30_stars_assets.png")
                auto.click_element("mirror/road_to_mir/dreaming_star/30_stars_2_assets.png")
                auto.click_element("mirror/road_to_mir/dreaming_star/10_stars_2_assets.png")

            if auto.click_element("mirror/road_to_mir/dreaming_star/dreaming_star_enter_assets.png"):
                sleep(0.5)
                continue

            retry()
            loop_count -= 1
            if loop_count < 20:
                auto.model = "normal"
            if loop_count < 10:
                auto.model = 'aggressive'
            if loop_count < 0:
                raise log.ERROR("无法进入镜牢，不能进行下一步,请手动操作重试")

    def select_init_ego_gift(self):
        scroll = False
        select_system = False
        loop_count = 30
        auto.model = 'clam'
        while True:
            # 自动截图
            if auto.take_screenshot() is None:
                continue

            if auto.find_element("mirror/theme_pack/feature_theme_pack_assets.png"):
                break

            if auto.click_element("mirror/road_in_mir/ego_gift_get_confirm_assets.png"):
                break

            if self.system == "slash" or self.system == "pierce" or self.system == "blunt" and scroll == False:
                slash_button = auto.find_element("mirror/road_to_mir/slash_gift_model_assets.png")
                if slash_button is not None:
                    auto.mouse_drag(slash_button[0], slash_button[1], drag_time=0.2, dx=0, dy=-200)
                    sleep(0.5)
                    continue
                scroll = True

            if auto.click_element(f"mirror/road_to_mir/{self.system}_gift_assets.png") and select_system == False:
                select_system = True
                continue

            auto.click_element(f"mirror/road_to_mir/select_init_gift/{self.system}_ego_gift_1.png")
            auto.click_element(f"mirror/road_to_mir/select_init_gift/{self.system}_ego_gift_2.png")
            auto.click_element(f"mirror/road_to_mir/select_init_gift/{self.system}_ego_gift_3.png")

            if auto.click_element("mirror/road_to_mir/select_init_ego_gifts_confirm_assets.png"):
                continue

            retry()
            loop_count -= 1
            if loop_count < 20:
                auto.model = "normal"
            if loop_count < 10:
                auto.model = 'aggressive'
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
        while auto.click_element("mirror/road_to_mir/select_team_confirm_assets.png") is False:
            if auto.take_screenshot() is None:
                continue
            retry()
            if auto.find_element("mirror/road_to_mir/dreaming_star/coins_assets.png"):
                break
            loop_count -= 1
            if loop_count < 20:
                auto.model = "normal"
            if loop_count < 10:
                auto.model = 'aggressive'
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
                retry()
            for _ in range(3):
                while auto.take_screenshot() is None:
                    continue
                if search_road_farthest_distance():
                    sleep(1)
                    return True
                retry()
        except Exception as e:
            log.ERROR(f"寻路出错:{e}")
            return False
        while True:
            # 自动截图
            if auto.take_screenshot() is None:
                continue
            auto.mouse_to_blank()
            if auto.click_element("mirror/road_in_mir/towindow&forfeit_confirm_assets.png"):
                break
            if auto.click_element("mirror/road_in_mir/to_window_assets.png"):
                continue
            if auto.click_element("mirror/road_in_mir/setting_assets.png"):
                sleep(1)
                continue
            retry()

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
            retry()
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

            # 如果在战斗中或回到镜牢路线图中，则跳出循环
            if auto.find_element("battle/turn_assets.png"):
                break
            if auto.find_element("mirror/road_in_mir/legend_assets.png"):
                break

            # 针对不同事件进行处理，优先选直接获取的，再选需要判定的，再选后续事件的，最后第一个事项
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

            retry()
            if auto.click_element("event/skip_assets.png", times=6):
                continue

            if event_chance < 0:
                msg = "事件卡死，尝试返回主界面"
                log.ERROR(msg)
                back_init_menu()
                break
            loop_count -= 1
            if loop_count < 20:
                auto.model = "normal"
            if loop_count < 10:
                auto.model = 'aggressive'
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
                        if cfg.language == "zh_cn":
                            ocr_result = auto.find_text_element("白棉花", bbox)
                        else:
                            ocr_result = auto.find_text_element(["white", "gossypium"], bbox)
                        if isinstance(ocr_result, list):
                            if len(ocr_result) >= 2:
                                continue
                        auto.mouse_click(button[0], button[1])
                        auto.click_element("mirror/road_in_mir/acquire_ego_gift_select_assets.png", model="normal")
                        time.sleep(2)
                        retry()
                        return
                elif len(acquire_button) == 1:
                    for button in acquire_button:
                        bbox = (button[0] - 350 * my_scale, button[1] - 50 * my_scale, button[0] + 150 * my_scale,
                                button[1] + 250 * my_scale)
                        if cfg.language == "zh_cn":
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
                                retry()
                                return
                        auto.mouse_click(button[0], button[1])
                        auto.click_element("mirror/road_in_mir/acquire_ego_gift_select_assets.png", model="normal")
                        time.sleep(2)
                        retry()
                        return
                else:
                    for button in acquire_button:
                        bbox = (button[0] - 350 * my_scale, button[1] - 50 * my_scale, button[0] + 150 * my_scale,
                                button[1] + 250 * my_scale)
                        if cfg.language == "zh_cn":
                            ocr_result = auto.find_text_element("白棉花", bbox)
                        else:
                            ocr_result = auto.find_text_element(["white", "gossypium"], bbox)
                        if ocr_result:
                            continue
                        if auto.find_element(f"mirror/road_in_mir/acquire_ego_gift/{self.system}.png", my_crop=bbox,
                                             threshold=0.85):
                            my_list.insert(0, button)
                        else:
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
                    retry()
                    return
                elif auto.find_text_element(["0/2", "02", "2/2", "22"], my_crop=select_bbox):
                    for gift in my_list[:2]:
                        auto.mouse_click(gift[0], gift[1])
                    auto.click_element("mirror/road_in_mir/acquire_ego_gift_select_assets.png", model="normal")
                    time.sleep(2)
                    retry()
                    return
                else:
                    for gift in my_list:
                        auto.mouse_click(gift[0], gift[1])
                    auto.click_element("mirror/road_in_mir/acquire_ego_gift_select_assets.png", model="normal")
                    time.sleep(2)
                    retry()
                    return


            except Exception as e:
                log.ERROR(e)
                continue

    @begin_and_finish_time_log(task_name="镜牢商店")
    def in_shop(self):
        self.shop.in_shop()
