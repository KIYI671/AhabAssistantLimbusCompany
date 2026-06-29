import time
from enum import StrEnum
from time import sleep

from module.automation import auto
from module.config import cfg
from module.decorator.decorator import begin_and_finish_time_log
from module.logger import log
from tasks.base import update_model_for_retry
from tasks.base.retry import (
    _is_runtime_ui_visible,
    click_title_screen_safely,
    ensure_simulator_game_started,
    retry,
)
from tasks.mirror.reward_card import get_reward_card


class StartupMainMenuWaitResult(StrEnum):
    MAIN_MENU = "main_menu"
    RUNTIME_UI = "runtime_ui"
    TIMEOUT = "timeout"


def get_startup_wait_timeout_seconds() -> int:
    key = "startup_wait_timeout_simulator" if cfg.simulator else "startup_wait_timeout_pc"
    default = 180 if cfg.simulator else 120
    return int(cfg.get_value(key, default))


def handle_launch_state_once() -> bool | None:
    if auto.find_element("base/clear_all_caches_assets.png", model="clam"):
        if auto.click_element("base/update_confirm_assets.png"):
            return True
        click_title_screen_safely()
        return True
    if auto.find_element("base/connecting_assets.png"):
        return True
    if auto.find_element("base/waiting_assets.png"):
        return True
    if auto.find_element("base/waiting_2_assets.png"):
        return True
    if auto.click_element("base/only_option_assets.png", model="clam"):
        return True
    return None


def wait_until_main_menu_after_launch(*, allow_restart: bool = True, max_retries: int = 3) -> StartupMainMenuWaitResult:
    retries = 0
    while True:
        auto.model = "clam"
        timeout_seconds = get_startup_wait_timeout_seconds()
        start_time = time.time()
        deadline = start_time + timeout_seconds
        halfway_logged = False
        halfway_threshold = start_time + timeout_seconds / 2
        while True:
            now = time.time()
            if now > deadline:
                break
            if not halfway_logged and timeout_seconds >= 10 and now >= halfway_threshold:
                log.info(f"启动后仍在等待进入主界面，已等待{int(now - start_time)}秒/{timeout_seconds}秒")
                halfway_logged = True
            if ensure_simulator_game_started():
                continue
            if auto.take_screenshot() is None:
                continue
            if handle_launch_state_once():
                continue
            if auto.click_element("home/window_assets.png") and auto.find_element("home/mail_assets.png", model="normal"):
                return StartupMainMenuWaitResult.MAIN_MENU
            if _is_runtime_ui_visible():
                return StartupMainMenuWaitResult.RUNTIME_UI
            sleep(0.5)
        log.error(f"启动等待主界面超时（{timeout_seconds}秒）")
        if not allow_restart:
            return StartupMainMenuWaitResult.TIMEOUT
        retries += 1
        if retries > max_retries:
            log.error(f"启动等待主界面已重试 {max_retries} 次仍超时，放弃重试")
            return StartupMainMenuWaitResult.TIMEOUT
        from tasks.base.retry import kill_game
        from tasks.base.script_task_scheme import init_game

        log.error("启动等待主界面超时，尝试重启游戏")
        kill_game()
        init_game()


@begin_and_finish_time_log(task_name="返回主界面")
def back_init_menu(*, allow_restart: bool = True):
    loop_count = 30
    auto.model = "clam"
    while True:
        loop_count -= 1
        update_model_for_retry(loop_count, normal_at=20, aggressive_at=10)
        if loop_count < 0:
            if not allow_restart:
                log.warning("无法返回主界面，本次调用禁用内部重启，返回失败")
                return False
            from tasks.base.retry import kill_game, restart_game

            log.error("无法返回主界面，尝试重启游戏")
            kill_game()
            restart_game()
            loop_count = 30
            auto.model = "clam"
            sleep(1)
            continue
        if ensure_simulator_game_started():
            continue
        if retry() is False:
            return False

        if auto.click_element("home/window_assets.png") and auto.find_element("home/mail_assets.png", model="normal"):
            return True

        if auto.find_element("base/notification_close_assets.png"):
            from datetime import datetime
            from zoneinfo import ZoneInfo

            from tasks.base.retry import kill_game, restart_game
            from utils.utils import get_day_of_week

            kill_game()
            if get_day_of_week() == 4:
                seoul_tz = ZoneInfo("Asia/Seoul")
                now_time = datetime.now(seoul_tz)
                today_10am = now_time.replace(hour=10, minute=0, second=0, microsecond=0)
                today_12pm = now_time.replace(hour=12, minute=0, second=0, microsecond=0)

                if today_10am <= now_time <= today_12pm:
                    time_remaining = today_12pm - now_time
                    total_seconds = int(time_remaining.total_seconds())
                    msg = f"当前时间为Limbus周常维护时间，距离正常维护时间结束还有{total_seconds}秒，脚本程序将暂停同样时间"
                    log.info(msg)
                    sleep(total_seconds)
            if not allow_restart:
                log.warning("检测到维护提示且本次调用禁用内部重启，返回失败")
                return False
            restart_game()
            continue

        if auto.click_element("mirror/road_in_mir/towindow&forfeit_confirm_assets.png"):
            continue
        if auto.click_element("mirror/road_in_mir/to_window_assets.png", threshold=0.75):
            continue
        if auto.find_element("mirror/road_in_mir/legend_assets.png"):
            auto.click_element("mirror/road_in_mir/setting_assets.png")
            continue

        if auto.find_element("mirror/road_in_mir/select_encounter_reward_card_assets.png"):
            get_reward_card()

        # 在剧情中
        if auto.click_element("scenes/story_skip_confirm_assets.png"):
            continue
        if auto.click_element("scenes/story_skip_assets.png"):
            continue
        if auto.click_element("scenes/story_meun_assets.png"):
            continue

        # 等待加载情况
        if auto.find_element("base/waiting_assets.png"):
            continue
        if auto.find_element("base/waiting_2_assets.png"):
            continue

        # 左上角有后退键
        if auto.click_element("home/back_assets.png"):
            continue

        # 在战斗中
        if auto.click_element("battle/setting_assets.png"):
            sleep(1)
            auto.click_element("battle/give_up_assets.png", take_screenshot=True)
            auto.click_element("battle/normal_give_up_assets.png")
            continue

        # 周年活动弹出的窗口
        if auto.click_element("home/close_anniversary_event_assets.png"):
            continue

        # 在刚进入游戏界面时
        if auto.find_element("base/clear_all_caches_assets.png", model="clam"):
            if auto.click_element("base/update_confirm_assets.png"):
                continue
            click_title_screen_safely()
            continue

        if auto.click_element("base/only_option_assets.png", model="clam"):
            continue

        auto.mouse_click_blank()
        auto.key_press("esc")
