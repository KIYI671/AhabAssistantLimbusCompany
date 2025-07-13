import ctypes
import os
import platform
import random
from sys import exc_info
from traceback import format_exception

from PyQt5.QtCore import QThread, pyqtSignal, QMutex
from playsound3 import playsound

from module.automation import auto
from module.config import cfg
from module.decorator.decorator import begin_and_finish_time_log
from module.logger import log
from module.my_error.my_error import userStopError, unableToFindTeamError, unexpectNumError, cannotOperateGameError, \
    netWorkUnstableError, backMainWinError, withOutGameWinError, notWaitError, withOutPicError, withOutAdminError
from module.screen import screen
from tasks.base.back_init_menu import back_init_menu
from tasks.base.make_enkephalin_module import lunacy_to_enkephalin, make_enkephalin_module
from tasks.battle import battle
from tasks.daily.get_prize import get_pass_prize, get_mail_prize
from tasks.daily.luxcavation import EXP_luxcavation, thread_luxcavation
from tasks.mirror.mirror import Mirror
from tasks.teams.team_formation import select_battle_team
from utils import pic_path
from utils.utils import get_day_of_week, calculate_the_teams

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
def onetime_EXP_process():
    if cfg.targeted_teaming_EXP:
        team = cfg.get_value(f"EXP_day_{calculate_the_teams()}")
    else:
        team = cfg.daily_teams
    EXP_luxcavation()
    select_battle_team(team)
    if battle.to_battle() is False:
        return False
    battle.fight()
    back_init_menu()
    make_enkephalin_module()


@begin_and_finish_time_log(task_name="一次纽本")
# 一次纽本的过程
def onetime_thread_process():
    if cfg.targeted_teaming_thread:
        team = cfg.get_value(f"thread_day_{get_day_of_week()}")
    else:
        team = cfg.daily_teams
    thread_luxcavation()
    select_battle_team(team)
    if battle.to_battle() is False:
        return False
    battle.fight()
    back_init_menu()
    make_enkephalin_module()


@begin_and_finish_time_log(task_name="一次镜牢")
# 一次镜牢的过程
def onetime_mir_process(the_selected_team_setting):
    # 读取队伍配置、顺序
    my_team = {}
    sinner_team = []
    shop_sell_list = []
    hard_switch = cfg.get_value("hard_mirror")
    no_weekly_bonuses = cfg.get_value('no_weekly_bonuses')
    fuse_switch = the_selected_team_setting['fuse']
    fuse_aggressive_switch = the_selected_team_setting['fuse_aggressive']
    dont_convert_starlight_to_cost = cfg.get_value("dont_convert_starlight_to_cost")
    dont_use_storaged_starlight = cfg.get_value("dont_use_storaged_starlight")
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
    try:
        mirror_adventure = Mirror(sinner_team, the_selected_team_setting["all_teams"], shop_sell_list, fuse_switch,
                                  all_systems[the_selected_team_setting["all_system"]], fuse_aggressive_switch,
                                  hard_switch, no_weekly_bonuses, dont_use_storaged_starlight, dont_convert_starlight_to_cost)
        if mirror_adventure.run():
            del mirror_adventure
            back_init_menu()
            make_enkephalin_module()
            return True
        else:
            return False
    except Exception as e:
        msg = f"镜牢行动出错: {e}"
        log.ERROR(msg)
        return False


def script_task():
    # 对游戏窗口进行设置
    screen.init_handle()
    if cfg.set_windows:
        screen.set_win()

    if cfg.language_in_game == "zh_cn":
        pic_path.insert(0, "zh_cn")

    if cfg.resonate_with_Ahab:
        random_number = random.randint(1, 4)
        playsound(f"assets/audio/This_is_all_your_fault_{random_number}.mp3")

    # 如果是战斗中，先处理战斗
    get_reward = None
    if auto.click_element("battle/turn_assets.png",take_screenshot=True):
        get_reward = battle.fight()

    # 执行日常刷本任务
    if cfg.daily_task:
        back_init_menu()
        make_enkephalin_module()
        exp_times = cfg.set_EXP_count
        if get_reward and get_reward == "EXP":
            exp_times -= 1
        thread_times = cfg.set_thread_count
        if get_reward and get_reward == "thread":
            thread_times -= 1
        for i in range(exp_times):
            onetime_EXP_process()
        for i in range(thread_times):
            onetime_thread_process()
    # 执行奖励领取任务
    if cfg.get_reward:
        if cfg.set_get_prize == 0:
            back_init_menu()
            get_pass_prize()
            back_init_menu()
            get_mail_prize()
            back_init_menu()
        elif cfg.set_get_prize == 1:
            back_init_menu()
            get_pass_prize()
            back_init_menu()
        else:
            back_init_menu()
            get_mail_prize()
            back_init_menu()

    # 执行狂气换饼任务
    if cfg.buy_enkephalin:
        back_init_menu()
        lunacy_to_enkephalin(times=cfg.set_lunacy_to_enkephalin)

    # 执行镜牢任务
    if cfg.mirror:
        all_teams = ["team1", "team2", "team3", "team4", "team5", "team6", "team7"]
        mir_times = cfg.set_mirror_count
        all_my_team_setting = []
        for team in all_teams:
            if cfg.get_value(team):
                sequence = "_order"
                team_sequence = team + sequence
                team_order = cfg.get_value(team_sequence)
                setting = "_setting"
                team_setting = team + setting
                my_team_setting = cfg.get_value(team_setting)
                this_team_setting = [team_order, my_team_setting, team_sequence]
                all_my_team_setting.append(this_team_setting)
        if len(all_my_team_setting) != 0:
            while mir_times > 0:
                the_selected_team_setting = None
                for this_team in all_my_team_setting:
                    if this_team[0] == 1:
                        the_selected_team_setting = this_team[1]
                        break
                mirror_result = onetime_mir_process(the_selected_team_setting)
                if mirror_result:
                    for this_team in all_my_team_setting:
                        if this_team[0] == 1:
                            this_team[0] = len(all_my_team_setting)
                        else:
                            this_team[0] -= 1
                        cfg.set_value(this_team[2], this_team[0])
                    mir_times -= 1
    if cfg.set_reduce_miscontact:
        screen.reset_win()

    if platform.system() == "Windows":
        after_completion = cfg.after_completion
        try:
            if after_completion == 1:
                os.system("rundll32.exe powrprof.dll,SetSuspendState Sleep")
            elif after_completion == 2:
                if platform.system() == "Windows":
                    os.system("rundll32.exe powrprof.dll,SetSuspendState Hibernate")
            elif after_completion == 3:
                if platform.system() == "Windows":
                    os.system("shutdown /s /t 30")
            elif after_completion == 4:
                if platform.system() == "Windows":
                    _, pid = ctypes.windll.user32.GetWindowThreadProcessId(screen.handle._hWnd, None)
                    os.system(f'taskkill /F /PID {pid}')
            elif after_completion == 5:
                if platform.system() == "Windows":
                    os.system("taskkill /f /im AALC.exe")
            elif after_completion == 6:
                if platform.system() == "Windows":
                    _, pid = ctypes.windll.user32.GetWindowThreadProcessId(screen.handle._hWnd, None)
                    os.system(f'taskkill /F /PID {pid}')
                    os.system("taskkill /f /im AALC.exe")
        except Exception as e:
            log.ERROR(f"脚本结束后的操作失败: {e}")


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
        except unableToFindTeamError as e:
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
            log.ERROR(f"出现错误: {e}")
        finally:
            if self.exc_traceback != '':
                self.exc_traceback = ''.join(
                    format_exception(*exc_info()))
                log.ERROR(self.exc_traceback)
                self.mutex.unlock()

        self.finished_signal.emit()

    """def stop(self):
        self.running=False
        self.finished_signal.emit()"""

    def _run(self):
        try:
            script_task()
        except Exception as e:
            log.ERROR(f"出现错误: {e}")
            self.exc_traceback = ''.join(
                format_exception(*exc_info()))
            log.ERROR(self.exc_traceback)
            self.mutex.unlock()
