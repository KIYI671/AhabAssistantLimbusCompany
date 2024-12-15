from time import sleep

import pyautogui

from my_decorator.decorator import begin_and_finish_time_log
from my_error.my_error import backMainWinError
from my_log.my_log import my_log
from script.check_scene import where_am_i
from command.get_position import get_pic_position
from script.in_battle import battle
from command.mouse_activity import mouse_click, mouse_click_blank
from script.some_script_in_MD import get_reward_card


@begin_and_finish_time_log(task_name="返回主界面")
def back_init_menu():
    loop_count = 0
    while (where := where_am_i()) != 30:
        msg = f"识别得知此时位置为代号{where}"
        my_log("debug", msg)

        if where == 51:
            mouse_click_blank()

        # 战斗途中，先战斗完再返回
        elif where == 2:
            battle()

        # 取消ego选择
        elif where == 3:
            mouse_click_blank()
            continue

        # 战斗结算的确认
        elif where == 4 or where == 5:
            mouse_click(get_pic_position("./pic/battle/battle_finish_confirm.png"))

        # 左上角存在退出按键
        elif where == 10 or where == 11 or 41 <= where <= 46:
            mouse_click(get_pic_position("./pic/scenes/the_back_button.png"))

        # 镜本地图中，直接返回!!!
        elif where == 12 or where == 16:
            mouse_click(get_pic_position("./pic/mirror/setting.png"))
            mouse_click(get_pic_position("./pic/mirror/to_window.png"))
            mouse_click(get_pic_position("./pic/mirror/forfeit.png"))
            mouse_click(get_pic_position("./pic/mirror/to_window_confirm.png"))
        elif where == 17:
            mouse_click(get_pic_position("./pic/mirror/to_window.png"))
            mouse_click(get_pic_position("./pic/mirror/forfeit.png"))
            mouse_click(get_pic_position("./pic/mirror/to_window_confirm.png"))

        elif where == 15:
            pass

        # 镜牢中需要esc的情况
        elif where == 13 or where == 14:
            pyautogui.press('esc')

        # 镜牢结算时退出!!!
        elif where == 18:
            mouse_click(get_pic_position("./pic/mirror/win_and_claim_rewards.png"))
            mouse_click(get_pic_position("./pic/mirror/claim.png"))
            mouse_click(get_pic_position("./pic/mirror/claim_confirm.png"))
        elif where == 19:
            mouse_click(get_pic_position("./pic/mirror/claim.png"))
            mouse_click(get_pic_position("./pic/mirror/claim_confirm.png"))

        elif where == 20:
            get_reward_card()

        # 无退出按键，但是可以使用esc按键返回
        elif 31 <= where <= 35:
            mouse_click(get_pic_position("./pic/scenes/init_window.png"))

        # 无退出按键，但是可以使用esc按键返回
        elif 36 <= where <= 39:
            pyautogui.press('esc')
            sleep(1)

        # 在剧情中退出!!!
        elif where == 40:
            mouse_click(get_pic_position("./pic/scenes/plot/plot_setting_menu.png"))
            mouse_click(get_pic_position("./pic/scenes/plot/plot_quit.png"))
            mouse_click(get_pic_position("./pic/scenes/plot/skip_plot_confirm.png"))

        # 升级页面
        elif where == 50:
            mouse_click(get_pic_position("./pic/battle/level_up_confirm.png"))

        # 等待加载情况
        elif where == 52:
            sleep(2)
            continue

        elif where == -1:
            pyautogui.press('esc')
            sleep(2)
            continue

        loop_count += 1

        if loop_count > 30:
            my_log("warning", "无法返回主界面，不能进行下一步,请手动操作重试")
            raise backMainWinError("无法返回主界面，不能进行下一步")
