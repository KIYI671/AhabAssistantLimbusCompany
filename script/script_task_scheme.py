from sys import exc_info
from time import sleep
from traceback import format_exception

import pyautogui
from PyQt5.QtCore import QThread, pyqtSignal, QMutex

from command.adjust_position_and_siz import adjust_position_and_size, reset_win
from command.get_position import get_pic_position
from my_decorator.decorator import begin_and_finish_log,begin_and_finish_time_log
from my_error.my_error import withOutGameWinError, userStopError, noSavedPresetsError, \
    unexpectNumError, cannotOperateGameError, netWorkUnstableError, backMainWinError, notWaitError, withOutPicError, \
    withOutAdminError
from my_log.my_log import my_log
from script.check_scene import where_am_i
from command.get_win_handle import get_win_handle
from script.in_battle import battle
from script.make_enkephalin_module import lunacy_to_enkephalin, make_enkephalin_module
from command.mouse_activity import mouse_click_blank, mouse_click
from command.use_yaml import get_yaml_information, save_yaml
from script.back_init_menu import back_init_menu
from script.get_prize import get_pass_prize, get_mail_prize
from script.luxcavation import EXP_luxcavation, thread_luxcavation
from script.mirror import execute_a_mirror
from script.team_formation import select_battle_team
from script.team_preparation import team_preparation
from os import environ

all_systems = {0: "burn", 1: "bleed", 2: "tremor", 3: "rupture", 4: "poise",
               5: "sinking", 6: "charge", 7: "slash", 8: "pierce", 9: "blunt"}
all_sinners_name = ["YiSang", "Faust", "DonQuixote", "Ryoshu", "Meursault", "HongLu",
                    "Heathcliff", "Ishmael", "Rodion", "Sinclair", "Outis", "Gregor"]
all_sinner = {
    "YiSang": 1, "Faust": 2, "DonQuixote": 3,
    "Ryoshu": 4, "Meursault": 5, "HongLu": 6,
    "Heathcliff": 7, "Ishmael": 8, "Rodion": 9,
    "Dante": 10,
    "Sinclair": 11, "Outis": 12, "Gregor": 13
}


@begin_and_finish_time_log(task_name="一次经验本")
# 一次经验本的过程
def onetime_EXP_process(team):
    EXP_luxcavation()
    select_battle_team(team)
    team_preparation()
    battle()
    back_init_menu()
    make_enkephalin_module()


@begin_and_finish_time_log(task_name="一次纽本")
# 一次纽本的过程
def onetime_thread_process(team):
    thread_luxcavation()
    select_battle_team(team)
    team_preparation()
    battle()
    back_init_menu()
    make_enkephalin_module()


@begin_and_finish_time_log(task_name="一次镜牢")
# 一次镜牢的过程
def onetime_mir_process(the_selected_team_setting):
    # 读取队伍配置、顺序
    my_team = {}
    sinner_team = []
    shop_sell_list = []
    for sinner in all_sinners_name:
        sinner_order = sinner + "_order"
        if the_selected_team_setting[sinner]:
            my_team[sinner] = int(the_selected_team_setting[sinner_order])
    my_sorted_team = dict(sorted(my_team.items(), key=lambda item: item[1]))
    for sinner in my_sorted_team:
        sinner_team.append(all_sinner[sinner])
    for num, shop_system in all_systems.items():
        if the_selected_team_setting[shop_system]:
            shop_sell_list.append(shop_system)
    # 进行一次镜牢
    while execute_a_mirror(sinner_team, the_selected_team_setting["all_teams"], shop_sell_list,
                           all_systems[the_selected_team_setting["all_system"]]) is not True:
        msg = f"无人生还，重启镜牢"
        my_log("info", msg)
        while not get_pic_position("./pic/mirror/setting.png"):
            pyautogui.press('esc')
        mouse_click(get_pic_position("./pic/mirror/setting.png"))
        mouse_click(get_pic_position("./pic/mirror/mirror_setting_forfeit.png"))
        mouse_click(get_pic_position("./pic/mirror/claim_confirm.png"))
        sleep(2)
        mouse_click(get_pic_position("./pic/mirror/forfeit_defeat_confirm.png"))
        if claim_rewards := get_pic_position("./pic/mirror/claim_rewards.png"):
            mouse_click(claim_rewards)
            sleep(1)
        mouse_click(get_pic_position("./pic/mirror/give_up_rewards.png"))
        mouse_click(get_pic_position("./pic/mirror/claim_confirm.png"))

    back_init_menu()
    make_enkephalin_module()


def script_task():
    all_setting = {
        "select_task": {"set_windows": True, "daily_task": False, "get_reward": False, "buy_enkephalin": False,
                        "mirror": False},
        "set_win": {"set_win_size": 0, "set_win_position": 0, "set_reduce_miscontact": 0},
        "set_daily": {"set_EXP_count": 0, "set_thread_count": 0},
        "set_prize": {"set_get_prize": 0},
        "set_buy": {"set_lunacy_to_enkephalin": 0},
        "set_mir": {"set_mirror_count": 0,
                    "team1": False, "team2": False, "team3": False, "team4": False, "team5": False, "team6": False,
                    "team7": False}
    }

    # 从配置文件中读取任务安排
    config_datas = get_yaml_information()
    for key, value in all_setting.items():
        for key_2, value_2 in all_setting[key].items():
            temp = config_datas.get(key_2)
            if temp:
                all_setting[key][key_2] = temp

    # 对游戏窗口进行设置
    handle = get_win_handle()
    if all_setting["select_task"]["set_windows"]:
        if handle == None:
            my_log("error", "没有找到游戏窗口")
            raise withOutGameWinError("没有找到游戏窗口")
        win_size = all_setting["set_win"]["set_win_size"]
        environ['window_size'] = f"{win_size}"
        adjust_position_and_size(handle)
        # back_init_menu()
        # make_enkephalin_module()

        environ['rewards'] = "0"
    # 如果是战斗中，先处理战斗
    if (where := where_am_i()) == 2:
        battle()
    elif where == 3:
        mouse_click_blank()
        battle()

    # 执行日常刷本任务
    if all_setting["select_task"]["daily_task"]:
        select_team = config_datas["all_teams"]
        back_init_menu()
        make_enkephalin_module()
        exp_times = all_setting["set_daily"]["set_EXP_count"]
        exp_times = exp_times if (environ.get('rewards') != "1") else exp_times - 1
        thread_times = all_setting["set_daily"]["set_thread_count"]
        thread_times = thread_times if (environ.get('rewards') != "2") else thread_times - 1
        for i in range(exp_times):
            onetime_EXP_process(select_team)
        for i in range(thread_times):
            onetime_thread_process(select_team)
    # 执行奖励领取任务
    if all_setting["select_task"]["get_reward"]:
        if all_setting["set_prize"]["set_get_prize"] == 0:
            back_init_menu()
            get_pass_prize()
            back_init_menu()
            get_mail_prize()
            back_init_menu()
        elif all_setting["set_prize"]["set_get_prize"] == 1:
            back_init_menu()
            get_pass_prize()
            back_init_menu()
        else:
            back_init_menu()
            get_mail_prize()
            back_init_menu()

    # 执行狂气换饼任务
    if all_setting["select_task"]["buy_enkephalin"]:
        back_init_menu()
        lunacy_to_enkephalin(times=all_setting["set_buy"]["set_lunacy_to_enkephalin"])

    # 执行镜牢任务
    if all_setting["select_task"]["mirror"]:
        all_teams = ["team1", "team2", "team3", "team4", "team5", "team6", "team7"]
        mir_times = all_setting["set_mir"]["set_mirror_count"]
        all_my_team_setting = []
        for team in all_teams:
            if all_setting["set_mir"][team]:
                sequence = "_order"
                team_sequence = team + sequence
                team_order = int(config_datas[team_sequence])
                setting = "_setting"
                team_setting = team + setting
                my_team_setting = config_datas[team_setting]
                this_team_setting = [team_order, my_team_setting, team_sequence]
                all_my_team_setting.append(this_team_setting)
        if len(all_my_team_setting) != 0:
            while mir_times > 0:
                the_selected_team_setting = None
                for t in all_my_team_setting:
                    if t[0] == 1:
                        the_selected_team_setting = t[1]
                        break
                onetime_mir_process(the_selected_team_setting)
                config_datas = get_yaml_information()
                for t in all_my_team_setting:
                    if t[0] == 1:
                        t[0] = len(all_my_team_setting)
                    else:
                        t[0] -= 1
                    config_datas[t[2]] = str(t[0])
                save_yaml(config_datas)
                mir_times -= 1
    if all_setting["set_win"]["set_reduce_miscontact"] == 0:
        reset_win(handle)


class my_script_task(QThread):
    # 定义信号
    finished_signal = pyqtSignal()

    def __init__(self):
        # 初始化，构造函数
        super().__init__()
        self.running = True
        self.exc_traceback = ''
        self.mutex = QMutex()

    def run(self):
        self.mutex.lock()

        try:
            self._run()
        except userStopError as e:
            self.exception = e
        except noSavedPresetsError as e:
            self.exception = e
        except unexpectNumError as e:
            self.exception = e
        except cannotOperateGameError as e:
            self.exception = e
        except netWorkUnstableError as e:
            self.exception = e
        except backMainWinError as e:
            self.exception = e
        except withOutGameWinError as e:
            self.exception = e
        except notWaitError as e:
            self.exception = e
        except withOutPicError as e:
            self.exception = e
        except withOutAdminError as e:
            self.exception = e
        except Exception as e:
            self.exception = e
            my_log("error", e)
        finally:
            if self.exc_traceback != '':
                self.exc_traceback = ''.join(
                    format_exception(*exc_info()))
                my_log('error', self.exc_traceback)
                self.mutex.unlock()

        self.finished_signal.emit()

    """def stop(self):
        self.running=False
        self.finished_signal.emit()"""

    def _run(self):
        script_task()
