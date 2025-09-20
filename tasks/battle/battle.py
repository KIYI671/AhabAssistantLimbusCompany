from time import sleep

from module.automation import auto
from module.config import cfg
from module.decorator.decorator import begin_and_finish_time_log
from module.logger import log
from tasks import sins
from tasks.base.retry import retry
from tasks.event.event_handling import EventHandling
from utils.image_utils import ImageUtils
from utils.utils import find_skill3


class Battle:
    def __init__(self):
        self.first_battle = False
        self.identify_keyword_turn = True

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
                log.DEBUG("识别模式切换到正常模式")
            if loop_count < 5:
                auto.model = 'aggressive'
                log.DEBUG("识别模式切换到激进模式")
            if loop_count < 0:
                msg = "超出最大尝试次数,未能进入战斗"
                log.ERROR(msg)
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
            log.DEBUG(msg)

        return new_time

    @begin_and_finish_time_log(task_name="一次战斗")
    def fight(self, avoid_skill_3=False, defense_first_round=False):
        INIT_CHANCE = 16
        chance = INIT_CHANCE
        waiting = self._update_wait_time()
        total_count = 0
        fail_count = 0
        in_mirror = False
        first_battle_reward = None
        event_chance = 15

        first_turn = True
        while True:
            # 自动截图
            if auto.take_screenshot() is None:
                continue

            if auto.find_element("mirror/road_in_mir/legend_assets.png"):
                return False

            # 战斗开始前的加载
            if auto.find_element("base/waiting_assets.png"):
                sleep(0.5)
                continue

            # 判断是否为镜牢战斗
            if in_mirror is False and auto.find_element("battle/in_mirror_assets.png", model="aggressive"):
                in_mirror = True

            # 如果正在交战过程
            if auto.find_element("battle/pause_assets.png"):
                sleep(2 * waiting)  # 战斗播片中增大间隔
                chance = INIT_CHANCE
                first_turn = False
                continue

            if auto.find_element("battle/dead_all.png"):
                dead_select = auto.find_element("battle/dead_all.png", find_type="image_with_multiple_targets")
                dead_select = sorted(dead_select, key=lambda y: y[1])
                auto.mouse_click(dead_select[1][0], dead_select[1][1])

                auto.click_element("battle/dead_all_confirm_assets.png")
                sleep(1)
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

            if fail_count >= 5 or self.identify_keyword_turn is False:
                # 如果多次识别不到战斗界面
                turn_bbox = ImageUtils.get_bbox(ImageUtils.load_image("battle/turn_assets.png"))
                turn_ocr_result = auto.find_text_element("turn", turn_bbox)
                if turn_ocr_result is not False:
                    auto.mouse_click_blank()
                    if first_turn and defense_first_round and auto.find_element("battle/gear_left.png", threshold=0.9):
                        msg = f"第一回合全员防御，开始战斗"
                        if self._defense_first_round() is False:
                            defense_first_round = False
                            msg = "第一回合全员防御失败尝试其他操作"
                            log.DEBUG(msg)
                        else:
                            log.DEBUG(msg)
                            continue
                    if avoid_skill_3 and auto.find_element("battle/gear_left.png", threshold=0.9):
                        msg = f"使用避免3技能模式开始战斗"
                        if self._chain_battle() is False:
                            avoid_skill_3 = False
                            msg = "使用避免三技能的链接战失败，本场战斗改为P+Enter"
                    else:
                        auto.key_press('p')
                        sleep(0.5)
                        auto.key_press('enter')
                        msg = f"使用P+Enter开始战斗"
                    chance = INIT_CHANCE
                    log.DEBUG(msg)
                    waiting = self._update_wait_time(waiting, False, total_count)
                    self.identify_keyword_turn = False
                    continue
            else:
                # 如果正在战斗待机界面
                if auto.click_element("battle/turn_assets.png") or auto.find_element("battle/win_rate_assets.png"):
                    auto.mouse_click_blank()
                    if first_turn and defense_first_round and auto.find_element("battle/gear_left.png", threshold=0.9):
                        msg = f"第一回合全员防御，开始战斗"
                        if self._defense_first_round() is False:
                            defense_first_round = False
                            msg = "第一回合全员防御失败，本场战斗改为P+Enter"
                    elif avoid_skill_3 and auto.find_element("battle/gear_left.png", threshold=0.9):
                        msg = f"使用避免3技能模式开始战斗"
                        if self._chain_battle() is False:
                            avoid_skill_3 = False
                            msg = "使用避免三技能的链接战失败，本场战斗改为P+Enter"
                    else:
                        auto.key_press('p')
                        sleep(0.5)
                        auto.key_press('enter')
                        msg = f"使用P+Enter开始战斗"
                    chance = INIT_CHANCE
                    log.DEBUG(msg)
                    waiting = self._update_wait_time(waiting, False, total_count)
                    continue

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
                break

            if auto.find_element("mirror/road_in_mir/legend_assets.png"):
                break
            if auto.find_element("mirror/road_in_mir/acquire_ego_gift.png"):
                break
            if auto.find_element("mirror/road_in_mir/select_encounter_reward_card_assets.png"):
                break
            if chance <= (INIT_CHANCE // 2 + 1) and auto.find_element("teams/announcer_assets.png"):
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
                break

        if total_count == 0:
            match_success_rate = 100
        else:
            # 保留最多三位小数
            match_success_rate = (1 - fail_count / total_count) * 100
        msg = f"此次战斗匹配失败次数{fail_count} 匹配总次数{total_count} 匹配成功率{match_success_rate}%"
        log.DEBUG(msg)
        if self.first_battle:
            return first_battle_reward
        else:
            return None

    def _chain_battle(self):
        try:
            scale = cfg.set_win_size / 1440

            gear_left = auto.find_element("battle/gear_left.png")

            gear_1 = [gear_left[0] + 100 * scale, gear_left[1] - 35 * scale]
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

            sleep(1)
        except Exception as e:
            return False

    def _defense_first_round(self):
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
                sleep(cfg.mouse_action_interval // 1.5)

            skill_list.insert(0, gear_left)
            skill_list.append([gear_right[0] + 75 * scale, gear_right[1] + 150 * scale])

            auto.mouse_drag_link(skill_list)

            sleep(1)
        except Exception as e:
            return False
