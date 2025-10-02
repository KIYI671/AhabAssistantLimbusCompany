import os
import platform
import random
from sys import exc_info
from time import sleep, time
from datetime import datetime
from traceback import format_exception

import win32process
from PySide6.QtCore import QThread, QMutex, QT_TRANSLATE_NOOP
from playsound3 import playsound

from module.ALI import auto_switch_language_in_game, AutoSwitchCon, get_game_config_from_registry
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
from app import mediator
from app.windows_toast import send_toast, TemplateToast

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
        exc_traceback = ''.join(format_exception(*exc_info()))
        msg += f"\n调用栈信息:\n{exc_traceback}"
        log.error(msg)
        return False

def to_get_reward():
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

def init_game():
    if cfg.simulator:
        if cfg.simulator_type == 0:
            from module.simulator.mumu_control import MumuControl
            MumuControl.connection_device.start_game()
        else:
            from module.simulator.simulator_control import SimulatorControl
            SimulatorControl.connection_device.start_game()
    else:
        game_process.start_game()
        while not screen.init_handle():
            sleep(10)
        if cfg.set_windows:
            screen.set_win()


def script_task() -> None | int:
    simulator = None
    if cfg.simulator:
        if cfg.simulator_type == 0:
            mumu_instance_number = 0
            if cfg.simulator_port == 0 and cfg.mumu_instance_number == -1:
                log.info("未设置模拟器端口或实例编号，使用默认mumu模拟器")
            elif cfg.simulator_port != 0:
                if cfg.simulator_port == 16384 or (cfg.simulator_port - 16384) % 32 == 0:
                    mumu_instance_number = 0 if cfg.simulator_port== 16384 else (cfg.simulator_port - 16384) // 32
                else:
                    log.info("设置的模拟器端口非常用默认端口，使用默认mumu模拟器")
            elif cfg.mumu_instance_number != -1:
                mumu_instance_number = cfg.mumu_instance_number
            from module.simulator.mumu_control import MumuControl
            simulator = MumuControl(instance_number=mumu_instance_number)
        else:
            from module.simulator.simulator_control import SimulatorControl
            simulator = SimulatorControl()
        auto.init_input()
    start_time = time()
    # 获取（启动）游戏对游戏窗口进行设置
    init_game()

    # 自动更改语言, 如果不支持则直接退出
    try:
        if cfg.experimental_auto_lang:
            ret = auto_switch_language_in_game(screen.handle._hWnd)
            if ret == AutoSwitchCon.FAILED:
                log.info(f"自动切换语言失败，使用英语尝试")
                cfg.set_value("language_in_game", "en")
        else:
            if cfg.language_in_game == "-":
                log.warning("自动切换语言已关闭但是并未设置语言! 即将使用英语尝试!")
                cfg.set_value("language_in_game", "en")
    except Exception as e:
        log.error(f"自动切换语言出错: {e}，使用英语尝试")
        cfg.set_value("language_in_game", "en")

    # 低渲染比例发出警告
    if get_game_config_from_registry().get("_renderingScale", -1) == 2:
        log.warning("当前游戏渲染比例为低, 可能会导致识别错误, 建议设置为中或更高")

    if cfg.language_in_game == "zh_cn":
        pic_path.insert(0, "zh_cn")
    elif cfg.language_in_game == "en":
        while pic_path[0] != "share":
            pic_path.pop(0)
        pic_path.insert(0, "en")

    if cfg.resonate_with_Ahab:
        random_number = random.randint(1, 4)
        playsound(f"assets/audio/This_is_all_your_fault_{random_number}.mp3", block=False)
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
        to_get_reward()

    # 执行狂气换饼任务
    if cfg.buy_enkephalin:
        back_init_menu()
        lunacy_to_enkephalin(times=cfg.set_lunacy_to_enkephalin)

    # 执行镜牢任务
    if cfg.mirror:
        # 判断执行镜牢任务的次数
        mir_times = cfg.set_mirror_count
        if cfg.infinite_dungeons:
            mir_times = 9999
        if cfg.save_rewards and cfg.hard_mirror:
            mir_times = 1
        finish_times = 0
        mediator.mirror_signal.emit(0, mir_times)
        # 开始执行镜牢任务
        while mir_times > 0:
            # 检测配置的队伍能否顺利执行
            useful = False
            hard = cfg.hard_mirror
            teams_be_select = cfg.get_value("teams_be_select")
            for index in (i for i, t in enumerate(teams_be_select) if t is True):
                team_setting = cfg.get_value(f"team{index + 1}_setting")
                if team_setting["fixed_team_use"] is False:
                    useful = True
                    break
                if team_setting["fixed_team_use_select"] == 1 and hard is False:
                    useful = True
                    break
                if team_setting["fixed_team_use_select"] == 0 and hard is True:
                    useful = True
                    break
            if useful is False:
                break

            teams_order = cfg.teams_order  # 复制一份队伍顺序
            team_num = teams_order.index(1)  # 获取序号1的队伍在队伍顺序中的位置
            team_setting = cfg.get_value(f"team{team_num + 1}_setting")  # 获取序号1的队伍的配置
            # 如果该队伍固定了用途，且不用途符合当前情况，将序号1的队伍移动到队伍顺序的最后
            if "fixed_team_use" in team_setting and team_setting["fixed_team_use"]:
                if (team_setting["fixed_team_use_select"] == 0 and cfg.hard_mirror is False) or (
                        team_setting["fixed_team_use_select"] == 1 and cfg.hard_mirror is True):
                    for index, value in enumerate(teams_order):
                        if value == 0:
                            continue
                        if teams_order[index] == 1:
                            teams_order[index] = cfg.teams_be_select_num
                        elif teams_order[index] != 0:
                            teams_order[index] -= 1
                    cfg.set_value("teams_order", teams_order)
                    continue
            # 执行一次镜牢任务，根据执行结果进行处理
            mirror_result = onetime_mir_process(team_setting)
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
                if cfg.hard_mirror and cfg.auto_hard_mirror:
                    chance = cfg.hard_mirror_chance - 1
                    cfg.set_value("hard_mirror_chance", chance)
                    if chance == 0:
                        cfg.set_value("hard_mirror", False)

                # 更新进度条
                finish_times += 1
                mediator.mirror_signal.emit(finish_times, mir_times)

        mediator.mirror_bar_kill_signal.emit()
        if cfg.re_claim_rewards:
            to_get_reward()

    if cfg.set_reduce_miscontact and not cfg.simulator:
        screen.reset_win()
    if cfg.simulator:
        if cfg.simulator_type == 0:
            from module.simulator.mumu_control import MumuControl
            MumuControl.clean_connect()


    log.info("脚本任务已经完成")
    QT_TRANSLATE_NOOP("WindowsToast", "AALC 运行结束")
    QT_TRANSLATE_NOOP("WindowsToast", "所有任务已完成")
    dt_start = datetime.fromtimestamp(start_time)
    dt_end = datetime.fromtimestamp(time())
    duration = dt_end - dt_start
    secends = duration.total_seconds()
    minutes, seconds = divmod(secends, 60)
    hours, minutes = divmod(minutes, 60)
    run_time = f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"
    send_toast("AALC 运行结束", ["所有任务已完成", run_time], template=TemplateToast.NormalTemplate)
    if cfg.resonate_with_Ahab:
        random_number = random.randint(1, 4)
        playsound(f"assets/audio/This_is_all_your_fault_{random_number}.mp3", block=False)

    if platform.system() == "Windows":
        after_completion = cfg.after_completion
        try:
            if after_completion == 1:
                os.system("rundll32.exe powrprof.dll,SetSuspendState Sleep")
            elif after_completion == 2:
                os.system("rundll32.exe powrprof.dll,SetSuspendState Hibernate")
            elif after_completion == 3:
                os.system("shutdown /s /t 30")
            elif after_completion == 4 or after_completion == 6:
                _, pid = win32process.GetWindowThreadProcessId(screen.handle._hWnd)
                ret = os.system(f'taskkill /F /PID {pid}')
                if ret == 0:
                    log.info("成功关闭 Limbus Company")
                elif ret == 128:
                    log.error("错误：进程不存在")
                elif ret == 1:
                    log.error("错误：权限不足")
        except Exception as e:
            log.error(f"脚本结束后的操作失败: {e}")

        finally:
            if after_completion == 5 or after_completion == 6:
                return 0  # 正常退出信号


class my_script_task(QThread):


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
        except ConnectionError as e:
            self.exception = e
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
            log.error(f"出现错误: {e}")
        finally:
            if self.exc_traceback != '':
                self.exc_traceback = ''.join(
                    format_exception(*exc_info()))
                log.error(self.exc_traceback)
                self.mutex.unlock()

        mediator.finished_signal.emit()

    """def stop(self):
        self.running=False
        self.finished_signal.emit()"""

    def _run(self):
        try:
            ret = script_task()
            if ret == 0:
                mediator.kill_signal.emit()
            auto.clear_img_cache()
        except Exception as e:
            log.error(f"出现错误: {e}")
            self.exc_traceback = ''.join(
                format_exception(*exc_info()))
            log.error(self.exc_traceback)
            self.mutex.unlock()
