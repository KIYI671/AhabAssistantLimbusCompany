from time import monotonic, sleep

from module.automation import auto
from module.decorator.decorator import begin_and_finish_time_log
from module.logger import log
from tasks.base import update_model_for_retry
from tasks.base.retry import click_title_screen_safely, ensure_simulator_game_started, retry
from tasks.mirror.reward_card import get_reward_card
from utils.image_utils import ImageUtils

LOOP_COUNT=30
LOADING_TIMEOUT = 90

@begin_and_finish_time_log(task_name="返回主界面")
def back_init_menu(*, allow_restart: bool = True):
    loop_count = LOOP_COUNT
    loading_started_at = None
    warned_no_escape = False
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
        if auto.find_element("base/waiting_assets.png") or auto.find_element("base/waiting_2_assets.png"):
            if loading_started_at is None:
                loading_started_at = monotonic()
            loop_count = LOOP_COUNT if monotonic() - loading_started_at < LOADING_TIMEOUT else 0
            continue
        loading_started_at = None

        # 左上角有后退键
        if auto.click_element("home/back_assets.png"):
            continue

        # 通行证（赛季）界面：领取日常/周常奖励后常停留在此界面，键盘端靠 ESC 退出。
        # 它的返回键与 home/back_assets.png 不是同一套样式（同屏相似度仅约 0.37），识别不到，
        # 但位置就在左上角的标准返回键槽位上，送不进 ESC 的设备按该槽位点一下即可。
        if not auto.supports_key("esc") and (
            auto.find_element("pass/pass_missions_assets.png") or auto.find_element("pass/weekly_assets.png")
        ):
            back_bbox = ImageUtils.get_bbox(ImageUtils.load_image("home/back_assets.png"))
            auto.mouse_click((back_bbox[0] + back_bbox[2]) / 2, (back_bbox[1] + back_bbox[3]) / 2)
            sleep(2)  # 等待界面切换动画播完，避免动画期间重复点击返回键
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
            loop_count = LOOP_COUNT
            continue

        if auto.click_element("base/only_option_assets.png", model="clam"):
            continue

        auto.mouse_click_blank()
        if not auto.supports_key("esc"):
            # 送不进 ESC 的设备：上面 mirror legend 分支的齿轮点击被 legend 识别门控，
            # 识别抖动时会漏，这里用新帧直接尝试界面上的设置/返回入口（与 luxcavation 同一模式）
            if auto.click_element("mirror/road_in_mir/setting_assets.png", take_screenshot=True):
                continue
            if auto.click_element("battle/setting_assets.png", take_screenshot=True):
                continue
            if auto.click_element("home/back_assets.png", take_screenshot=True):
                continue
            if not warned_no_escape:
                log.warning("当前输入设备送不进 ESC 且未识别到可点的设置/返回入口，界面可能卡住")
                warned_no_escape = True
        auto.key_press("esc")
