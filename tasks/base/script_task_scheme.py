import platform
import random
from datetime import datetime
from threading import Event
from time import sleep, time

import win32api
import win32con
from playsound3 import playsound
from PySide6.QtCore import QT_TRANSLATE_NOOP, QMutex, QThread

from app import mediator
from app.windows_toast import TemplateToast, send_toast
from module.automation import auto
from module.config import TeamSetting, cfg
from module.config.task_queue import DailyTask, EnkephalinTask, MirrorTask, RewardOptions, RewardTask
from module.decorator.decorator import begin_and_finish_time_log
from module.game_and_screen import game_process, screen
from module.game_and_screen.hdr import get_monitor_hdr_info
from module.logger import log
from module.my_error.my_error import (
    backMainWinError,
    cannotOperateGameError,
    netWorkUnstableError,
    notWaitError,
    unableToFindTeamError,
    unexpectNumError,
    userStopError,
    withOutAdminError,
    withOutGameWinError,
    withOutPicError,
)
from module.system_actions import (
    apply_power_keep_awake,
    execute_after_completion,
    get_after_completion_config,
)
from tasks.base.back_init_menu import back_init_menu
from tasks.base.make_enkephalin_module import (
    lunacy_to_enkephalin,
    make_enkephalin_module,
)
from tasks.base.retry_monitor import retry_monitor
from tasks.base.run_plan import (
    RunContext,
    RunPlan,
    any_team_usable,
    daily_times,
    exp_team,
    is_hard_mirror,
    mirror_times,
    split_combat,
    team_usable,
    thread_team,
)
from tasks.battle import battle
from tasks.daily.get_prize import get_mail_prize, get_pass_prize
from tasks.daily.luxcavation import EXP_luxcavation, thread_luxcavation
from tasks.mirror.mirror import Mirror
from tasks.teams.team_formation import select_battle_team
from utils.path_manager import path_manager
from utils.utils import calculate_the_teams, check_hard_mirror_time, get_day_of_week


@begin_and_finish_time_log(task_name="一次经验本")
# 一次经验本的过程
def onetime_EXP_process(team: int, combat_count: int = 1):
    EXP_luxcavation(combat_count)
    select_battle_team(team)
    if battle.to_battle() is False:
        return False
    battle.fight(combat_count=combat_count)
    back_init_menu()
    make_enkephalin_module()


@begin_and_finish_time_log(task_name="一次纽本")
# 一次纽本的过程
def onetime_thread_process(team: int, combat_count: int = 1):
    thread_luxcavation(combat_count)
    select_battle_team(team)
    if battle.to_battle() is False:
        return False
    battle.fight(combat_count=combat_count)
    back_init_menu()
    make_enkephalin_module()


def refresh_auto_hard_mirror() -> None:
    """自动困牢：进入新的困牢周期时重置剩余次数为 3"""
    if not cfg.auto_hard_mirror:
        return
    if cfg.last_auto_change == 1715990400:
        cfg.set_value("last_auto_change", datetime.now().timestamp())
    if check_hard_mirror_time():
        log.info("检测到新的困牢周期，设置困牢次数为3")
        cfg.set_value("last_auto_change", datetime.now().timestamp())
        cfg.set_value("hard_mirror_chance", 3)


@begin_and_finish_time_log(task_name="一次镜牢")
# 一次镜牢的过程
def onetime_mir_process(team_setting: TeamSetting, team_num: int, task: MirrorTask, hard: bool):
    try:
        mirror_adventure = Mirror(team_setting, team_num, task, hard)
        if mirror_adventure.run():
            del mirror_adventure
            mirror_adventure = None
            back_init_menu()
            make_enkephalin_module()
            return True
        else:
            return False
    except Exception as e:
        log.exception(f"镜牢行动出错: {e}")
        return False


def to_get_reward(options: RewardOptions):
    if not options.any():
        return
    back_init_menu()
    if options.missions or options.battle_pass:
        if not get_pass_prize(claim_missions=options.missions, claim_rewards=options.battle_pass):
            return
        back_init_menu()
    if options.mail:
        get_mail_prize()
        back_init_menu()


def init_game():
    log.debug("初始化游戏")
    if cfg.simulator:
        if cfg.simulator_type == 0:
            mumu_instance_number = 0
            if cfg.simulator_port == 0 and cfg.mumu_instance_number == -1:
                log.info("未设置模拟器端口或实例编号，使用默认mumu模拟器")
            elif cfg.simulator_port != 0:
                if cfg.simulator_port == 16384 or (cfg.simulator_port - 16384) % 32 == 0:
                    mumu_instance_number = 0 if cfg.simulator_port == 16384 else (cfg.simulator_port - 16384) // 32
                    log.debug(f"使用mumu模拟器实例号为 {mumu_instance_number}")
                else:
                    log.info("设置的模拟器端口非常用默认端口，使用默认mumu模拟器")
            elif cfg.mumu_instance_number != -1:
                mumu_instance_number = cfg.mumu_instance_number
            log.debug(
                f"init_game: 模拟器类型=Mumu, 实例编号={mumu_instance_number}, "
                f"simulator_port={cfg.simulator_port}, mumu_instance_number={cfg.mumu_instance_number}"
            )
            from module.automation.input_handlers.simulator.mumu_control import (
                MumuControl,
            )

            MumuControl(instance_number=mumu_instance_number)
        else:
            from module.automation.input_handlers.simulator.simulator_control import (
                SimulatorControl,
            )

            # 启动时先清理旧连接
            SimulatorControl.clean_connect()
            SimulatorControl()
    auto.init_input()
    if cfg.simulator:
        if cfg.simulator_type == 0:
            from module.automation.input_handlers.simulator.mumu_control import (
                MumuControl,
            )

            MumuControl.connection_device.start_game()
        else:
            from module.automation.input_handlers.simulator.simulator_control import (
                SimulatorControl,
            )

            SimulatorControl.connection_device.start_game()
    else:
        game_process.start_game()
        while not screen.init_handle():
            sleep(10)
        if cfg.set_windows:
            screen.set_win()


def _warn_if_game_monitor_hdr_enabled() -> None:
    if cfg.simulator or not bool(cfg.get_value("experimental_hdr_warning", True)):
        return

    hwnd = screen.handle.hwnd
    if not hwnd:
        log.warning("游戏窗口句柄无效，跳过 HDR 检测")
        return

    try:
        hmonitor = win32api.MonitorFromWindow(
            hwnd,
            win32con.MONITOR_DEFAULTTONEAREST,
        )
        info = get_monitor_hdr_info(int(hmonitor))
    except Exception as exc:
        log.warning(f"检测游戏显示器 HDR 状态失败: {exc}")
        return

    if info is None or not info.hdr_enabled:
        return

    acknowledged = Event()
    log.warning("检测到游戏所在显示器已开启 HDR，可能导致图像识别问题")
    mediator.hdr_warning.emit(acknowledged)
    acknowledged.wait()


def Resonate_with_Ahab():
    random_number = random.randint(1, 4)
    playsound(f"assets/audio/This_is_all_your_fault_{random_number}.mp3", block=False)


def _get_game_rendering_scale() -> int | None:
    """读取非模拟器模式下 Limbus 的渲染比例设置。"""
    try:
        import json
        import winreg

        root = winreg.HKEY_CURRENT_USER
        sub_key = r"Software\ProjectMoon\LimbusCompany"
        value_name = "LocalSave.LocalGameOptionData_h467498167"
        with winreg.OpenKey(root, sub_key, 0, winreg.KEY_READ) as key:
            raw_data, reg_type = winreg.QueryValueEx(key, value_name)

        if reg_type != winreg.REG_BINARY:
            log.debug(f"游戏设置注册表值类型为 {reg_type}，预期为 REG_BINARY")
            return None

        json_str = raw_data.rstrip(b"\x00").decode("utf-8")
        game_config = json.loads(json_str)
        return game_config.get("_renderingScale")
    except FileNotFoundError:
        log.debug(r"游戏设置注册表路径不存在: HKEY_CURRENT_USER\Software\ProjectMoon\LimbusCompany")
    except PermissionError:
        log.debug("读取游戏设置注册表时权限不足")
    except Exception as e:
        log.debug(f"读取游戏渲染比例失败: {e}")
    return None


def run_daily(task: DailyTask, ctx: RunContext) -> None:
    back_init_menu()
    make_enkephalin_module()
    exp_times, thread_times = daily_times(task, ctx.take_finished_battle())
    exp_team_num = exp_team(task, calculate_the_teams())
    thread_team_num = thread_team(task, get_day_of_week())
    if task.continuous_combat:
        exp_batches = split_combat(exp_times, task.continuous_combat_max)
        thread_batches = split_combat(thread_times, task.continuous_combat_max)
    else:
        exp_batches = [1] * exp_times
        thread_batches = [1] * thread_times
    for count in exp_batches:
        onetime_EXP_process(exp_team_num, count)
    for count in thread_batches:
        onetime_thread_process(thread_team_num, count)


def run_reward(task: RewardTask, ctx: RunContext) -> None:
    to_get_reward(task)


def run_enkephalin(task: EnkephalinTask, ctx: RunContext) -> None:
    back_init_menu()
    lunacy_to_enkephalin(times=task.lunacy_times, dr_grandet=task.dr_grandet)


def _current_hard(task: MirrorTask) -> bool:
    return is_hard_mirror(task, cfg.auto_hard_mirror, cfg.hard_mirror_chance)


def run_mirror(task: MirrorTask, ctx: RunContext) -> None:
    refresh_auto_hard_mirror()
    hard = _current_hard(task)
    mir_times = mirror_times(task, hard)
    if task.save_rewards and hard:
        log.info("启用了保存困牢奖励，将只执行一次困牢，并且不结算")
    finish_times = 0
    mediator.mirror_signal.emit(0, mir_times, hard)
    cfg.normalize_and_sync_team_state(persist=False)
    re_claim = task.re_claim_rewards and task.re_claim.any()
    # 开始执行镜牢任务
    while mir_times > 0:
        # 实时检查是否进入新的困牢周期
        refresh_auto_hard_mirror()
        hard = _current_hard(task)
        # 检测配置的队伍能否顺利执行
        teams_be_select = cfg.get_value("teams_be_select")
        enabled_teams = [
            cfg.config.teams[f"{index + 1}"] for index, selected in enumerate(teams_be_select) if selected is True
        ]
        if not any_team_usable([(t.fixed_team_use, t.fixed_team_use_select) for t in enabled_teams], hard):
            log.warning("没有可用于当前难度的队伍，镜牢任务结束")
            break

        if not cfg.teams_active_queue:
            break

        team_num = cfg.teams_active_queue[0]
        team_setting = cfg.config.teams[f"{team_num}"]
        # 如果该队伍固定了用途，且用途不符合当前情况，将队首队伍轮转到队尾
        if not team_usable(team_setting.fixed_team_use, team_setting.fixed_team_use_select, hard):
            cfg.rotate_team_queue()
            continue
        # 执行一次镜牢任务，根据执行结果进行处理
        mirror_result = onetime_mir_process(team_setting, team_num, task, hard)
        if mirror_result:
            cfg.rotate_team_queue()
            mir_times -= 1
            if hard and cfg.auto_hard_mirror and cfg.hard_mirror_chance > 0:
                cfg.set_value("hard_mirror_chance", cfg.hard_mirror_chance - 1)

            # 更新进度条
            finish_times += 1
            mediator.mirror_signal.emit(finish_times, mir_times, hard)
            msg = f"已完成 {finish_times} 次镜牢"
            log.info(msg)
            if finish_times == 1 and re_claim:  # 完成第一次镜牢后重新领取奖励
                to_get_reward(task.re_claim)

    mediator.mirror_bar_kill_signal.emit()
    if re_claim and finish_times > 1:
        to_get_reward(task.re_claim)


TASK_RUNNERS = {
    "daily": run_daily,
    "reward": run_reward,
    "enkephalin": run_enkephalin,
    "mirror": run_mirror,
}

TASK_LOG_NAMES = {"daily": "日常任务", "reward": "领取奖励", "enkephalin": "狂气换体", "mirror": "镜牢"}


def task_log_name(task) -> str:
    return task.name or TASK_LOG_NAMES.get(task.type, task.type)


def script_task(plan: RunPlan) -> None | int:
    start_time = time()
    # 获取（启动）游戏对游戏窗口进行设置
    init_game()
    _warn_if_game_monitor_hdr_enabled()

    if cfg.skip_enkephalin:
        log.info("设置了跳过合成脑啡肽，将不会自动合成\nSet to skip make enkephalin, it will not to do")
    if not cfg.simulator:
        if _get_game_rendering_scale() == 2:
            log.warning("当前游戏渲染比例为低, 可能会导致识别错误, 建议设置为中或更高")
        if cfg.set_win_size == 720:
            log.warning("当前游戏分辨率为1280*720, 可能会导致识别错误或卡死, 建议设置为更高分辨率")

    path_manager.initialize_paths()
    auto.clear_img_cache()
    log.debug(f"初始化图片路径: {path_manager.pic_path}")
    retry_monitor.start()

    if cfg.resonate_with_Ahab:
        Resonate_with_Ahab()

    names = "、".join(task_log_name(t) for t in plan.tasks)
    log.info(f"本次执行 {len(plan.tasks)} 个任务（来源：{plan.source}）：{names}")
    ctx = RunContext()
    # 如果是战斗中，先处理战斗
    if auto.click_element("battle/turn_assets.png", take_screenshot=True):
        first_mirror = plan.first(MirrorTask)
        ctx.finished_battle = battle.fight(fight_to_last_man=first_mirror.fight_to_last_man if first_mirror else False)

    for task in plan.tasks:
        log.info(f"开始执行任务：{task_log_name(task)}")
        mediator.task_item_started.emit(task.id)
        TASK_RUNNERS[task.type](task, ctx)
    mediator.task_item_started.emit("")

    if cfg.set_reduce_miscontact and not cfg.simulator:
        # 任务已结束，这里只恢复游戏窗口样式，避免把前台重新切回游戏。
        screen.reset_win(activate=False)

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
    send_toast(
        "AALC 运行结束",
        ["所有任务已完成", run_time],
        template=TemplateToast.NormalTemplate,
    )
    if cfg.resonate_with_Ahab:
        Resonate_with_Ahab()

    should_exit_aalc = False
    if platform.system() == "Windows":
        # 收尾动作可能主动关闭游戏或模拟器。先停止截图监控，避免设备消失
        # 被误判为断链并触发自动恢复，重新拉起刚关闭的模拟器。
        retry_monitor.stop()
        if plan.after_completion is not None:
            actions, power_action = plan.after_completion.normalized()
        else:
            actions, power_action = get_after_completion_config()
        try:
            should_exit_aalc = execute_after_completion(actions, power_action)
        except Exception:
            log.exception("脚本结束后的操作失败")

    if cfg.simulator:
        if cfg.simulator_type == 0:
            from module.automation.input_handlers.simulator.mumu_control import (
                MumuControl,
            )

            MumuControl.clean_connect()

    if should_exit_aalc:
        return 0


class my_script_task(QThread):
    def __init__(self, plan: RunPlan):
        # 初始化，构造函数
        super().__init__()
        self.mutex = QMutex()
        self.plan = plan

    def run(self):
        self.mutex.lock()

        try:
            self._run()
        except (
            ConnectionError,
            userStopError,
            unableToFindTeamError,
            unexpectNumError,
            cannotOperateGameError,
            netWorkUnstableError,
            backMainWinError,
            withOutGameWinError,
            notWaitError,
            withOutPicError,
            withOutAdminError,
        ) as e:
            self.exception = e
        except Exception as e:
            self.exception = e
            log.exception("脚本线程执行失败")
        finally:
            retry_monitor.stop()
            self.mutex.unlock()

    def terminate(self):
        retry_monitor.stop()
        super().terminate()
        # TerminateThread 不会释放被杀线程持有的 RLock,换新锁防止后续任务取锁永久阻塞
        auto.reset_safety_locks()

    """def stop(self):
        self.running=False
        self.finished_signal.emit()"""

    def _run(self):
        keep_awake_enabled = bool(cfg.get_value("experimental_keep_screen_awake", False))
        try:
            if keep_awake_enabled:
                apply_power_keep_awake(True)
            ret = script_task(self.plan)
            if ret == 0:
                mediator.kill_signal.emit()
        finally:
            if keep_awake_enabled:
                # 先切回 AALC 再释放线程级防息屏，避免游戏仍持有前台时继续阻止息屏。
                mediator.request_focus.emit()
                self.msleep(800)  # 覆盖 WinRT toast 异步归还焦点（延迟约 600ms），再释放防息屏
                apply_power_keep_awake(False)
            auto.clear_img_cache()
