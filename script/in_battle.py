from time import sleep

import pyautogui

from command.get_position import get_pic_position, get_pic_position_without_cap
from command.mouse_activity import mouse_click, mouse_click_blank
from os import environ

from my_decorator.decorator import begin_and_finish_log,begin_and_finish_time_log
from my_log.my_log import my_log
from my_ocr.ocr import commom_ocr, commom_gain_text, commom_all_ocr
from script.decision_event_handling import decision_event_handling


def update_wait_time(time:float = None, fail_flag: bool = False,total_count:int = 1):
     
    MAX_WAITING = 3.0 # 最大等待时间
    MIN_WAITING = 0.5 # 最小等待时间
    INIT_WAITING = 1.5 # 初始等待时间
    fail_adjust = 0.5
    success_adjust = -0.2
    if time is None:
        return INIT_WAITING
    
    total_count = total_count if total_count > 0 else 1 # 防止除0
    adjust = fail_adjust if fail_flag else success_adjust
    new_time = time + adjust / (total_count ** 0.5) # 平方根调整
    
    new_time = min(new_time, MAX_WAITING) # 防止超过最大等待时间
    new_time = max(new_time, MIN_WAITING) # 防止低于最小等待时间
    if fail_flag:
        msg = f"匹配失败，等待时间从{time:.3f}调整为{new_time:.3f}"
        my_log("debug", msg)
        
    return new_time


@begin_and_finish_time_log(task_name="一次战斗")
def battle():
    INIT_CHANCE = 15
    chance = INIT_CHANCE
    waiting = update_wait_time()
    total_count= 0
    fail_count = 0
    in_mirror = False

    
    while get_pic_position("./pic/wait.png"): # 战斗开始前的加载
        sleep(waiting)
    sleep(1.5 * waiting)

    while True:
        total_count += 1
        if in_mirror is False and get_pic_position("./pic/battle/in_mirror_battle.png"):
            in_mirror = True
        
        # 如果正在交战过程
        if get_pic_position("./pic/battle/pause.png"):
            sleep(2 * waiting) # 战斗播片中增大间隔
            chance = INIT_CHANCE
            continue
        # 如果正在战斗待机界面
        elif get_pic_position("./pic/battle/in_battle.png"):
            pyautogui.press('p')
            sleep(0.5)
            pyautogui.press('enter')
            chance = INIT_CHANCE
            msg = f"使用P+Enter开始战斗"
            my_log("debug", msg)
            mouse_click_blank()
            waiting = update_wait_time(waiting,False,total_count)
            continue     
        # 如果战斗中途出现事件
        elif get_pic_position("./pic/event/skip.png"):
            mouse_click(get_pic_position("./pic/event/skip.png"), 5)
            if get_pic_position("./pic/battle/event_choices.png") and get_pic_position(
                    "./pic/battle/random_to_choose_event.png"):
                mouse_click(get_pic_position("./pic/battle/random_to_choose_event.png"))
            if get_pic_position("./pic/event/perform_the_check_features_1.png") and get_pic_position(
                    "./pic/event/perform_the_check_features_2.png"):
                decision_event_handling()
            if continue_button := get_pic_position("./pic/event/continue.png"):
                mouse_click(continue_button)
            if process_button := get_pic_position("./pic/battle/proceed.png"):
                mouse_click(process_button)
            chance = INIT_CHANCE
            continue
        # 战斗结束，进入结算页面
        elif get_pic_position("./pic/battle/battle_finish_confirm.png"):
            sleep(1)
            if get_pic_position("./pic/battle/level_up_message.png"):
                level_up_leave()
                chance = INIT_CHANCE
                continue
            elif get_pic_position("./pic/battle/level_up_message2.png"):
                level_up_leave()
                chance = INIT_CHANCE
                continue
            # 为某些人在副本战斗过程中启动脚本任务进行收尾
            if environ.get('rewards') == '0':
                if get_pic_position("./pic/battle/rewards/clear_rewards.png"):
                    if get_pic_position("./pic/battle/rewards/training_ticket_IV.png") or \
                            get_pic_position("./pic/battle/rewards/training_ticket_III.png") or \
                            get_pic_position("./pic/battle/rewards/training_ticket_II.png"):
                        environ['rewards'] = "1"
                    elif get_pic_position("./pic/battle/rewards/thread.png"):
                        environ['rewards'] = "2"
            mouse_click(get_pic_position("./pic/battle/battle_finish_confirm.png"))
            break
        elif get_pic_position("./pic/scenes/road_in_mirror.png"):
            break
        elif get_pic_position("./pic/mirror/acquire_ego_gift.png"):
            break
        elif get_pic_position("./pic/mirror/select_encounter_reward_card.png"):
            break
        elif chance <= (INIT_CHANCE // 2 + 1) and get_pic_position("./pic/teams/formation_features.png"):
            break
        # 如果战斗结束进入黑屏
        elif get_pic_position("./pic/wait.png"):
            sleep(waiting)
            chance = INIT_CHANCE
            continue
        # 如果在镜牢战斗，并且有角色死亡，退出战斗
        elif in_mirror and get_pic_position("./pic/battle/dead.png", 0.9) and battle_ocr():
            sleep(2)
            if get_pic_position("./pic/battle/dead.png", 0.9):
                msg = f"角色死亡，退出战斗"
                my_log("info", msg)
                while give_up_button := get_pic_position("./pic/battle/give_up.png") is None:
                    mouse_click(get_pic_position("./pic/battle/setting.png"))
                mouse_click(get_pic_position("./pic/battle/give_up.png"))
                break
        # 如果交战过程误触，导致战斗暂停
        elif get_pic_position("./pic/battle/continue.png"):
            mouse_click(get_pic_position("./pic/battle/continue.png"))
            chance = INIT_CHANCE
            continue
        # 两种升级可能出现的图片识别
        elif get_pic_position("./pic/battle/level_up_message.png"):
            level_up_leave()
            chance = INIT_CHANCE
            continue
        elif get_pic_position("./pic/battle/level_up_message2.png"):
            level_up_leave()
            chance = INIT_CHANCE
            continue
        # 如果网络波动，需要点击重试
        elif get_pic_position("./pic/scenes/network/retry_countdown.png"):
            sleep(5)
            if get_pic_position("./pic/scenes/network/retry.png"):
                mouse_click(get_pic_position("./pic/scenes/network/retry.png"))
            chance = INIT_CHANCE
            continue
        elif get_pic_position("./pic/scenes/network/retry.png"):
            mouse_click(get_pic_position("./pic/scenes/network/retry.png"))
            chance = INIT_CHANCE
            continue
        elif get_pic_position("./pic/scenes/network/retry_countdown.png") \
                or get_pic_position_without_cap("./pic/scenes/network/retry.png") \
                or get_pic_position_without_cap("./pic/scenes/network/try_again.png"):
            mouse_click(get_pic_position_without_cap("./pic/scenes/network/retry.png"))
        else:
            chance -= 1
            sleep(waiting)
            # 更新等待时间
            waiting = update_wait_time(waiting,True,total_count)
            # 统计失败次数 
            fail_count += 1
        if chance < 0:
            break

    msg = f"匹配失败次数{fail_count} 匹配总次数{total_count} 匹配成功率{(1 - fail_count / total_count):.3f}"
    my_log("debug", msg)


def battle_ocr():
    dead = commom_ocr("./pic/battle/dead.png", 85, 20)
    text = commom_gain_text(dead[0])
    text_values = [d.get("text", "") for d in text]
    if any("dead" in t.lower() for t in text_values):
        msg = f"OCR检测到单词{"dead"}"
        my_log("debug", msg)
        return True
    msg = f"OCR没有检测到单词{"dead"}"
    my_log("debug", msg)
    return False


def level_up_leave(word="confirm"):
    leave = commom_gain_text(commom_all_ocr()[0])
    p = []
    for b in leave:
        if word in b['text'].lower():
            box = b['box']
            p = [(box[0][0] + box[2][0]) // 2, (box[0][1] + box[2][1]) // 2]
            break
    mouse_click(p)
