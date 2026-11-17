from time import sleep

from module.automation import auto
from module.config import cfg
from module.decorator.decorator import begin_and_finish_time_log
from module.logger import log
from tasks.base import update_model_for_retry
from tasks.base.retry import retry
from utils.image_utils import ImageUtils


@begin_and_finish_time_log(task_name="收取日常/周常", calculate_time=False)
def get_pass_prize():
    loop_count = 15
    auto.model = "clam"
    last_try = False
    while True:
        # 自动截图
        if auto.take_screenshot() is None:
            continue
        if coordinates := auto.find_element("pass/pass_coin.png", find_type="image_with_multiple_targets"):
            for coordinate in coordinates:
                auto.mouse_click(coordinate[0], coordinate[1])
                retry()
            break
        if auto.click_element("pass/pass_missions_assets.png"):
            continue
        if loop_count >= 10:
            if auto.click_element("home/season_assets.png"):
                continue
        else:
            season_bbox = ImageUtils.get_bbox(ImageUtils.load_image("home/season_assets.png"))
            if auto.find_text_element(["season","seasun"], season_bbox):
                auto.mouse_click(
                    (season_bbox[0] + season_bbox[2]) / 2,
                    (season_bbox[1] + season_bbox[3]) / 2,
                )
                continue

        auto.mouse_to_blank()
        loop_count -= 1
        update_model_for_retry(loop_count, normal_at=10, aggressive_at=5)
        if loop_count < 0:
            if last_try is False:
                scale = cfg.set_win_size / 1440
                mail_pos = auto.find_element("home/mail_assets.png")
                auto.mouse_click(mail_pos[0], mail_pos[1]+200*scale)
                loop_count+=1
                continue
            log.error("无法收取日常/周常")
            return
    auto.click_element("pass/weekly_assets.png")
    loop_count = 15
    auto.model = "clam"
    while True:
        if coordinates := auto.find_element(
            "pass/pass_coin.png",
            find_type="image_with_multiple_targets",
            take_screenshot=True,
        ):
            for coordinate in coordinates:
                auto.mouse_click(coordinate[0], coordinate[1])
                retry()
            break
        loop_count -= 1
        update_model_for_retry(loop_count, normal_at=10, aggressive_at=5)
        if loop_count < 0:
            log.error("无法收取日常/周常")
            break


@begin_and_finish_time_log(task_name="收取邮箱", calculate_time=False)
def get_mail_prize():
    loop_count = 15
    auto.model = "clam"
    scale = cfg.set_win_size / 1440
    empty_mail_bbox = tuple(round(value * scale) for value in (1000, 600, 1560, 850))
    while loop_count >= 0:
        # 自动截图
        if auto.take_screenshot() is None:
            continue
        loop_count -= 1
        update_model_for_retry(loop_count, normal_at=10, aggressive_at=5)
        if retry() is False:
            return False
        if auto.click_element("mail/get_mail_prize_confirm.png"):
            auto.click_element("mail/close_assets.png")
            break
        close_position = auto.find_element("mail/close_assets.png", model="normal", threshold=0.68)
        if close_position and auto.find_text_element(["暂无邮件", "no mail"], my_crop=empty_mail_bbox):
            auto.mouse_action_with_pos(close_position, offset=False)
            break
        if auto.click_element("mail/claim_all_assets.png"):
            sleep(3)
            if retry():
                continue
            auto.click_element("mail/close_assets.png")
            break
        if not close_position and auto.click_element("home/mail_assets.png"):
            continue
        auto.mouse_to_blank()
    else:
        log.error("无法收取邮箱")
