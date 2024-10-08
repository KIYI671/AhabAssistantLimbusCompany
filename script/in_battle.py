from time import sleep

import pyautogui

from command.get_position import get_pic_position, get_pic_position_without_cap
from command.mouse_activity import mouse_click, mouse_click_blank
from os import environ

from my_decorator.decorator import begin_and_finish_log
from my_log.my_log import my_log
from my_ocr.ocr import commom_ocr, commom_gain_text, commom_all_ocr
from script.decision_event_handling import decision_event_handling


@begin_and_finish_log(task_name="一次战斗")
def battle():
    chance = 5
    in_mirror = False
    while True:
        if in_mirror is False and get_pic_position("./pic/battle/in_mirror_battle.png"):
            in_mirror = True
        # 如果在镜牢战斗，并且有角色死亡，退出战斗
        if in_mirror and get_pic_position("./pic/battle/dead.png", 0.9) and battle_ocr():
            sleep(2)
            if get_pic_position("./pic/battle/dead.png", 0.9):
                msg = f"角色死亡，退出战斗"
                my_log("info", msg)
                while give_up_button := get_pic_position("./pic/battle/give_up.png") is None:
                    mouse_click(get_pic_position("./pic/battle/setting.png"))
                mouse_click(get_pic_position("./pic/battle/give_up.png"))
                break
        # 如果正在战斗待机界面
        elif get_pic_position("./pic/battle/in_battle.png"):
            pyautogui.press('p')
            sleep(0.5)
            pyautogui.press('enter')
            chance = 5
            msg = f"使用P+Enter开始战斗"
            my_log("debug", msg)
            mouse_click_blank()
            continue
        # 如果正在交战过程
        elif get_pic_position("./pic/battle/pause.png"):
            sleep(2)
            chance = 5
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
            chance = 5
            continue
        # 如果战斗结束进入黑屏
        elif get_pic_position("./pic/wait.png"):
            sleep(2)
            chance = 5
            continue
        # 如果交战过程误触，导致战斗暂停
        elif get_pic_position("./pic/battle/continue.png"):
            mouse_click(get_pic_position("./pic/battle/continue.png"))
            chance = 5
            continue
        # 两种升级可能出现的图片识别
        elif get_pic_position("./pic/battle/level_up_message.png"):
            level_up_leave()
            chance = 5
            continue
        elif get_pic_position("./pic/battle/level_up_message2.png"):
            level_up_leave()
            chance = 5
            continue
        # 如果网络波动，需要点击重试
        elif get_pic_position("./pic/scenes/network/retry_countdown.png"):
            sleep(5)
            if get_pic_position("./pic/scenes/network/retry.png"):
                mouse_click(get_pic_position("./pic/scenes/network/retry.png"))
            chance = 5
            continue
        elif get_pic_position("./pic/scenes/network/retry.png"):
            mouse_click(get_pic_position("./pic/scenes/network/retry.png"))
            chance = 5
            continue
        # 战斗结束，进入结算页面
        elif get_pic_position("./pic/battle/battle_finish_confirm.png"):
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
        elif get_pic_position("./pic/scenes/network/retry_countdown.png") \
                or get_pic_position_without_cap("./pic/scenes/network/retry.png") \
                or get_pic_position_without_cap("./pic/scenes/network/try_again.png"):
            mouse_click(get_pic_position_without_cap("./pic/scenes/network/retry.png"))
        elif get_pic_position("./pic/scenes/road_in_mirror.png"):
            break
        elif get_pic_position("./pic/mirror/acquire_ego_gift.png"):
            break
        elif chance <= 3 and get_pic_position("./pic/teams/formation_features.png"):
            break
        else:
            chance -= 1
            sleep(3)
        if chance < 0:
            break


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
