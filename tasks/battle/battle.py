from time import sleep

import pyautogui

from module.automation import auto
from module.decorator.decorator import begin_and_finish_time_log
from module.logger import log
from tasks.base.retry import retry
from tasks.event.event_handling import EventHandling


def to_battle():
    loop_count = 15
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
        if loop_count < 5:
            auto.model = 'aggressive'
        if loop_count < 0:
            msg = "超出最大尝试次数,未能进入战斗"
            log.ERROR(msg)
            return False


def update_wait_time(time: float = None, fail_flag: bool = False, total_count: int = 1):
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
def battle(first_battle=False):
    INIT_CHANCE = 16
    chance = INIT_CHANCE
    waiting = update_wait_time()
    total_count = 0
    fail_count = 0
    in_mirror = False
    first_battle_reward = None
    event_chance = 15

    while True:
        # 自动截图
        if auto.take_screenshot() is None:
            continue

        # 战斗开始前的加载
        if auto.find_element("base/waiting_assets.png"):
            sleep(0.5)
            continue

        # 判断是否为镜牢战斗
        if in_mirror is False and auto.find_element("battle/in_mirror_assets.png"):
            in_mirror = True

        # 如果正在交战过程
        if auto.find_element("battle/pause_assets.png"):
            sleep(2 * waiting)  # 战斗播片中增大间隔
            chance = INIT_CHANCE
            continue

        # 如果正在战斗待机界面
        if auto.click_element("battle/turn_assets.png") or auto.find_element("battle/win_rate_assets.png"):
            auto.mouse_click_blank()
            pyautogui.press('p')
            sleep(0.5)
            pyautogui.press('enter')
            chance = INIT_CHANCE
            msg = f"使用P+Enter开始战斗"
            log.DEBUG(msg)
            waiting = update_wait_time(waiting, False, total_count)
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
            if first_battle:
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
        retry()

        chance -= 1
        sleep(waiting)
        # 更新等待时间
        waiting = update_wait_time(waiting, True, total_count)
        # 统计失败次数
        fail_count += 1
        if chance < 0:
            break

    if total_count == 0:
        match_success_rate = 100
    else:
        #保留最多三位小数
        match_success_rate = (1 - fail_count / total_count) * 100
    msg = f"此次战斗匹配失败次数{fail_count} 匹配总次数{total_count} 匹配成功率{match_success_rate}%"
    log.DEBUG(msg)
    if first_battle:
        return first_battle_reward
    else:
        return None
