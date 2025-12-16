import time
from time import sleep
from datetime import datetime

import cv2
import numpy as np

from module.automation import auto
from module.config import cfg
from module.decorator.decorator import begin_and_finish_time_log
from module.logger import log
from module.ocr import ocr
from tasks import sins
from tasks.base.retry import retry
from tasks.event.event_handling import EventHandling
from utils.image_utils import ImageUtils
from utils.utils import find_skill3


class Battle:
    def __init__(self):
        self.first_battle = False
        self.identify_keyword_turn = True
        self.mouse_click_rate = False
        self.INIT_CHANCE = 16
        self.running = True  # 用于外部打断战斗逻辑执行
        self.defense_all_time = False
        self.fail_times = 0

    @staticmethod
    def to_battle():
        loop_count = 15
        auto.model = 'clam'
        while True:
            # 自动截图
            if auto.take_screenshot() is None:
                continue
            if auto.click_element("battle/normal_to_battle_assets.png"):
                break
            if auto.click_element("battle/chaim_to_battle_assets.png"):
                break
            loop_count -= 1
            if loop_count < 10:
                auto.model = "normal"
                log.debug("识别模式切换到正常模式")
            if loop_count < 5:
                auto.model = 'aggressive'
                log.debug("识别模式切换到激进模式")
            if loop_count < 0:
                msg = "超出最大尝试次数,未能进入战斗"
                log.error(msg)
                return False

    @staticmethod
    def _update_wait_time(time: float = None, fail_flag: bool = False, total_count: int = 1):
        MAX_WAITING = 3.0  # 最大等待时间
        MIN_WAITING = 0.5  # 最小等待时间
        INIT_WAITING = 1.5  # 初始等待时间
        fail_adjust = 0.5
        success_adjust = -0.2
        if time is None:
            return INIT_WAITING

        total_count = total_count if total_count > 0 else 1  # 防止除0
        adjust = fail_adjust if fail_flag else success_adjust
        new_time = time + adjust / (total_count ** 0.5)  # 平方根调整

        new_time = min(new_time, MAX_WAITING)  # 防止超过最大等待时间
        new_time = max(new_time, MIN_WAITING)  # 防止低于最小等待时间
        if fail_flag:
            msg = f"匹配失败，等待时间从{time:.3f}调整为{new_time:.3f}"
            log.debug(msg)

        return new_time

    def _battle_operation(self, first_turn: bool, defense_first_round: bool, avoid_skill_3: bool):
        auto.mouse_click_blank()
        if first_turn and defense_first_round and auto.find_element("battle/gear_left.png", threshold=0.9):
            msg = f"第一回合全员防御，开始战斗"
            if self._defense_this_round() is False:
                defense_first_round = False
                msg = "第一回合全员防御失败，本场战斗改为P+Enter"
                auto.key_press('p')
                sleep(0.5)
                auto.key_press('enter')
            sleep(2)
            if not auto.find_element("battle/pause_assets.png", take_screenshot=True):
                auto.key_press('p')
                sleep(0.5)
                auto.key_press('enter')
        elif self.defense_all_time and auto.find_element("battle/gear_left.png", threshold=0.9):
            msg = f"使用全员防御模式开始战斗"
            if self._defense_this_round() is False:
                defense_all_time = False
                msg = "全员防御失败，本场战斗改为P+Enter"
                auto.key_press('p')
                sleep(0.5)
                auto.key_press('enter')
            sleep(2)
            if not auto.find_element("battle/pause_assets.png", take_screenshot=True):
                auto.key_press('p')
                sleep(0.5)
                auto.key_press('enter')
        elif avoid_skill_3 and auto.find_element("battle/gear_left.png", threshold=0.9):
            msg = f"使用避免3技能模式开始战斗"
            if self._chain_battle() is False:
                avoid_skill_3 = False
                msg = "使用避免三技能的链接战失败，本场战斗改为P+Enter"
                auto.key_press('p')
                sleep(0.5)
                auto.key_press('enter')
            sleep(2)
            if not auto.find_element("battle/pause_assets.png", take_screenshot=True):
                auto.key_press('p')
                sleep(0.5)
                auto.key_press('enter')
        else:
            auto.key_press('p')
            sleep(0.5)
            auto.key_press('enter')
            msg = f"使用P+Enter开始战斗"
            if self.mouse_click_rate:
                my_scale = cfg.set_win_size / 1440
                if pos := auto.find_element("battle/win_rate_card.png", threshold=0.75):
                    pos = [pos[0] + 50 * my_scale, pos[1] - 50 * my_scale]
                    auto.mouse_click(pos[0], pos[1])
                    auto.click_element("battle/gear_right.png")
            else:
                sleep(1)
                if not auto.find_element("battle/pause_assets.png", threshold=0.75):
                    self.mouse_click_rate = True
                else:
                    self.mouse_click_rate = False
        log.debug(msg)

    @begin_and_finish_time_log(task_name="一次战斗")
    def fight(self, avoid_skill_3=False, defense_first_round=False, infinite_battle=False, defense_all_time=False):
        chance = self.INIT_CHANCE
        waiting = self._update_wait_time()
        total_count = 0
        fail_count = 0
        in_mirror = False
        first_battle_reward = None
        event_chance = 15
        if defense_all_time:
            self.defense_all_time = defense_all_time

        first_turn = True
        start_time = time.time()

        self.fail_times = 0
        while self.running:
            from tasks.base.retry import check_times
            # 自动截图
            if auto.take_screenshot() is None:
                continue
            if auto.get_restore_time() is not None:
                start_time = max(start_time, auto.get_restore_time())
            if infinite_battle is False and check_times(start_time, timeout=900, logs=False):
                from tasks.base.back_init_menu import back_init_menu
                back_init_menu()
                return False

            if auto.find_element("mirror/road_in_mir/legend_assets.png"):
                if infinite_battle:
                    continue
                return False

            # 战斗开始前的加载
            if auto.find_element("base/waiting_assets.png"):
                sleep(0.5)
                continue

            # 判断是否为镜牢战斗
            if in_mirror is False and auto.find_element("battle/in_mirror_assets.png", model="aggressive"):
                in_mirror = True

            if view_status := auto.find_element("battle/view_status_assets.png", model="clam"):
                my_scale = cfg.set_win_size / 1440
                auto.click_element(view_status[0] + 100 * my_scale, view_status[1] - 500 * my_scale)
                continue

            # 如果正在交战过程
            if auto.find_element("battle/pause_assets.png"):
                sleep(2 * waiting)  # 战斗播片中增大间隔
                chance = self.INIT_CHANCE
                first_turn = False
                continue

            # 战斗失败重启
            if auto.find_element("battle/dead_all.png"):
                dead_select = auto.find_element("battle/dead_all.png", find_type="image_with_multiple_targets")
                if len(dead_select) == 3:
                    dead_select = sorted(dead_select, key=lambda y: y[1])
                    auto.mouse_click(dead_select[1][0], dead_select[1][1])
                else:
                    confirm_button = auto.find_element("battle/dead_all_confirm_assets.png")
                    try:
                        my_scale = cfg.set_win_size / 1440
                        auto.mouse_click(confirm_button[0] + 200 * my_scale, confirm_button[1] - 350 * my_scale)
                    except:
                        continue

                auto.click_element("battle/dead_all_confirm_assets.png")
                sleep(1)
                start_time = time.time()
                self.fail_times += 1
                if self.fail_times >= 5:
                    return False
                continue

            if in_mirror:
                if dead_position := auto.find_element("battle/dead.png"):
                    my_scale = cfg.set_win_size / 1440
                    dead_bbox = (
                        dead_position[0] - 100 * my_scale, dead_position[1] - 30 * my_scale,
                        dead_position[0] + 100 * my_scale,
                        dead_position[1] + 30 * my_scale)
                    if cfg.language_in_game == "zh_cn":
                        ocr_result = auto.find_text_element("阵亡", dead_bbox)
                    else:
                        ocr_result = auto.find_text_element("dead", dead_bbox)
                    if ocr_result is not False:
                        while True:
                            auto.mouse_to_blank()
                            if auto.take_screenshot() is None:
                                continue
                            if auto.find_element("mirror/road_in_mir/legend_assets.png"):
                                return False
                            if auto.click_element("battle/give_up_assets.png"):
                                sleep(2)
                                return False
                            if auto.click_element("battle/setting_assets.png"):
                                continue

            if fail_count >= 10 or self.identify_keyword_turn is False:
                # 如果多次识别不到战斗界面
                try:
                    turn_bbox = ImageUtils.get_bbox(ImageUtils.load_image("battle/turn_assets.png"))
                    sc = ImageUtils.crop(np.array(auto.screenshot), turn_bbox)
                    sc = cv2.inRange(sc, 50, 255)
                    result = ocr.run(sc)
                    ocr_result = [result.txts[i] for i in range(len(result.txts))]
                    ocr_result = "".join(ocr_result)
                except:
                    ocr_result = ''
                if "turn" in ocr_result:
                    self._battle_operation(first_turn, defense_first_round, avoid_skill_3)
                    chance = self.INIT_CHANCE
                    waiting = self._update_wait_time(waiting, False, total_count)
                    self.identify_keyword_turn = False
                    continue
            elif fail_count >= 5:
                if auto.click_element("battle/turn_assets.png") or auto.find_element("battle/win_rate_assets.png"):
                    self._battle_operation(first_turn, defense_first_round, avoid_skill_3)
                    chance = self.INIT_CHANCE
                    waiting = self._update_wait_time(waiting, False, total_count)
                    continue
            else:
                # 如果正在战斗待机界面
                if auto.find_element("battle/more_information_assets.png") or auto.find_element(
                        "battle/win_rate_assets.png"):
                    self._battle_operation(first_turn, defense_first_round, avoid_skill_3)
                    chance = self.INIT_CHANCE
                    waiting = self._update_wait_time(waiting, False, total_count)
                    continue
            if chance < 5:
                if not infinite_battle:
                    auto.mouse_to_blank()
                try:
                    turn_bbox = ImageUtils.get_bbox(ImageUtils.load_image("battle/turn_assets.png"))
                    sc = ImageUtils.crop(np.array(auto.screenshot), turn_bbox)
                    sc = cv2.inRange(sc, 50, 255)
                    result = ocr.run(sc)
                    ocr_result = [result.txts[i] for i in range(len(result.txts))]
                    ocr_result = "".join(ocr_result)
                except:
                    ocr_result = ''
                if "turn" in ocr_result or auto.click_element("battle/turn_assets.png") or auto.find_element(
                        "battle/win_rate_assets.png") or auto.find_element("battle/win_rate_card.png", threshold=0.75):
                    self._battle_operation(first_turn, defense_first_round, avoid_skill_3)
                    chance = self.INIT_CHANCE
                    waiting = self._update_wait_time(waiting, False, total_count)
                    continue
            if chance == 1:
                if not infinite_battle:
                    auto.mouse_to_blank()
                if auto.find_text_element(["rate", "胜率"]):
                    self._battle_operation(first_turn, defense_first_round, avoid_skill_3)
                    chance = self.INIT_CHANCE
                    waiting = self._update_wait_time(waiting, False, total_count)
                    sleep(1)
                    if not auto.find_element("battle/pause_assets.png"):
                        self.mouse_click_rate = True
                    continue
            if self.mouse_click_rate:
                if auto.find_element("battle/win_rate_card.png", threshold=0.75):
                    self._battle_operation(first_turn, defense_first_round, avoid_skill_3)
                    chance = self.INIT_CHANCE
                    waiting = self._update_wait_time(waiting, False, total_count)

            # 如果战斗中途出现事件
            if auto.find_element("event/choices_assets.png") and auto.find_element(
                    "event/select_first_option_assets.png"):
                if event_chance > 5:
                    auto.click_element("event/select_first_option_assets.png")
                    event_chance -= 1
                elif event_chance > 0:
                    auto.click_element("event/select_first_option_assets.png", find_type="image_with_multiple_targets")
                    event_chance -= 1
                else:
                    auto.click_element("event/select_first_option_assets.png", find_type="image_with_multiple_targets")
                    finishes_bbox = ImageUtils.get_bbox(
                        ImageUtils.load_image("event/continue_assets.png"))
                    if auto.find_text_element(
                            ["conti", "proc", "comme", "choices", "confirm", "行判", "始战", "继续"],
                            finishes_bbox):
                        auto.mouse_click((finishes_bbox[0] + finishes_bbox[2]) // 2,
                                         (finishes_bbox[1] + finishes_bbox[3]) // 2)
                        if infinite_battle:
                            continue
                        break
                    else:
                        event_chance = -1

            if auto.find_element("event/perform_the_check_feature_assets.png"):
                EventHandling.decision_event_handling()
            if auto.click_element("event/continue_assets.png"):
                continue
            if auto.click_element("event/proceed_assets.png"):
                continue
            if auto.click_element("event/commence_assets.png"):
                continue
            if auto.click_element("event/skip_assets.png", times=6):
                continue

            # 战斗结束，进入结算页面
            if auto.click_element("battle/battle_finish_confirm_assets.png", click=False):
                sleep(1)
                if auto.click_element("base/leave_up_assets.png"):
                    auto.click_element("base/leave_up_confirm_assets.png")
                    continue
                # 为某些人在副本战斗过程中启动脚本任务进行收尾
                if self.first_battle:
                    if auto.find_element("battle/clear_rewards_EXP_1.png") or auto.find_element(
                            "battle/clear_rewards_EXP_2.png") or auto.find_element("battle/clear_rewards_EXP_3.png"):
                        first_battle_reward = "EXP"
                    if auto.find_element("battle/clear_rewards_thread.png"):
                        first_battle_reward = "thread"
                auto.click_element("battle/battle_finish_confirm_assets.png")
                if infinite_battle:
                    continue
                break

            if auto.find_element("mirror/road_in_mir/legend_assets.png"):
                if infinite_battle:
                    continue
                break
            if auto.find_element("mirror/road_in_mir/acquire_ego_gift_card.png"):
                if infinite_battle:
                    continue
                break
            if auto.find_element("mirror/road_in_mir/select_encounter_reward_card_assets.png"):
                if infinite_battle:
                    continue
                break
            if chance <= (self.INIT_CHANCE // 2 + 1) and auto.find_element("teams/announcer_assets.png"):
                if infinite_battle:
                    continue
                break

            # 如果交战过程误触，导致战斗暂停
            if auto.click_element("battle/continue_assets.png"):
                continue
                # 如果网络波动，需要点击重试
            if retry() is False:
                return False

            chance -= 1
            sleep(waiting)
            # 更新等待时间
            waiting = self._update_wait_time(waiting, True, total_count)
            # 统计失败次数
            fail_count += 1
            if chance < 0:
                if infinite_battle:
                    continue
                break

        self.defense_all_time = False

        if total_count == 0:
            match_success_rate = 100
        else:
            # 保留最多三位小数
            match_success_rate = (1 - fail_count / total_count) * 100
        msg = f"此次战斗匹配失败次数{fail_count} 匹配总次数{total_count} 匹配成功率{match_success_rate}%"
        log.debug(msg)
        if self.first_battle:
            return first_battle_reward
        else:
            return None

    def _chain_battle(self):
        try:
            scale = cfg.set_win_size / 1440

            gear_left = auto.find_element("battle/gear_left.png")

            gear_1 = [gear_left[0] + 94 * scale, gear_left[1] - 37 * scale]
            gear_right = auto.find_element("battle/gear_right.png")
            gear_2 = [gear_right[0] - 100 * scale, gear_right[1]]

            bbox = (gear_1[0], gear_1[1] - 15 * scale, gear_2[0], gear_1[1])

            skill_nums = int((bbox[2] - bbox[0]) / (145 * scale))

            if skill_nums >= 10:
                bbox = (bbox[0] + 50 * scale, bbox[1], bbox[2], bbox[3])

            sc = auto.get_screenshot_crop(bbox)

            skill3 = []
            for sin in sins.keys():
                skill3 += find_skill3(sc, sins[sin])
            skill3 = [round(x[0] / (145 * scale)) for x in skill3]

            skill_list = [gear_left]

            for i in range(1, skill_nums + 1):
                if i in skill3:
                    skill_list.append(
                        [gear_left[0] + 250 * scale + 150 * scale * (i - 1), gear_left[1] + 50 * scale + 250 * scale])
                else:
                    skill_list.append([gear_left[0] + 250 * scale + 150 * scale * (i - 1), gear_left[1] + 50 * scale])
            skill_list.append([gear_right[0], gear_right[1] + 150 * scale])

            auto.mouse_drag_link(skill_list)

            auto.mouse_to_blank()

            sleep(1)
        except Exception as e:
            return False

    @staticmethod
    def _defense_this_round(move_back: bool = False) -> bool:
        try:
            scale = cfg.set_win_size / 1440

            gear_left = auto.find_element("battle/gear_left.png")

            gear_1 = [gear_left[0] + 100 * scale, gear_left[1] - 35 * scale]
            gear_right = auto.find_element("battle/gear_right.png")
            gear_2 = [gear_right[0] - 100 * scale, gear_right[1]]

            bbox = (gear_1[0], gear_1[1] - 15 * scale, gear_2[0], gear_1[1])

            skill_nums = int((bbox[2] - bbox[0]) / (145 * scale))

            skill_list = []

            for i in range(1, skill_nums + 1):
                skill_list.append(
                    [gear_left[0] + 250 * scale + 150 * scale * (i - 1), gear_left[1] + 50 * scale + 250 * scale])

            for skill in skill_list:
                auto.mouse_click(skill[0], skill[1])
                if cfg.simulator:
                    sleep(cfg.mouse_action_interval)
                else:
                    sleep(cfg.mouse_action_interval // 1.5)

            skill_list.insert(0, gear_left)
            skill_list.append([gear_right[0] + 100 * scale, gear_right[1] + 150 * scale])

            auto.mouse_drag_link(skill_list)

            auto.mouse_to_blank(move_back=move_back)

            sleep(1)
            return True
        except Exception as e:
            return False
