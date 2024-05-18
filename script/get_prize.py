from command.get_pic import win_cap
from command.get_position import get_pic_position, get_all_pic_position
from command.mouse_activity import mouse_click
from my_decorator.decorator import begin_and_finish_log


@begin_and_finish_log(task_name="收取日常/周常")
def get_pass_prize():
    mouse_click(get_pic_position("./pic/prize/now_season.png"))
    mouse_click(get_pic_position("./pic/prize/pass_missions.png"))
    daily_coin = get_all_pic_position("./pic/prize/pass_coin.png")
    for coin in daily_coin:
        mouse_click(coin)

    mouse_click(get_pic_position("./pic/prize/weekly.png"))
    weekly_coin = get_all_pic_position("./pic/prize/pass_coin.png")
    for coin in weekly_coin:
        mouse_click(coin)

@begin_and_finish_log(task_name="收取邮箱")
def get_mail_prize():
    mouse_click(get_pic_position("./pic/scenes/mail.png"))
    mouse_click(get_pic_position("./pic/prize/claim_all.png"))
    if get_pic_position("./pic/prize/get_mail_prize_confirm.png") is not None:
        mouse_click(get_pic_position("./pic/prize/get_mail_prize_confirm.png"))
    mouse_click(get_pic_position("./pic/prize/mail_close.png"))

