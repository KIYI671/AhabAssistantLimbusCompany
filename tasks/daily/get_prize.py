from module.automation import auto
from module.decorator.decorator import begin_and_finish_time_log
from module.logger import log
from utils.image_utils import ImageUtils


@begin_and_finish_time_log(task_name="收取日常/周常", calculate_time=False)
def get_pass_prize():
    loop_count = 15
    auto.model = 'clam'
    while True:
        # 自动截图
        if auto.take_screenshot() is None:
            continue
        if auto.click_element("pass/pass_coin.png", find_type='image_with_multiple_targets', interval=2):
            break
        if auto.click_element("pass/pass_missions_assets.png"):
            continue
        if loop_count>=10:
            if auto.click_element("home/season_assets.png"):
                continue
        else:
            season_bbox = ImageUtils.get_bbox(ImageUtils.load_image("home/season_assets.png"))
            if auto.find_text_element("season", season_bbox):
                auto.mouse_click((season_bbox[0]+season_bbox[2])/2, (season_bbox[1]+season_bbox[3])/2)
                continue
        #else:

        auto.mouse_to_blank()
        loop_count -= 1

        if loop_count < 10:
            auto.model = "normal"
        if loop_count < 5:
            auto.model = 'aggressive'
        if loop_count < 0:
            log.ERROR("无法收取日常/周常")
            return
    auto.click_element("pass/weekly_assets.png")
    loop_count = 15
    auto.model = 'clam'
    while True:
        if auto.click_element("pass/pass_coin.png", find_type='image_with_multiple_targets', take_screenshot=True):
            break
        loop_count -= 1
        if loop_count < 10:
            auto.model = "normal"
        if loop_count < 5:
            auto.model = 'aggressive'
        if loop_count < 0:
            log.ERROR("无法收取日常/周常")
            break


@begin_and_finish_time_log(task_name="收取邮箱", calculate_time=False)
def get_mail_prize():
    loop_count = 15
    auto.model = 'clam'
    while True:
        # 自动截图
        if auto.take_screenshot() is None:
            continue
        if auto.click_element("mail/get_mail_prize_confirm.png"):
            auto.click_element("mail/close_assets.png")
            break
        if auto.click_element("mail/claim_all_assets.png"):
            auto.click_element("mail/close_assets.png")
            break
        if auto.click_element("home/mail_assets.png") or auto.click_element("home/mail_cn_assets.png", model='normal'):
            continue
        auto.mouse_to_blank()
        loop_count -= 1
        if loop_count < 20:
            auto.model = "normal"
        if loop_count < 10:
            auto.model = 'aggressive'
        if loop_count < 0:
            log.ERROR("无法收取邮箱")
            break
