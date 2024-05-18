from time import sleep

from command.get_position import get_pic_position, get_pic_position_without_cap
from command.mouse_activity import mouse_click


def retry():
    while get_pic_position("./pic/scenes/network/retry_countdown.png") \
            or get_pic_position_without_cap("./pic/scenes/network/retry.png") \
            or get_pic_position_without_cap("./pic/scenes/network/try_again.png"):
        if retry_button := get_pic_position("./pic/scenes/network/retry.png"):
            mouse_click(retry_button)
            sleep(5)
