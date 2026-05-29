import re

from module.automation import auto
from module.config import cfg
from module.decorator.decorator import begin_and_finish_time_log
from module.logger import log
from tasks.base.retry import retry
from utils.image_utils import ImageUtils


def _screen_size() -> tuple[int, int]:
    height = int(cfg.set_win_size or 1080)
    return int(height * 16 / 9), height


def _mail_window_text() -> str:
    width, height = _screen_size()
    bbox = (int(width * 0.10), int(height * 0.14), int(width * 0.92), int(height * 0.90))
    try:
        return " ".join(str(text) for text in auto.get_text_from_screenshot(bbox)).lower()
    except Exception as e:
        log.debug(f"邮箱 OCR 失败: {e}")
        return ""


def _is_mailbox_open(mail_text: str) -> bool:
    return any(key in mail_text for key in ("mailbox", "inbox", "mail in storage", "邮件", "收件"))


def _is_mailbox_empty(mail_text: str) -> bool:
    compact = mail_text.replace(" ", "")
    return ("no mail" in mail_text and "storage" in mail_text) or "0/100" in compact or "0／100" in compact


def _mail_inbox_count(mail_text: str) -> int | None:
    compact = mail_text.replace(" ", "").replace("o", "0").replace("O", "0")
    match = re.search(r"(\d+)[/／]100", compact)
    if match is None:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def _click_mail_claim_confirm(relaxed: bool = False) -> bool:
    if auto.click_element("mail/get_mail_prize_confirm.png"):
        return True
    if relaxed:
        width, height = _screen_size()
        confirm_pos = auto.find_element("mail/get_mail_prize_confirm.png", threshold=0.65, model="aggressive")
        if (
            confirm_pos
            and width * 0.25 <= confirm_pos[0] <= width * 0.75
            and height * 0.45 <= confirm_pos[1] <= height * 0.90
        ):
            log.info("邮箱领取确认按钮低相似度命中，尝试点击确认")
            auto.mouse_action_with_pos(confirm_pos)
            return True
        text_pos = auto.find_text_element(["Confirm", "OK", "确认", "领取"])
        if (
            text_pos
            and width * 0.25 <= text_pos[0] <= width * 0.75
            and height * 0.45 <= text_pos[1] <= height * 0.90
        ):
            log.info("通过 OCR 找到邮箱领取确认按钮，尝试点击确认")
            auto.mouse_action_with_pos(text_pos, offset=False)
            return True
    return False


def _close_mailbox() -> bool:
    if auto.click_element("mail/close_assets.png", threshold=0.75):
        return True
    if close_position := auto.find_text_element(["Close", "关闭"]):
        auto.mouse_action_with_pos(close_position, offset=False)
        return True
    width, height = _screen_size()
    auto.mouse_click(int(width * 0.60), int(height * 0.80))
    return True


@begin_and_finish_time_log(task_name="收取日常/周常", calculate_time=False)
def get_pass_prize():
    loop_count = 15
    auto.model = "clam"
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
            if auto.find_text_element("season", season_bbox):
                auto.mouse_click(
                    (season_bbox[0] + season_bbox[2]) / 2,
                    (season_bbox[1] + season_bbox[3]) / 2,
                )
                continue
        # else:

        auto.mouse_to_blank()
        loop_count -= 1

        if loop_count < 10:
            auto.model = "normal"
        if loop_count < 5:
            auto.model = "aggressive"
        if loop_count < 0:
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
        if loop_count < 10:
            auto.model = "normal"
        if loop_count < 5:
            auto.model = "aggressive"
        if loop_count < 0:
            log.error("无法收取日常/周常")
            break


@begin_and_finish_time_log(task_name="收取邮箱", calculate_time=False)
def get_mail_prize():
    loop_count = 25
    waiting_for_confirm = False
    confirm_wait_count = 0
    claim_retry_count = 0
    auto.model = "clam"
    while True:
        # 自动截图
        if auto.take_screenshot() is None:
            continue
        if _click_mail_claim_confirm(relaxed=waiting_for_confirm):
            waiting_for_confirm = False
            confirm_wait_count = 0
            continue
        mail_text = _mail_window_text()
        mailbox_open = _is_mailbox_open(mail_text) or bool(auto.find_element("mail/close_assets.png", threshold=0.75))
        inbox_count = _mail_inbox_count(mail_text)
        if waiting_for_confirm and not mailbox_open:
            confirm_wait_count += 1
            if confirm_wait_count <= 3:
                log.debug("已点击 Claim All，等待邮箱领取确认弹窗")
                continue
            log.error("邮箱领取确认弹窗未能稳定识别，停止本次邮箱领取")
            break
        if mailbox_open and _is_mailbox_empty(mail_text):
            log.info("邮箱为空，关闭邮箱")
            _close_mailbox()
            break
        if mailbox_open:
            if waiting_for_confirm:
                confirm_wait_count += 1
                if confirm_wait_count <= 3:
                    log.debug("已点击 Claim All，等待邮箱领取确认")
                    continue
                if inbox_count and inbox_count > 0 and claim_retry_count < 2:
                    log.warning(f"邮箱领取确认未完成，当前仍有 {inbox_count} 封邮件，重新尝试 Claim All")
                    waiting_for_confirm = False
                    confirm_wait_count = 0
                    claim_retry_count += 1
                else:
                    log.error(f"邮箱领取确认失败，当前邮箱数量: {inbox_count}")
                    _close_mailbox()
                    break
            if auto.click_element("mail/claim_all_assets.png"):
                waiting_for_confirm = True
                confirm_wait_count = 0
                continue
            if inbox_count == 0:
                log.info("邮箱已无邮件，关闭邮箱")
                _close_mailbox()
                break
            if inbox_count and inbox_count > 0:
                log.debug(f"邮箱仍有 {inbox_count} 封邮件，继续尝试领取")
        elif auto.click_element("home/mail_assets.png"):
            continue
        auto.mouse_to_blank()
        loop_count -= 1
        if loop_count < 20:
            auto.model = "normal"
        if loop_count < 10:
            auto.model = "aggressive"
        if loop_count < 0:
            log.error("无法收取邮箱")
            break
