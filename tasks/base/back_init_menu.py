from module.automation import auto
from module.config import cfg
from module.decorator.decorator import begin_and_finish_time_log
from module.logger import log
from module.my_error.my_error import backMainWinError
from tasks.base.retry import retry
from tasks.mirror.reward_card import get_reward_card


@begin_and_finish_time_log(task_name="返回主界面")
def back_init_menu():
    loop_count = 30
    auto.model = 'clam'
    while True:
        # 自动截图
        if auto.take_screenshot() is None:
            continue
        if cfg.language_in_game == 'zh_cn':
            if auto.click_element("home/window_assets.png") and (
                    auto.find_element("home/mail_assets.png", model='normal') or auto.find_element(
                "home/mail_cn_assets.png", model='normal')):
                break
        else:
            if auto.click_element("home/window_assets.png") and auto.find_element("home/mail_assets.png",
                                                                                  model='normal'):
                break

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

        # 周年活动弹出的窗口
        if auto.click_element("home/close_anniversary_event_assets.png"):
            continue

        # 在刚进入游戏界面时
        if clear_all_caches := auto.find_element("base/clear_all_caches_assets.png", model="clam"):
            if auto.click_element("base/update_confirm_assets.png"):
                continue
            # auto.mouse_click(clear_all_caches[0], clear_all_caches[1] - 100) 临时禁用清除缓存功能
            continue

        auto.mouse_click_blank()
        auto.key_press('esc')
        retry()

        loop_count -= 1
        if loop_count < 20:
            auto.model = "normal"
        if loop_count < 10:
            auto.model = 'aggressive'
        if loop_count < 0:
            log.error("无法返回主界面，不能进行下一步,请手动操作重试")
            raise backMainWinError("无法返回主界面")
