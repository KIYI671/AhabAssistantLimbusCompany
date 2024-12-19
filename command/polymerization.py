from time import sleep

from command.get_position import get_pic_position
from command.mouse_activity import mouse_click


def wait_to_click(pic_path):
    wait_time = 0.2
    position = None
    while True:
        if position := get_pic_position(pic_path):
            break
        sleep(wait_time)
        if wait_time < 1:
            wait_time += 0.1
    mouse_click(position)
