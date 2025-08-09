import ctypes
import os
import platform
import random
from sys import exc_info
from time import sleep
from traceback import format_exception

from PyQt5.QtCore import QThread, pyqtSignal, QMutex
from playsound3 import playsound

from module.automation import auto
from module.config import cfg
from module.decorator.decorator import begin_and_finish_time_log
from module.game_and_screen import screen, game_process
from module.logger import log
from module.my_error.my_error import userStopError, unableToFindTeamError, unexpectNumError, cannotOperateGameError, \
    netWorkUnstableError, backMainWinError, withOutGameWinError, notWaitError, withOutPicError, withOutAdminError
from tasks.base.back_init_menu import back_init_menu
from tasks.base.make_enkephalin_module import lunacy_to_enkephalin, make_enkephalin_module
from tasks.battle import battle
from tasks.daily.get_prize import get_pass_prize, get_mail_prize
from tasks.daily.luxcavation import EXP_luxcavation, thread_luxcavation
from tasks.mirror.mirror import Mirror
from tasks.teams.team_formation import select_battle_team
from utils import pic_path
from utils.utils import get_day_of_week, calculate_the_teams


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
def onetime_mir_process(team_setting):
    # 进行一次镜牢
    try:
        mirror_adventure = Mirror(team_setting)
        if mirror_adventure.run():
            del mirror_adventure
            mirror_adventure = None
            back_init_menu()
            make_enkephalin_module()
            return True
        else:
            return False
    except Exception as e:
        msg = f"镜牢行动出错: {e}"
        log.ERROR(msg)
        return False


def init_game():
    game_process.start_game()
    while not screen.init_handle():
        sleep(10)
    if cfg.set_windows:
        screen.set_win()


def script_task():
    # 获取（启动）游戏对游戏窗口进行设置
    init_game()

    if cfg.language_in_game == "zh_cn":
        pic_path.insert(0, "zh_cn")
    elif cfg.language_in_game == "en":
        pic_path = ["share", "en"] # 不用删除怕以后出什么bug

    if cfg.resonate_with_Ahab:
        random_number = random.randint(1, 4)
        playsound(f"assets/audio/This_is_all_your_fault_{random_number}.mp3")

    # 如果是战斗中，先处理战斗
    get_reward = None
    if auto.click_element("battle/turn_assets.png", take_screenshot=True):
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
        mir_times = cfg.set_mirror_count
        if cfg.infinite_dungeons:
            mir_times = 9999
        if cfg.save_rewards:
            mir_times = 1
        if cfg.teams_be_select_num != 0:
            while mir_times > 0:
                teams_order = cfg.teams_order
                team_num = teams_order.index(1)
                mirror_result = onetime_mir_process(cfg.get_value(f"team{team_num + 1}_setting"))
                if mirror_result:
                    for index, value in enumerate(teams_order):
                        if value == 0:
                            continue
                        if teams_order[index] == 1:
                            teams_order[index] = cfg.teams_be_select_num
                        elif teams_order[index] != 0:
                            teams_order[index] -= 1
                    cfg.set_value("teams_order", teams_order)
                    mir_times -= 1
        else:
            log.WARNING("没有选择任何队伍，请选择一个队伍进行镜牢任务")

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
