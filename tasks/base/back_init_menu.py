from time import sleep

from module.automation import auto
from module.config import cfg
from module.decorator.decorator import begin_and_finish_time_log
from module.logger import log
from module.my_error.my_error import backMainWinError
from tasks.base.retry import retry
from tasks.mirror.reward_card import get_reward_card

from time import sleep

@begin_and_finish_time_log(task_name="返回主界面")
def back_init_menu():
    loop_count = 30
    auto.model = 'clam'
    while True:
        if cfg.simulator:
            if cfg.simulator_type ==0 :
                from module.simulator.mumu_control import MumuControl
                if MumuControl.connection_device.check_game_alive() is False:
                    MumuControl.connection_device.start_game()
            else:
                from module.simulator.simulator_control import SimulatorControl
                if SimulatorControl.connection_device.check_game_alive() is False:
                    SimulatorControl.connection_device.start_game()
        # 自动截图
        if auto.take_screenshot() is None:
            continue

        if retry() is False:
            return False

        if cfg.language_in_game == 'zh_cn':
            if auto.click_element("home/window_assets.png") and (
                    auto.find_element("home/mail_assets.png", model='normal') or auto.find_element(
                "home/mail_cn_assets.png", model='normal')):
                break
        else:
            if auto.click_element("home/window_assets.png") and auto.find_element("home/mail_assets.png",
                                                                                  model='normal'):
                break

        if auto.find_element("base/notification_close_assets.png"):
            from tasks.base.retry import kill_game,restart_game
            from utils.utils import get_timezone,get_day_of_week
            from datetime import datetime, timedelta, time
            kill_game()
            if get_day_of_week() == 4:
                get_timezone()
                now_time = datetime.now()
                offset = timedelta(hours=cfg.timezone)
                now_time_offset = now_time + offset
                # 创建当天10:00和12:00的时间对象（与now_time_offset同日期）
                today_10am = now_time_offset.replace(hour=10, minute=0, second=0, microsecond=0)
                today_12pm = now_time_offset.replace(hour=12, minute=0, second=0, microsecond=0)

                # 判断是否在10:00-12:00之间
                if today_10am <= now_time_offset <= today_12pm:
                    # 计算时间差
                    time_remaining = today_12pm - now_time_offset

                    # 获取总秒数
                    total_seconds = int(time_remaining.total_seconds())
                    msg = f"当前时间为Limbus周常维护时间，距离正常维护时间结束还有{total_seconds}秒，脚本程序将暂停同样时间"
                    log.info(msg)
                    sleep(total_seconds)
            restart_game()
            continue

        if auto.click_element("mirror/road_in_mir/towindow&forfeit_confirm_assets.png"):
            continue
        if auto.click_element("mirror/road_in_mir/to_window_assets.png"):
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
            auto.mouse_click_blank()
            sleep(5)
            continue

        auto.mouse_click_blank()
        auto.key_press('esc')

        loop_count -= 1
        if loop_count < 20:
            auto.model = "normal"
        if loop_count < 10:
            auto.model = 'aggressive'
        if loop_count < 0:
            log.error("无法返回主界面，不能进行下一步,请手动操作重试")
            raise backMainWinError("无法返回主界面")
