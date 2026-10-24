import random
import re
import time
from dataclasses import dataclass
from time import sleep
from typing import Callable, Optional

import cv2
import numpy as np

from module.automation import auto
from module.config import cfg
from module.decorator.decorator import begin_and_finish_time_log
from module.logger import log
from module.my_error.my_error import userStopError
from module.ocr import ocr
from tasks import sins
from tasks.base.retry import retry
from tasks.battle.optional_actions import BattleEventOutcome, BattleOptions, TurnEgoAction, general_battle, lower_row_points
from tasks.battle.animation_hold import optional_hold_cleanup
from tasks.battle.speed_hold import UnifiedSpeedHold
from tasks.event import event_handling
from tasks.mirror.failure_policy import BattleAttemptBudget, DefeatDialogAction
from utils.image_utils import ImageUtils
from utils.utils import find_skill3

DEFENSE_FOR_SOLO_TURN_LIMIT = 5


@dataclass
class DefenseForSoloState:
    """一次镜牢任务内共享的连续防御回合状态。"""

    remaining_turns: int = DEFENSE_FOR_SOLO_TURN_LIMIT

    def consume_turn(self) -> None:
        if self.remaining_turns > 0:
            self.remaining_turns -= 1


class Battle:
    def __init__(self, is_tool: bool = False):
        self.first_battle = False
        self.identify_keyword_turn = True
        self.mouse_click_rate = False
        self.INIT_CHANCE = 16
        self.running = True  # 用于外部打断战斗逻辑执行
        self.defense_all_time = False
        self.fail_times = 0
        self.cur_turn = 1
        self.is_tool = is_tool
        """是否由小工具初始化"""

    @staticmethod
    def to_battle():
        loop_count = 15
        auto.model = "clam"
        click = False
        while True:
            # 自动截图
            if auto.take_screenshot() is None:
                continue
            if click and (
                auto.find_element("battle/normal_to_battle_assets.png")
                or auto.find_element("battle/chaim_to_battle_assets.png")
            ):
                click = False
                from tasks.teams.team_formation import deal_with_spills

                deal_with_spills()
            if auto.click_element("battle/normal_to_battle_assets.png"):
                click = True
                sleep(2)
                continue
            if auto.click_element("battle/chaim_to_battle_assets.png"):
                click = True
                sleep(2)
                continue
            loop_count -= 1
            if loop_count < 10:
                auto.model = "normal"
                log.debug("识别模式切换到正常模式")
            if loop_count < 5:
                auto.model = "aggressive"
                log.debug("识别模式切换到激进模式")
            if loop_count < 0:
                msg = "超出最大尝试次数,未能进入战斗"
                log.error(msg)
                return False
            if click:
                break

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
        new_time = time + adjust / (total_count**0.5)  # 平方根调整

        new_time = min(new_time, MAX_WAITING)  # 防止超过最大等待时间
        new_time = max(new_time, MIN_WAITING)  # 防止低于最小等待时间
        if fail_flag:
            msg = f"匹配失败，等待时间从{time:.3f}调整为{new_time:.3f}"
            log.debug(msg)

        return new_time

    def _battle_operation(
        self,
        first_turn: bool,
        defense_first_round: bool,
        avoid_skill_3: bool,
        prioritize_skill_3: bool = False,
        defense_for_solo_state: DefenseForSoloState | None = None,
        defense_for_solo_used_this_turn: bool = False,
    ) -> bool:
        auto.mouse_click_blank()
        use_limited_defense = (
            defense_for_solo_state is not None
            and defense_for_solo_state.remaining_turns > 0
            and not defense_for_solo_used_this_turn
        )
        use_first_round_defense = (
            first_turn and defense_first_round and not defense_for_solo_used_this_turn
        )
        limited_defense_succeeded = False
        if (use_limited_defense or use_first_round_defense) and auto.find_element(
            "battle/gear_left.png", threshold=0.9
        ):
            if use_limited_defense:
                msg = f"小指良单通连续防御（剩余{defense_for_solo_state.remaining_turns}回合），开始战斗"
            else:
                msg = "第一回合全员防御，开始战斗"
            if self._defense_this_round() is False:
                if use_limited_defense:
                    msg = "小指良单通连续防御失败，本回合改为P+Enter"
                else:
                    msg = "第一回合全员防御失败，本场战斗改为P+Enter"
                auto.key_press("p")
                sleep(0.5)
                auto.key_press("enter")
            elif use_limited_defense:
                defense_for_solo_state.consume_turn()
                limited_defense_succeeded = True
                log.info(f"小指良单通连续防御已执行，剩余 {defense_for_solo_state.remaining_turns} 回合")
                if defense_for_solo_state.remaining_turns == 0:
                    log.info("本次镜牢的连续防御已完成，后续回合恢复普通战斗操作")
            sleep(2)
            if not auto.find_element("battle/pause_assets.png", take_screenshot=True):
                auto.key_press("p")
                sleep(0.5)
                auto.key_press("enter")
        elif self.defense_all_time:
            if auto.find_element("battle/gear_left.png", threshold=0.9):
                msg = "使用全员防御模式开始战斗"
                self._defense_this_round()
        elif (avoid_skill_3 or prioritize_skill_3) and auto.find_element(
            "battle/gear_left.png", threshold=0.9
        ):
            use_prioritize_skill_3 = prioritize_skill_3 and not avoid_skill_3
            mode_name = "优先" if use_prioritize_skill_3 else "避免"
            msg = f"使用{mode_name}3技能模式开始战斗"
            if self._chain_battle(prioritize_skill_3=use_prioritize_skill_3) is False:
                msg = f"使用{mode_name}三技能的链接战失败，本场战斗改为P+Enter"
                auto.key_press("p")
                sleep(0.5)
                auto.key_press("enter")
            sleep(2)
            if not auto.find_element("battle/pause_assets.png", take_screenshot=True):
                auto.key_press("p")
                sleep(0.5)
                auto.key_press("enter")
        else:
            auto.key_press("p")
            sleep(0.5)
            auto.key_press("enter")
            msg = "使用P+Enter开始战斗"
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
        return limited_defense_succeeded

    @begin_and_finish_time_log(task_name="一次战斗")
    @optional_hold_cleanup(auto)
    def fight(
        self,
        avoid_skill_3=False,
        defense_first_round=False,
        infinite_battle=False,
        defense_all_time=False,
        defense_on_turn1=False,
        choice_event_handling=True,
        combat_count=1,
        defense_for_solo_state: DefenseForSoloState | None = None,
        prioritize_skill_3=False,
        rabbit_options: BattleOptions | None = None,
        rabbit_animation_hold=False,
        event_excluded_sinners=(),
        ego_attempt_state=None,
        max_attempts=None,
        combat_speed_hold=False,
        speed_hold=False,
    ):
        chance = self.INIT_CHANCE
        waiting = self._update_wait_time()
        total_count = 0
        fail_count = 0
        in_mirror = False
        first_battle_reward = None
        event_chance = 15
        if defense_all_time:
            self.defense_all_time = defense_all_time
        if defense_on_turn1:
            defense_first_round = True
            turn_ocr_bbox = ImageUtils.get_bbox(ImageUtils.load_image("battle/turn_ocr_assets.png"))

        first_turn = True
        optional_action = None
        if rabbit_options and rabbit_options.ego_enabled:
            turn_box = None
            if rabbit_options.ego_enabled:
                try:
                    turn_box = ImageUtils.get_bbox(ImageUtils.load_image("battle/turn_ocr_assets.png"))
                except Exception:
                    log.warning("TURN区域未就绪，本次使用一般战斗流程")
            optional_action = TurnEgoAction(auto, cfg.set_win_size, rabbit_options, log, turn_box, lambda: self.running,
                                            attempted_turns=ego_attempt_state)
        # Legacy keyword aliases use the same controller, never competing holds.
        speed_controller = UnifiedSpeedHold(auto, lambda: self.running, logger=log) if (
            speed_hold or rabbit_animation_hold or combat_speed_hold
        ) and not cfg.simulator else None
        event_check_active = False
        attempt_budget = BattleAttemptBudget(max_attempts) if max_attempts is not None else None
        defeat_action = DefeatDialogAction() if attempt_budget is not None else None
        defense_for_solo_used_this_turn = False
        start_time = time.time()

        def perform_battle_operation() -> None:
            nonlocal defense_for_solo_used_this_turn
            if speed_controller is not None:
                speed_controller.update(False)
            if attempt_budget is not None:
                attempt_budget.combat_resumed()
            ego_claim = optional_action.claim_turn() if optional_action is not None else None
            limited_due = (defense_for_solo_state is not None
                           and defense_for_solo_state.remaining_turns > 0
                           and not defense_for_solo_used_this_turn)
            guard_due = (limited_due or (first_turn and defense_first_round
                         and not defense_for_solo_used_this_turn) or self.defense_all_time)
            # Preparation must never drag/Enter. EGO is allowed to cover guard.
            # With EGO disabled use the mature original guard/skill path.
            guard_due = guard_due and optional_action is not None
            guard_prepared = self._prepare_defense() if guard_due else False
            ego_due = optional_action.prepare(ego_claim) if optional_action is not None else False
            if guard_due or ego_due:
                if self.running:
                    general_battle(auto, cfg.set_win_size / 1440, True, log)
                    if guard_prepared:
                        defense_for_solo_used_this_turn = True
                        if limited_due:
                            defense_for_solo_state.consume_turn()
                            log.info(f"已准备守备并提交（允许EGO覆盖），剩余 {defense_for_solo_state.remaining_turns} 回合")
                return
            limited_defense_succeeded = self._battle_operation(
                first_turn=first_turn,
                defense_first_round=defense_first_round,
                avoid_skill_3=avoid_skill_3,
                prioritize_skill_3=prioritize_skill_3,
                defense_for_solo_state=defense_for_solo_state,
                defense_for_solo_used_this_turn=defense_for_solo_used_this_turn,
            )
            defense_for_solo_used_this_turn = (
                defense_for_solo_used_this_turn or limited_defense_succeeded
            )

        self.fail_times = 0
        while self.running:
            from tasks.base.retry import check_times

            # 自动截图
            if (auto.take_screenshot(gray=False) if speed_controller is not None else auto.take_screenshot()) is None:
                if speed_controller is not None:
                    speed_controller.release(block=True)
                continue
            if auto.get_restore_time() is not None:
                start_time = max(start_time, auto.get_restore_time())
            if infinite_battle is False and check_times(start_time, timeout=900 + 300 * combat_count, logs=False):
                from tasks.base.back_init_menu import back_init_menu

                if speed_controller is not None:
                    speed_controller.release(block=True)
                back_init_menu()
                return False

            # A floor transition can skip the map/reward pages. Hand the
            # theme-pack screen back to Mirror.run before any battle input.
            if not infinite_battle and auto.find_element("mirror/theme_pack/feature_theme_pack_assets.png"):
                return False

            if speed_controller is not None:
                if auto.find_element("mirror/road_in_mir/select_encounter_reward_card_assets.png", threshold=0.9):
                    speed_controller.release(block=True)
                    if not infinite_battle:
                        break
                speed_controller.probe()
                if speed_controller.signal_visible:
                    if speed_controller.combat_visible:
                        if optional_action is not None:
                            optional_action.observe_running()
                        if attempt_budget is not None:
                            attempt_budget.combat_resumed()
                        chance = self.INIT_CHANCE
                        first_turn = False
                        defense_for_solo_used_this_turn = False
                    sleep(0.1)
                    continue
                auto.screenshot = auto.screenshot.convert("L")

            total_count += 1

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
                auto.mouse_click(view_status[0] + 100 * my_scale, view_status[1] - 500 * my_scale)
                continue

            # 如果正在交战过程
            defeated = auto.find_element("battle/dead_all.png")
            if defeat_action is not None and not defeated:
                defeat_action.reset()
            if auto.find_element("battle/pause_assets.png") and not defeated:
                if optional_action is not None:
                    optional_action.observe_running()
                if attempt_budget is not None:
                    attempt_budget.combat_resumed()
                sleep(0.15 if speed_controller is not None else 2 * waiting)
                chance = self.INIT_CHANCE
                first_turn = False
                defense_for_solo_used_this_turn = False
                continue

            # 战斗失败重启
            if defeated:
                if optional_action is not None:
                    optional_action.reset()  # A visible defeat ends this attempt, before any retry input.
                if attempt_budget is not None:
                    attempt_budget.defeat()  # Raise before selecting another retry.
                    if not defeat_action.submit(auto, retry=True, config=cfg, pause=sleep):
                        sleep(0.5)
                        continue
                else:
                    # Limit disabled: retain the original retry selection path.
                    dead_select = auto.find_element("battle/dead_all.png", find_type="image_with_multiple_targets")
                    if len(dead_select) == 3:
                        dead_select = sorted(dead_select, key=lambda y: y[1])
                        auto.mouse_click(dead_select[1][0], dead_select[1][1])
                    else:
                        confirm_button = auto.find_element("battle/dead_all_confirm_assets.png")
                        try:
                            my_scale = cfg.set_win_size / 1440
                            auto.mouse_click(
                                confirm_button[0] + 200 * my_scale,
                                confirm_button[1] - 350 * my_scale,
                            )
                        except:
                            continue

                    auto.click_element("battle/dead_all_confirm_assets.png")
                sleep(1)
                start_time = time.time()
                self.fail_times += 1
                if optional_action is not None:
                    optional_action.reset()
                defense_for_solo_used_this_turn = False
                first_turn = True
                if attempt_budget is None and self.fail_times >= 5:
                    return False
                continue

            if in_mirror and not cfg.fight_to_last_man and not infinite_battle:
                if dead_position := auto.find_element("battle/dead.png"):
                    my_scale = cfg.set_win_size / 1440
                    dead_bbox = (
                        dead_position[0] - 100 * my_scale,
                        dead_position[1] - 30 * my_scale,
                        dead_position[0] + 100 * my_scale,
                        dead_position[1] + 30 * my_scale,
                    )
                    ocr_result = auto.find_language_text("阵亡", "dead", dead_bbox)
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

            # 如果正在战斗待机界面
            # 更新回合数
            if infinite_battle and defense_on_turn1:
                try:
                    sc = ImageUtils.crop(np.array(auto.screenshot), turn_ocr_bbox)
                    result = ocr.run(sc)
                    ocr_result = [result.txts[i] for i in range(len(result.txts))]
                    ocr_result = "".join(ocr_result)
                    # 用正则匹配字符串里的数字
                    m = re.search(r"\d+", ocr_result)
                    if m:
                        self.cur_turn = int(m.group())
                    else:
                        self.cur_turn = -1
                    if self.cur_turn == 1:
                        first_turn = True
                except:
                    self.cur_turn = -1  # 表示识别失败

            if fail_count >= 10 or self.identify_keyword_turn is False:
                # 如果多次识别不到战斗界面
                try:
                    turn_bbox = ImageUtils.get_bbox(ImageUtils.load_image("battle/turn_assets.png"))
                    sc = ImageUtils.crop(np.array(auto.screenshot), turn_bbox)
                    sc = cv2.inRange(sc, 50, 255)
                    result = ocr.run(sc)
                    ocr_result = [result.txts[i] for i in range(len(result.txts))]
                    ocr_result = "".join(ocr_result).lower()
                except:
                    ocr_result = ""
                if "turn" in ocr_result:
                    perform_battle_operation()
                    chance = self.INIT_CHANCE
                    waiting = self._update_wait_time(waiting, False, total_count)
                    self.identify_keyword_turn = False
                    continue
            elif fail_count >= 5:
                if auto.click_element("battle/turn_assets.png") or auto.find_element("battle/win_rate_assets.png"):
                    perform_battle_operation()
                    chance = self.INIT_CHANCE
                    waiting = self._update_wait_time(waiting, False, total_count)
                    continue
            else:
                if auto.find_element("battle/more_information_assets.png") or auto.find_element(
                    "battle/win_rate_assets.png"
                ):
                    perform_battle_operation()
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
                    ocr_result = "".join(ocr_result).lower()
                except:
                    ocr_result = ""
                if (
                    "turn" in ocr_result
                    or auto.click_element("battle/turn_assets.png")
                    or auto.find_element("battle/win_rate_assets.png")
                    or auto.find_element("battle/win_rate_card.png", threshold=0.75)
                ):
                    perform_battle_operation()
                    chance = self.INIT_CHANCE
                    waiting = self._update_wait_time(waiting, False, total_count)
                    continue
            if chance == 1:
                if not infinite_battle:
                    auto.mouse_to_blank()
                if auto.find_language_text("胜率", "rate"):
                    perform_battle_operation()
                    chance = self.INIT_CHANCE
                    waiting = self._update_wait_time(waiting, False, total_count)
                    sleep(1)
                    if not auto.find_element("battle/pause_assets.png"):
                        self.mouse_click_rate = True
                    continue
            if self.mouse_click_rate:
                if auto.find_element("battle/win_rate_card.png", threshold=0.75):
                    perform_battle_operation()
                    chance = self.INIT_CHANCE
                    waiting = self._update_wait_time(waiting, False, total_count)

            # 如果战斗中途出现事件
            if (
                choice_event_handling
                and auto.find_element("event/choices_assets.png")
                and auto.find_element("event/select_first_option_assets.png")
            ):
                if event_chance > 5:
                    auto.click_element("event/select_first_option_assets.png")
                    event_chance -= 1
                elif event_chance > 0:
                    auto.click_element(
                        "event/select_first_option_assets.png",
                        find_type="image_with_multiple_targets",
                    )
                    event_chance -= 1
                else:
                    auto.click_element(
                        "event/select_first_option_assets.png",
                        find_type="image_with_multiple_targets",
                    )
                    finishes_bbox = ImageUtils.get_bbox(ImageUtils.load_image("event/continue_assets.png"))
                    if auto.find_text_element(
                        [
                            "conti",
                            "proc",
                            "comme",
                            "choices",
                            "confirm",
                            "行判",
                            "始战",
                            "继续",
                        ],
                        finishes_bbox,
                    ):
                        auto.mouse_click(
                            (finishes_bbox[0] + finishes_bbox[2]) // 2,
                            (finishes_bbox[1] + finishes_bbox[3]) // 2,
                        )
                        if infinite_battle:
                            continue
                        break
                    else:
                        event_chance = -1

            if choice_event_handling and auto.find_element("event/perform_the_check_feature_assets.png"):
                if event_excluded_sinners:
                    if not event_check_active:
                        event_handling.reset_exclusion_attempts()
                    event_check_active = True
                    event_handling.decision_event_handling(excluded_sinners=event_excluded_sinners)
                    if event_handling.exclusion_exhausted:
                        return BattleEventOutcome.EXCLUDED_EXHAUSTED
                else:
                    event_handling.decision_event_handling()
            elif event_check_active:
                event_handling.reset_exclusion_attempts()
                event_check_active = False
            if choice_event_handling:
                if auto.click_element("event/continue_assets.png"):
                    continue
                if auto.click_element("event/proceed_assets.png"):
                    continue
                if auto.click_element("event/commence_assets.png"):
                    continue
                if auto.click_element("event/skip_assets.png", times=6):
                    continue
            if auto.find_element("mirror/road_in_mir/select_encounter_reward_card_assets.png"):
                if infinite_battle:
                    continue
                break
            if not self.is_tool:
                # 点击中心以跳过播报员播报加速结算动画
                random_number = random.randint(-10, 10)
                width = int(cfg.set_win_size * 16 / 9)
                height = cfg.set_win_size
                center_x = width // 2
                center_y = height // 2
                auto.mouse_click(center_x - random_number, center_y + random_number, times=1)
                sleep(0.15)

            # 战斗结束，进入结算页面
            if auto.click_element("battle/battle_finish_confirm_assets.png", click=False) or auto.find_element(
                "mirror/claim_reward/battle_statistics_assets.png"
            ):
                sleep(1)
                if auto.click_element("base/leave_up_assets.png"):
                    auto.click_element("base/leave_up_confirm_assets.png")
                    continue
                # 为某些人在副本战斗过程中启动脚本任务进行收尾
                if self.first_battle:
                    if (
                        auto.find_element("battle/clear_rewards_EXP_1_assets.png")
                        or auto.find_element("battle/clear_rewards_EXP_2_assets.png")
                        or auto.find_element("battle/clear_rewards_EXP_3_assets.png")
                    ):
                        first_battle_reward = "EXP"
                    if auto.find_element("battle/clear_rewards_thread_assets.png"):
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
            if chance <= (self.INIT_CHANCE // 2 + 1) and auto.find_element("teams/identify_assets.png"):
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

    @staticmethod
    def _calculate_skills_position(
        skill_positions: list[list],
        gear_left: tuple,
        skill_nums: int,
        custom_tune: Optional[Callable[[list, int, int, float], list]] = None,
    ) -> None:
        """计算划线的技能位置(也是守备的位置)
        专门写一个方便修改
        直接修改传入的`skill_positions`, 故不返回值
        """
        scale: float = cfg.set_win_size / 1440
        skill_size: float = 161 * scale
        x_offset: float = 220 - 4.5 * skill_nums
        y_offset: float = 250

        for index in range(skill_nums):
            pos = [
                gear_left[0] + x_offset * scale + skill_size * index,
                gear_left[1] + y_offset * scale,
            ]
            if custom_tune is not None:
                pos: list = custom_tune(pos, index, skill_nums, scale)
            skill_positions.append(pos)

    @staticmethod
    def _get_lower_row_skill_indexes(
        skill_3_indexes: set[int],
        skill_nums: int,
        prioritize_skill_3: bool,
    ) -> set[int]:
        """Return slots that should use the lower skill row.

        ``find_skill3`` identifies slots whose upper option is skill 3. Avoid mode
        switches those slots to the lower row; prioritize mode switches the rest.
        """
        valid_indexes = set(range(1, skill_nums + 1))
        skill_3_indexes = skill_3_indexes & valid_indexes
        if prioritize_skill_3:
            return valid_indexes - skill_3_indexes
        return skill_3_indexes

    @staticmethod
    def _chain_battle(prioritize_skill_3: bool = False) -> bool:
        try:
            scale = cfg.set_win_size / 1440

            gear_left = auto.find_element("battle/gear_left.png")
            gear_right = auto.find_element("battle/gear_right.png")
            if gear_left is None or gear_right is None:
                return False

            gear_1 = [gear_left[0] + 94 * scale, gear_left[1] - 37 * scale]
            gear_2 = [gear_right[0] - 100 * scale, gear_right[1]]

            bbox = (gear_1[0], gear_1[1] - 15 * scale, gear_2[0], gear_1[1])

            skill_nums = int((bbox[2] - bbox[0]) / (145 * scale))
            if skill_nums <= 0:
                return False

            if skill_nums >= 10:
                bbox = (bbox[0] + 50 * scale, bbox[1], bbox[2], bbox[3])

            sc = auto.get_screenshot_crop(bbox)

            skill_3_matches = []
            for sin_color in sins.values():
                skill_3_matches.extend(find_skill3(sc, sin_color))
            skill_3_indexes = {
                round(match[0] / (145 * scale)) for match in skill_3_matches
            }
            lower_row_indexes = Battle._get_lower_row_skill_indexes(
                skill_3_indexes,
                skill_nums,
                prioritize_skill_3,
            )

            skill_list = [gear_left]

            def custom_tune(
                pos: list,
                index: int,
                skill_nums: int,
                scale: float,
                *,
                reverse: int = 1,
            ) -> list:
                """针对上方的技能位置调整, 呈三角形偏移"""
                center = skill_nums // 2

                if index <= center:
                    pos[0] += (center - index) * 8 * scale * reverse
                else:
                    pos[0] -= (index - center) * 8 * scale * reverse
                return pos

            Battle._calculate_skills_position(
                skill_list,
                (gear_left[0], gear_left[1] - 125 * scale),
                skill_nums,
                custom_tune=custom_tune,
            )
            for index in sorted(lower_row_indexes):
                skill_list[index][1] += 125 * scale
                skill_list[index] = custom_tune(skill_list[index], index, skill_nums, scale, reverse=-1)

            skill_list.append([gear_right[0] + 5 * skill_nums * scale, gear_right[1] + 150 * scale])

            auto.mouse_drag_link(skill_list)

            auto.mouse_to_blank()

            sleep(0.5)

            auto.key_press("enter")

            sleep(1)
            return True
        except Exception:
            return False

    @staticmethod
    def _prepare_defense() -> bool:
        """Click lower slots into guard without submitting the action chain."""
        try:
            scale = cfg.set_win_size / 1440
            left = auto.find_element("battle/gear_left.png", threshold=0.9)
            right = auto.find_element("battle/gear_right.png", threshold=0.9)
            points = lower_row_points(left, right, scale) if left and right else []
            if not points:
                return False
            for x, y in points:
                auto.mouse_click(x, y)
                sleep(cfg.mouse_action_interval if cfg.simulator else cfg.mouse_action_interval // 1.5)
            return True
        except userStopError:
            raise
        except Exception as error:
            log.warning(f"守备准备未完成，继续一般战斗：{error}")
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
            Battle._calculate_skills_position(skill_list, gear_left, skill_nums)

            for skill in skill_list:
                auto.mouse_click(skill[0], skill[1])
                if cfg.simulator:
                    sleep(cfg.mouse_action_interval)
                else:
                    sleep(cfg.mouse_action_interval // 1.5)

            skill_list.insert(0, gear_left)
            skill_list.append([gear_right[0] + 5 * skill_nums * scale, gear_right[1] + 150 * scale])

            auto.mouse_drag_link(skill_list)

            auto.mouse_to_blank(move_back=move_back)

            sleep(1)
            return True
        except Exception:
            return False
